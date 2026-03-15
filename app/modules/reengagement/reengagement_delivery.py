"""
Re-Engagement Delivery Service

Wraps the v3.16 email infrastructure to send re-engagement messages.
Uses the same email service that sends welcome emails and password
resets — consistent voice, consistent delivery.

Design rules:
  - Uses existing EmailService from v3.16 — do NOT create a new email client
  - Re-engagement emails are FROM the same sender as other InDE email
  - Plain text preferred over HTML — coaching messages should feel personal
  - Subject lines come from ReengagementGenerator (pursuit-specific)
  - Body is a single coaching question — no InDE branding in the body
  - Footer contains a single unsubscribe-equivalent: opt-out of coaching cadence
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ReengagementDeliveryService:
    """
    Delivers re-engagement messages via the v3.16 email infrastructure.

    Usage:
        delivery = ReengagementDeliveryService()
        sent = delivery.send(to_email, to_name, subject, body, metadata)
    """

    # Footer appended to all re-engagement messages
    # Uses plain language — not "unsubscribe" (which sounds like marketing)
    FOOTER_TEMPLATE = (
        "\n\n---\n"
        "You're receiving this because you enabled coaching check-ins in your "
        "InDE preferences. To stop receiving these, visit your preferences and "
        "turn off 'Coaching Check-ins'."
    )

    def __init__(self):
        """Initialize delivery service."""
        pass  # Stateless — uses the module-level email functions

    def send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Send a re-engagement message.

        Args:
            to_email:  Recipient email address
            to_name:   Recipient display name (for logging, not added to body)
            subject:   Email subject from ReengagementGenerator
            body:      Message body from ReengagementGenerator
            metadata:  Optional dict for logging/telemetry

        Returns:
            True if sent, False on failure. Never raises.
        """
        if not to_email:
            logger.warning("Re-engagement send skipped: no email address")
            return False

        full_body = body + self.FOOTER_TEMPLATE

        try:
            # Use existing v3.16 email service
            from services.email_service import _send_email, is_email_configured

            if not is_email_configured():
                logger.warning("Re-engagement skipped: email not configured")
                return False

            # Create HTML version for email service compatibility
            html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <p style="color: #333; white-space: pre-line;">{body}</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em;">
      You're receiving this because you enabled coaching check-ins in your InDE preferences.
      To stop receiving these, visit your preferences and turn off 'Coaching Check-ins'.
    </p>
  </div>
</body>
</html>
            """.strip()

            result = _send_email(
                to_address=to_email,
                subject=subject,
                html_body=html_body,
                text_body=full_body,
            )

            if result:
                logger.info(
                    f"Re-engagement sent: to={to_email[:4]}***@***, "
                    f"subject='{subject[:50]}', "
                    f"pursuit={metadata.get('pursuit_id') if metadata else 'unknown'}"
                )
            return bool(result)

        except Exception as e:
            logger.error(f"Re-engagement delivery failed for {to_email[:4]}***: {e}")
            return False
