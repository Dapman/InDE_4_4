"""
InDE v3.2 - Consumer Registry
Creates and configures all Redis Streams consumers for inde-app.

Each consumer group processes events independently. Multiple consumer
groups can read the same events for different purposes.
"""

import logging
from typing import List
from events.redis_consumer import RedisStreamConsumer

logger = logging.getLogger("inde.events.registry")


def create_app_consumers(db=None) -> List[RedisStreamConsumer]:
    """
    Create and configure all Redis Streams consumers for inde-app.

    Returns list of consumer instances to be started as async tasks.
    Each consumer group processes events independently.

    Args:
        db: Database instance for handler access

    Returns:
        List of configured RedisStreamConsumer instances
    """
    consumers = []

    # --- Maturity Engine Consumer ---
    maturity_consumer = RedisStreamConsumer(group_name="maturity-engine")

    def on_element_captured(event):
        """Update maturity score when element captured."""
        logger.debug(f"Maturity: Element captured in {event.pursuit_id}")
        # Full handler implementation uses maturity model

    def on_pursuit_completed(event):
        """Update maturity score when pursuit completes."""
        logger.debug(f"Maturity: Pursuit completed {event.pursuit_id}")

    def on_experiment_completed(event):
        """Update validation_rigor dimension."""
        logger.debug(f"Maturity: Experiment completed in {event.pursuit_id}")

    def on_coaching_exchange(event):
        """Track coaching engagement for reflective_practice."""
        logger.debug(f"Maturity: Coaching exchange in {event.pursuit_id}")

    maturity_consumer.register_handler("element.captured", on_element_captured)
    maturity_consumer.register_handler("rve.experiment.completed", on_experiment_completed)
    maturity_consumer.register_handler("pursuit.completed", on_pursuit_completed)
    maturity_consumer.register_handler("coaching.message.exchanged", on_coaching_exchange)

    consumers.append(maturity_consumer)

    # --- Health Monitor Consumer ---
    health_consumer = RedisStreamConsumer(group_name="health-monitor")

    def on_pursuit_state_changed(event):
        """Recalculate health when pursuit state changes."""
        logger.debug(f"Health: State changed for {event.pursuit_id}")

    def on_element_for_health(event):
        """Update element coverage in health score."""
        logger.debug(f"Health: Element captured in {event.pursuit_id}")

    health_consumer.register_handler("pursuit.state.transitioned", on_pursuit_state_changed)
    health_consumer.register_handler("element.captured", on_element_for_health)
    health_consumer.register_handler("pursuit.created", on_pursuit_state_changed)

    consumers.append(health_consumer)

    # --- Crisis Monitor Consumer ---
    crisis_consumer = RedisStreamConsumer(group_name="crisis-monitor")

    def on_health_crisis(event):
        """Auto-trigger crisis mode on critical health."""
        logger.debug(f"Crisis: Health crisis detected in {event.pursuit_id}")

    def on_health_zone_changed(event):
        """Monitor for critical zone transitions."""
        logger.debug(f"Crisis: Health zone changed in {event.pursuit_id}")

    crisis_consumer.register_handler("health.crisis.detected", on_health_crisis)
    crisis_consumer.register_handler("health.zone.changed", on_health_zone_changed)

    consumers.append(crisis_consumer)

    # --- Temporal Logger Consumer ---
    temporal_consumer = RedisStreamConsumer(group_name="temporal-logger")

    def log_temporal_event(event):
        """Log all events as temporal events for timeline."""
        logger.debug(f"Temporal: {event.event_type} at {event.timestamp}")
        # In full implementation, writes to temporal_events collection
        if db:
            from datetime import datetime, timezone
            db.db.temporal_events.insert_one({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "pursuit_id": event.pursuit_id,
                "user_id": event.user_id,
                "timestamp": event.timestamp,
                "logged_at": datetime.now(timezone.utc)
            })

    temporal_consumer.register_handler("*", log_temporal_event)

    consumers.append(temporal_consumer)

    # --- Portfolio Intelligence Consumer ---
    portfolio_consumer = RedisStreamConsumer(group_name="portfolio-intel")

    def on_pursuit_for_portfolio(event):
        """Update portfolio analytics on pursuit changes."""
        logger.debug(f"Portfolio: Pursuit event {event.event_type}")

    def on_health_for_portfolio(event):
        """Update portfolio health on health score changes."""
        logger.debug(f"Portfolio: Health updated for {event.pursuit_id}")

    portfolio_consumer.register_handler("pursuit.completed", on_pursuit_for_portfolio)
    portfolio_consumer.register_handler("pursuit.state.transitioned", on_pursuit_for_portfolio)
    portfolio_consumer.register_handler("health.score.updated", on_health_for_portfolio)

    consumers.append(portfolio_consumer)

    logger.info(f"Registered {len(consumers)} consumer groups for inde-app")
    return consumers


def register_fallback_handlers(dispatcher, db=None):
    """
    Register v3.1-style fallback handlers on the dispatcher.

    These handlers are invoked when Redis is unavailable,
    ensuring graceful degradation.

    Args:
        dispatcher: EventDispatcher instance
        db: Database instance
    """
    def fallback_log(event):
        """Fallback handler that logs events."""
        logger.info(f"Fallback handler: {event.event_type}")

    # Register fallback for critical event types
    dispatcher.register("pursuit.created", fallback_log)
    dispatcher.register("pursuit.completed", fallback_log)
    dispatcher.register("element.captured", fallback_log)
    dispatcher.register("crisis.triggered", fallback_log)

    logger.info("Registered fallback event handlers")
