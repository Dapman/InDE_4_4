"""
Federation Circuit Breaker

Protects the InDE coaching layer from federation failures.

States:
- CLOSED (normal): All outbound calls flow to remote IKF
- OPEN (failed): Calls short-circuit immediately; return local fallback
- HALF_OPEN (testing): Single probe call allowed to test recovery

The circuit breaker is TRANSPARENT to the coaching layer.
When OPEN, the query client returns local-only results.
The innovator never sees any degradation.

Configuration (from .env):
- IKF_CIRCUIT_BREAKER_THRESHOLD: Failures before OPEN (default 5)
- IKF_CIRCUIT_BREAKER_RESET_SECONDS: Time before HALF_OPEN (default 300)

Usage:
    breaker = CircuitBreaker(failure_threshold=5, reset_timeout=300)

    try:
        result = await breaker.call(http_client.post, url, json=data)
    except CircuitOpenError:
        # Use local fallback
        result = get_local_fallback()
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger("inde.ikf.circuit_breaker")


class CircuitState(str, Enum):
    """Circuit breaker state machine states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing - reject all calls
    HALF_OPEN = "HALF_OPEN" # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN and call is rejected."""

    def __init__(self, message: str, reset_in_seconds: float = 0):
        super().__init__(message)
        self.reset_in_seconds = reset_in_seconds


class CircuitBreaker:
    """
    Circuit breaker for protecting the coaching layer from federation failures.

    The circuit breaker tracks consecutive failures and opens the circuit
    when the threshold is exceeded. Once open, all calls are rejected
    immediately without attempting the actual network call.

    After the reset timeout, the circuit enters HALF_OPEN state where
    a single probe call is allowed. If successful, the circuit closes.
    If the probe fails, the circuit returns to OPEN.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 300,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Seconds before OPEN → HALF_OPEN transition
            on_state_change: Optional callback for state transitions
        """
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._on_state_change = on_state_change

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._last_state_change: float = time.time()
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_rejections = 0

        logger.info(
            f"Circuit breaker initialized: threshold={failure_threshold}, "
            f"reset_timeout={reset_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for OPEN → HALF_OPEN transition."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self._reset_timeout:
                # Transition to HALF_OPEN (allow probe)
                self._transition_state(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is in normal (closed) state."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting calls)."""
        return self.state == CircuitState.OPEN

    def _transition_state(self, new_state: CircuitState):
        """Transition to a new state with logging and callback."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._last_state_change = time.time()

            logger.info(f"Circuit breaker: {old_state.value} → {new_state.value}")

            if self._on_state_change:
                try:
                    self._on_state_change(old_state, new_state)
                except Exception as e:
                    logger.warning(f"State change callback failed: {e}")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        If CLOSED: execute normally; track failures
        If OPEN: raise CircuitOpenError immediately (no network call)
        If HALF_OPEN: allow one probe call; if success → CLOSED, if fail → OPEN

        Args:
            func: Async callable to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result of func(*args, **kwargs)

        Raises:
            CircuitOpenError: If circuit is OPEN
            Exception: Any exception from func (also tracked as failure)
        """
        self._total_calls += 1
        current_state = self.state

        if current_state == CircuitState.OPEN:
            self._total_rejections += 1
            reset_in = max(0, self._reset_timeout - (time.time() - self._last_failure_time))
            raise CircuitOpenError(
                f"Circuit breaker is OPEN (failures: {self._failure_count}, "
                f"reset in: {reset_in:.0f}s)",
                reset_in_seconds=reset_in
            )

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success handling
            async with self._lock:
                self._success_count += 1

                if current_state == CircuitState.HALF_OPEN:
                    # Probe succeeded — close the circuit
                    self._transition_state(CircuitState.CLOSED)
                    self._failure_count = 0
                    logger.info("Circuit breaker recovery confirmed")
                elif self._failure_count > 0:
                    # Gradual recovery: reduce failure count on success
                    self._failure_count = max(0, self._failure_count - 1)

            return result

        except Exception as e:
            # Failure handling
            self._total_failures += 1

            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self._failure_threshold:
                    if self._state != CircuitState.OPEN:
                        self._transition_state(CircuitState.OPEN)
                        logger.error(
                            f"Circuit breaker OPEN after {self._failure_count} failures: {e}"
                        )
                elif current_state == CircuitState.HALF_OPEN:
                    # Probe failed — back to OPEN
                    self._transition_state(CircuitState.OPEN)
                    logger.warning(f"Circuit breaker probe failed: {e}")

            # Re-raise the original exception
            raise

    def record_failure(self):
        """
        Record a failure without executing a call.

        Useful when failure is detected externally (e.g., timeout in calling code).
        """
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._total_failures += 1

        if self._failure_count >= self._failure_threshold:
            if self._state != CircuitState.OPEN:
                self._transition_state(CircuitState.OPEN)

    def record_success(self):
        """
        Record a success without executing a call.

        Useful when success is detected externally.
        """
        self._success_count += 1
        if self._failure_count > 0:
            self._failure_count = max(0, self._failure_count - 1)

    def reset(self):
        """
        Manual reset (admin action).

        Resets the circuit to CLOSED state and clears failure count.
        Does not reset statistics.
        """
        self._transition_state(CircuitState.CLOSED)
        self._failure_count = 0
        self._last_failure_time = 0
        logger.info("Circuit breaker manually reset to CLOSED")

    def force_open(self):
        """
        Force the circuit to OPEN state (admin action).

        Useful for maintenance or testing.
        """
        self._transition_state(CircuitState.OPEN)
        self._last_failure_time = time.time()
        logger.info("Circuit breaker manually forced to OPEN")

    def get_status(self) -> dict:
        """Return current circuit breaker status for API/dashboard."""
        current_state = self.state
        time_in_state = time.time() - self._last_state_change

        status = {
            "state": current_state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "reset_timeout_seconds": self._reset_timeout,
            "time_in_state_seconds": round(time_in_state, 1),
            "statistics": {
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_rejections": self._total_rejections,
                "success_count": self._success_count
            }
        }

        if current_state == CircuitState.OPEN:
            time_since_failure = time.time() - self._last_failure_time
            status["reset_in_seconds"] = max(0, self._reset_timeout - time_since_failure)

        return status

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self.state.value}, "
            f"failures={self._failure_count}/{self._failure_threshold})"
        )
