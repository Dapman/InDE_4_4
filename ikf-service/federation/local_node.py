"""
InDE v3.2 - Local Federation Node
Represents this InDE instance as a node in the IKF federation.

Node Types:
- CONTRIBUTOR: Can submit packages (default)
- CONSUMER: Can query patterns
- FULL: Both contributor and consumer

Federation Connectivity:
- Direct: Connect to federation hub
- Peer: Connect to known peer nodes
- Offline: Local-only mode (packages queued for later sync)
"""

import logging
import os
import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger("inde.ikf.federation")


class NodeType(str, Enum):
    CONTRIBUTOR = "CONTRIBUTOR"
    CONSUMER = "CONSUMER"
    FULL = "FULL"


class ConnectivityMode(str, Enum):
    DIRECT = "DIRECT"
    PEER = "PEER"
    OFFLINE = "OFFLINE"


class LocalFederationNode:
    """
    Local node in the IKF federation.

    Handles:
    - Node registration with federation
    - Heartbeat/health reporting
    - Capability advertisement
    - Connectivity management
    """

    def __init__(self, db, config: Optional[Dict] = None):
        """
        Initialize local federation node.

        Args:
            db: MongoDB database instance
            config: Optional node configuration
        """
        self._db = db
        self._config = config or {}

        # Node identity
        self._node_id = self._config.get("node_id") or self._get_or_create_node_id()
        self._node_type = NodeType(self._config.get("node_type", "FULL"))

        # Federation connectivity
        self._hub_url = os.environ.get("IKF_HUB_URL", "")
        self._api_key = os.environ.get("IKF_API_KEY", "")
        self._mode = ConnectivityMode.OFFLINE

        # Peer nodes (for peer-to-peer mode)
        self._peers: List[Dict] = []

        # Status
        self._registered = False
        self._last_heartbeat: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    def _get_or_create_node_id(self) -> str:
        """Get existing node ID or create new one."""
        node_doc = self._db.ikf_node_config.find_one({"_id": "local_node"})
        if node_doc:
            return node_doc.get("node_id")

        # Create new node ID
        node_id = f"node-{uuid.uuid4().hex[:12]}"
        self._db.ikf_node_config.insert_one({
            "_id": "local_node",
            "node_id": node_id,
            "created_at": datetime.now(timezone.utc)
        })
        logger.info(f"Created new federation node ID: {node_id}")
        return node_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def mode(self) -> ConnectivityMode:
        return self._mode

    @property
    def is_connected(self) -> bool:
        return self._mode != ConnectivityMode.OFFLINE and self._registered

    async def initialize(self):
        """Initialize node and attempt federation connection."""
        logger.info(f"Initializing federation node: {self._node_id}")

        # Try to connect to hub
        if self._hub_url and self._api_key:
            try:
                self._http_client = httpx.AsyncClient(
                    base_url=self._hub_url,
                    headers={"X-IKF-API-Key": self._api_key},
                    timeout=30.0
                )
                await self._register_with_hub()
                self._mode = ConnectivityMode.DIRECT
                logger.info(f"Connected to federation hub: {self._hub_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to hub: {e}")
                self._mode = ConnectivityMode.OFFLINE
        else:
            logger.info("No federation hub configured, running in OFFLINE mode")
            self._mode = ConnectivityMode.OFFLINE

    async def _register_with_hub(self):
        """Register this node with the federation hub."""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")

        registration = {
            "node_id": self._node_id,
            "node_type": self._node_type.value,
            "capabilities": self._get_capabilities(),
            "version": "3.5.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        response = await self._http_client.post("/nodes/register", json=registration)

        if response.status_code == 200:
            self._registered = True
            self._last_heartbeat = datetime.now(timezone.utc)

            # Store registration info
            self._db.ikf_node_config.update_one(
                {"_id": "local_node"},
                {"$set": {
                    "registered_at": datetime.now(timezone.utc),
                    "hub_url": self._hub_url
                }}
            )
            logger.info("Successfully registered with federation hub")
        elif response.status_code == 409:
            # Already registered, refresh registration
            self._registered = True
            logger.info("Node already registered, refreshing")
        else:
            raise RuntimeError(f"Registration failed: {response.status_code}")

    def _get_capabilities(self) -> Dict[str, Any]:
        """Get this node's capabilities for advertisement."""
        return {
            "package_types": [
                "temporal_benchmark",
                "pattern_contribution",
                "risk_intelligence",
                "effectiveness_metrics",
                "retrospective_wisdom"
            ],
            "methodologies": [
                "LEAN_STARTUP",
                "DESIGN_THINKING",
                "AGILE",
                "WATERFALL"
            ],
            "generalization_version": "1.0",
            "supports_query": self._node_type in (NodeType.CONSUMER, NodeType.FULL),
            "supports_contribute": self._node_type in (NodeType.CONTRIBUTOR, NodeType.FULL)
        }

    async def heartbeat(self) -> bool:
        """Send heartbeat to federation hub."""
        if self._mode == ConnectivityMode.OFFLINE or not self._http_client:
            return False

        try:
            response = await self._http_client.post(
                f"/nodes/{self._node_id}/heartbeat",
                json={"timestamp": datetime.now(timezone.utc).isoformat()}
            )

            if response.status_code == 200:
                self._last_heartbeat = datetime.now(timezone.utc)
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False

    async def sync_pending_packages(self) -> Dict[str, int]:
        """
        Sync locally-queued packages to federation.

        Returns:
            {"synced": count, "failed": count}
        """
        if self._mode == ConnectivityMode.OFFLINE:
            return {"synced": 0, "failed": 0, "reason": "offline"}

        # Find packages queued for federation
        pending = list(self._db.ikf_contributions.find({
            "status": "IKF_READY",
            "federation_status": {"$in": [None, "PENDING"]}
        }))

        synced = 0
        failed = 0

        for package in pending:
            try:
                success = await self._submit_to_federation(package)
                if success:
                    self._db.ikf_contributions.update_one(
                        {"contribution_id": package["contribution_id"]},
                        {"$set": {
                            "federation_status": "SUBMITTED",
                            "submitted_at": datetime.now(timezone.utc)
                        }}
                    )
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to sync package {package['contribution_id']}: {e}")
                failed += 1

        logger.info(f"Federation sync complete: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed}

    async def _submit_to_federation(self, package: Dict) -> bool:
        """Submit a single package to federation."""
        if not self._http_client:
            return False

        submission = {
            "node_id": self._node_id,
            "contribution_id": package["contribution_id"],
            "package_type": package["package_type"],
            "generalized_data": package.get("generalized_data", {}),
            "confidence": package.get("confidence", 0.0),
            "context": {
                "industry": package.get("generalized_data", {}).get("preserved_context", {}).get("industry_naics", ""),
                "methodology": package.get("generalized_data", {}).get("preserved_context", {}).get("methodology", "")
            }
        }

        response = await self._http_client.post("/packages/submit", json=submission)
        return response.status_code in (200, 201)

    def get_status(self) -> Dict[str, Any]:
        """Get node status for monitoring."""
        return {
            "node_id": self._node_id,
            "node_type": self._node_type.value,
            "mode": self._mode.value,
            "registered": self._registered,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
            "hub_url": self._hub_url if self._hub_url else None,
            "capabilities": self._get_capabilities()
        }

    async def shutdown(self):
        """Gracefully shutdown node."""
        if self._http_client:
            await self._http_client.aclose()
        logger.info(f"Federation node {self._node_id} shutdown")
