"""
Trust Relationship Manager - Bilateral Trust Establishment & Lifecycle

Manages trust relationships via the IKF Trust APIs (Section 7.1):

IKF Endpoints:
- POST /trust/relationship/request       - Initiate trust request
- POST /trust/relationship/respond       - Accept/reject request
- GET  /trust/relationship/{id}          - Get relationship details
- DELETE /trust/relationship/{id}        - Terminate relationship
- GET  /trust/network                    - List all trust relationships
- POST /trust/consortium/join            - Join consortium
- GET  /trust/consortium/{id}/members    - List consortium members

Local Storage:
- ikf_trust_relationships collection - cached trust network
- Updated on sync and on trust lifecycle events

Trust Prerequisites for Cross-Org Features:
- Cross-org IDTFS requires: ACTIVE trust + CONTRIBUTOR/STEWARD verification
- PARTNER sharing level enables: richer pattern detail, cross-org discovery

All trust operations are logged to the audit stream.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("inde.ikf.trust_manager")


class TrustManager:
    """
    Manages bilateral trust relationships with other organizations.

    Trust relationships enable enhanced knowledge sharing and cross-org
    talent discovery through the IKF federation network.
    """

    def __init__(self, db, connection_manager, circuit_breaker,
                 http_client, event_publisher, config):
        """
        Initialize the Trust Manager.

        Args:
            db: MongoDB database instance
            connection_manager: Federation connection manager
            circuit_breaker: Circuit breaker for resilience
            http_client: HTTP client for IKF requests
            event_publisher: Event publisher for notifications
            config: Configuration object
        """
        self._db = db
        self._conn_manager = connection_manager
        self._breaker = circuit_breaker
        self._http_client = http_client
        self._publisher = event_publisher
        self._config = config

    async def request_trust(self, target_org_id: str,
                            relationship_type: str,
                            sharing_level: str,
                            justification: str = None,
                            expiration_date: str = None) -> Optional[dict]:
        """
        Initiate a trust relationship request.

        POST /trust/relationship/request

        The request goes to the IKF, which forwards it to the target
        organization. Neither party sees the other's internal data
        until both accept.

        Args:
            target_org_id: Target organization ID
            relationship_type: BILATERAL, CONSORTIUM, or RESEARCH
            sharing_level: INDUSTRY or PARTNER
            justification: Optional reason for the request
            expiration_date: Optional expiration date (ISO 8601)

        Returns:
            Relationship dict if successful, None otherwise
        """
        if not self._conn_manager.is_connected:
            logger.warning("Cannot request trust: not connected to federation")
            return None

        payload = {
            "targetOrganizationId": target_org_id,
            "relationshipType": relationship_type,
            "sharingLevel": sharing_level,
            "justification": justification,
            "expirationDate": expiration_date
        }

        try:
            response = await self._breaker.call(
                self._http_client.post,
                f"{self._get_ikf_base_url()}/v1/trust/relationship/request",
                json=payload,
                headers=self._create_outbound_headers()
            )

            if response.status_code == 201:
                relationship = response.json()
                # Cache locally
                await self._cache_relationship(relationship)
                # Publish event
                await self._publish_event("trust.requested", {
                    "relationship_id": relationship.get("relationshipId"),
                    "target_org": target_org_id,
                    "type": relationship_type,
                    "sharing_level": sharing_level
                })
                logger.info(f"Trust request sent to {target_org_id}: {relationship.get('relationshipId')}")
                return relationship
            else:
                logger.error(f"Trust request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Trust request error: {e}")
            return None

    async def respond_to_trust(self, relationship_id: str,
                                accept: bool,
                                terms: dict = None) -> Optional[dict]:
        """
        Accept or reject a trust relationship request.

        POST /trust/relationship/respond

        Args:
            relationship_id: The relationship ID to respond to
            accept: True to accept, False to reject
            terms: Optional terms for acceptance

        Returns:
            Updated relationship dict if successful
        """
        if not self._conn_manager.is_connected:
            logger.warning("Cannot respond to trust: not connected to federation")
            return None

        payload = {
            "relationshipId": relationship_id,
            "response": "ACCEPT" if accept else "REJECT",
            "terms": terms
        }

        try:
            response = await self._breaker.call(
                self._http_client.post,
                f"{self._get_ikf_base_url()}/v1/trust/relationship/respond",
                json=payload,
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                relationship = response.json()
                await self._cache_relationship(relationship)
                event_type = "trust.accepted" if accept else "trust.rejected"
                await self._publish_event(event_type, {
                    "relationship_id": relationship_id,
                    "status": relationship.get("status")
                })
                logger.info(f"Trust response sent for {relationship_id}: {'ACCEPTED' if accept else 'REJECTED'}")
                return relationship
            else:
                logger.error(f"Trust response failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Trust response error: {e}")
            return None

    async def revoke_trust(self, relationship_id: str, reason: str = None) -> bool:
        """
        Terminate a trust relationship.

        DELETE /trust/relationship/{id}

        Immediate effect: cross-org features disabled for this partner.

        Args:
            relationship_id: The relationship to revoke
            reason: Optional reason for revocation

        Returns:
            True if successful
        """
        if not self._conn_manager.is_connected:
            logger.warning("Cannot revoke trust: not connected to federation")
            return False

        try:
            response = await self._breaker.call(
                self._http_client.delete,
                f"{self._get_ikf_base_url()}/v1/trust/relationship/{relationship_id}",
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                self._db.ikf_trust_relationships.update_one(
                    {"relationship_id": relationship_id},
                    {"$set": {
                        "status": "REVOKED",
                        "revoked_at": datetime.now(timezone.utc),
                        "revoke_reason": reason
                    }}
                )
                await self._publish_event("trust.revoked", {
                    "relationship_id": relationship_id,
                    "reason": reason
                })
                logger.info(f"Trust relationship {relationship_id} revoked")
                return True
            else:
                logger.error(f"Trust revoke failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Trust revoke error: {e}")
            return False

    async def get_trust_network(self) -> List[dict]:
        """
        Retrieve the org's full trust network from IKF.

        Returns local cache if IKF is unavailable.

        Returns:
            List of trust relationship dicts
        """
        if self._conn_manager.is_connected:
            try:
                response = await self._breaker.call(
                    self._http_client.get,
                    f"{self._get_ikf_base_url()}/v1/trust/network",
                    headers=self._create_outbound_headers()
                )
                if response.status_code == 200:
                    relationships = response.json().get("relationships", [])
                    # Update local cache
                    for rel in relationships:
                        await self._cache_relationship(rel)
                    return relationships
            except Exception as e:
                logger.warning(f"Trust network fetch failed, using cache: {e}")

        # Fallback to cached data
        return list(self._db.ikf_trust_relationships.find(
            {},
            {"_id": 0}
        ))

    async def get_active_trust_relationships(self) -> List[dict]:
        """Get only active trust relationships."""
        return list(self._db.ikf_trust_relationships.find(
            {"status": "ACTIVE"},
            {"_id": 0}
        ))

    async def has_active_trust(self, target_org_id: str) -> bool:
        """Check if there's an active trust relationship with target org."""
        return self._db.ikf_trust_relationships.count_documents({
            "partner_org_id": target_org_id,
            "status": "ACTIVE"
        }) > 0

    async def get_trust_level(self, target_org_id: str) -> Optional[str]:
        """
        Get sharing level for a trusted partner.

        Returns:
            "PARTNER", "INDUSTRY", or None if no trust
        """
        rel = self._db.ikf_trust_relationships.find_one({
            "partner_org_id": target_org_id,
            "status": "ACTIVE"
        })
        return rel.get("sharing_level") if rel else None

    async def get_relationship(self, relationship_id: str) -> Optional[dict]:
        """Get a specific trust relationship by ID."""
        return self._db.ikf_trust_relationships.find_one(
            {"relationship_id": relationship_id},
            {"_id": 0}
        )

    async def check_trust_prerequisites(self) -> dict:
        """
        Check if trust-dependent features are available.

        Returns status dict with:
        - has_active_trust: bool
        - active_trust_count: int
        - can_use_cross_org_idtfs: bool
        - can_use_partner_sharing: bool
        - verification_level: str
        """
        active_trusts = await self.get_active_trust_relationships()

        # Get verification level
        fed_state = self._db.ikf_federation_state.find_one({"type": "registration"})
        verification_level = fed_state.get("verification_level", "OBSERVER") if fed_state else "OBSERVER"

        # Check cross-org IDTFS prerequisites
        can_cross_org = (
            len(active_trusts) > 0 and
            verification_level in ("CONTRIBUTOR", "STEWARD")
        )

        # Check partner sharing
        has_partner = any(t.get("sharing_level") == "PARTNER" for t in active_trusts)

        return {
            "has_active_trust": len(active_trusts) > 0,
            "active_trust_count": len(active_trusts),
            "can_use_cross_org_idtfs": can_cross_org,
            "can_use_partner_sharing": has_partner,
            "verification_level": verification_level,
            "trusted_org_ids": [t.get("partner_org_id") for t in active_trusts]
        }

    async def _cache_relationship(self, relationship: dict):
        """Cache trust relationship locally."""
        self._db.ikf_trust_relationships.update_one(
            {"relationship_id": relationship.get("relationshipId")},
            {"$set": {
                "relationship_id": relationship.get("relationshipId"),
                "partner_org_id": relationship.get("partnerOrgId"),
                "partner_org_name": relationship.get("partnerOrgName"),
                "relationship_type": relationship.get("relationshipType"),
                "sharing_level": relationship.get("sharingLevel"),
                "status": relationship.get("status"),
                "established_at": relationship.get("establishedAt"),
                "expires_at": relationship.get("expiresAt"),
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _get_ikf_base_url(self) -> str:
        """Get the IKF base URL from config or environment."""
        if self._config and hasattr(self._config, 'ikf_base_url'):
            return self._config.ikf_base_url
        return os.environ.get("IKF_REMOTE_NODE_URL", "http://localhost:8081/ikf-hub")

    def _create_outbound_headers(self) -> dict:
        """Create headers for outbound IKF requests."""
        if self._config and hasattr(self._config, 'create_outbound_headers'):
            return self._config.create_outbound_headers()
        return {"Content-Type": "application/json"}

    async def _publish_event(self, event_type: str, data: dict):
        """Publish trust event."""
        if self._publisher:
            try:
                await self._publisher.publish_ikf_event(event_type, data)
            except Exception as e:
                logger.warning(f"Failed to publish {event_type} event: {e}")
