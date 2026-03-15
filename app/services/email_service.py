"""
InDE Email Service
Handles all outbound email with graceful degradation when SMTP is not configured.
Supports SendGrid (primary) and SMTP (fallback) providers.

v3.12: Account Trust & Completeness
v3.16: Added SendGrid support, welcome emails with GII, invitation emails
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# Email Provider Configuration
EMAIL_PROVIDER = os.environ.get("INDE_EMAIL_PROVIDER", "smtp")  # sendgrid or smtp
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

# SMTP Configuration from environment
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_ADDRESS = os.environ.get("SMTP_FROM_ADDRESS", "noreply@indeverse.com")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "InDE Innovation Platform")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
APP_BASE_URL = os.environ.get("INDE_BASE_URL", os.environ.get("APP_BASE_URL", "http://localhost:5173")).rstrip("/")


def is_email_configured() -> bool:
    """Return True if email provider (SendGrid or SMTP) is configured."""
    if EMAIL_PROVIDER == "sendgrid":
        return bool(SENDGRID_API_KEY)
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)


def _send_email(to_address: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Internal email sender. Returns True on success, False on failure.
    Routes to SendGrid or SMTP based on configuration.
    Never raises — logs errors instead.
    """
    if not is_email_configured():
        logger.warning(f"Email not sent to {to_address}: Email service not configured.")
        return False

    try:
        if EMAIL_PROVIDER == "sendgrid":
            return _send_via_sendgrid(to_address, subject, html_body)
        else:
            return _send_via_smtp(to_address, subject, html_body, text_body)
    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {e}")
        return False


def _send_via_sendgrid(to_address: str, subject: str, html_body: str) -> bool:
    """Send email via SendGrid API."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        logger.error("sendgrid package not installed. Run: pip install sendgrid")
        return False

    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    message = Mail(
        from_email=Email(SMTP_FROM_ADDRESS, SMTP_FROM_NAME),
        to_emails=To(to_address),
        subject=subject,
        html_content=Content("text/html", html_body)
    )
    response = sg.client.mail.send.post(request_body=message.get())
    success = response.status_code in (200, 201, 202)
    if success:
        logger.info(f"Email sent via SendGrid to {to_address}: {subject}")
    else:
        logger.error(f"SendGrid error {response.status_code}: {response.body}")
    return success


def _send_via_smtp(to_address: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_ADDRESS}>"
    msg["To"] = to_address

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if SMTP_USE_TLS:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)

    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(SMTP_FROM_ADDRESS, to_address, msg.as_string())
    server.quit()

    logger.info(f"Email sent via SMTP to {to_address}: {subject}")
    return True


def send_password_reset_email(to_address: str, display_name: str, reset_token: str) -> bool:
    """Send password reset email with secure reset link."""
    reset_url = f"{APP_BASE_URL}/reset-password?token={reset_token}"

    subject = "Reset your InDE password"

    text_body = f"""
Hi {display_name},

You requested a password reset for your InDE account.

Click this link to reset your password (expires in 1 hour):
{reset_url}

If you did not request a password reset, you can ignore this email.
Your password will not be changed.

The InDE Team
    """.strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2 style="color: #1A2B5C; margin-top: 0;">Reset your InDE password</h2>
    <p style="color: #333;">Hi {display_name},</p>
    <p style="color: #333;">You requested a password reset for your InDE account.</p>
    <p style="text-align: center; margin: 32px 0;">
      <a href="{reset_url}"
         style="background: #0097A7; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; display: inline-block;
                font-weight: 500;">
        Reset Password
      </a>
    </p>
    <p style="color: #666; font-size: 0.9em;">
      This link expires in 1 hour.<br>
      If you didn't request this, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em;">
      Or copy this URL: <a href="{reset_url}" style="color: #0097A7;">{reset_url}</a>
    </p>
  </div>
</body>
</html>
    """.strip()

    return _send_email(to_address, subject, html_body, text_body)


def send_deletion_confirmation_email(
    to_address: str,
    display_name: str,
    cancellation_token: str,
    scheduled_for: str
) -> bool:
    """Send account deletion confirmation with cancellation link."""
    cancel_url = f"{APP_BASE_URL}/cancel-deletion?token={cancellation_token}"

    subject = "Your InDE account deletion has been scheduled"

    text_body = f"""
Hi {display_name},

Your InDE account has been scheduled for deletion on {scheduled_for}.

To cancel this deletion and restore your account, click here within 14 days:
{cancel_url}

What will be deleted:
- Your account credentials and profile
- Your coaching sessions and conversation history
- Your pursuit data and artifacts
- Your personal innovation memory records

What will be preserved:
- Anonymized innovation patterns you contributed to the collective knowledge fabric
  (these cannot be attributed to you and are not personal data under GDPR)

If you did not request account deletion, click the link above immediately.

The InDE Team
    """.strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2 style="color: #c53030; margin-top: 0;">Account deletion scheduled</h2>
    <p style="color: #333;">Hi {display_name},</p>
    <p style="color: #333;">Your InDE account has been scheduled for deletion on <strong>{scheduled_for}</strong>.</p>
    <p style="text-align: center; margin: 32px 0;">
      <a href="{cancel_url}"
         style="background: #D4A017; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; display: inline-block;
                font-weight: 500;">
        Cancel Deletion &amp; Keep My Account
      </a>
    </p>
    <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 6px; padding: 16px; margin: 24px 0;">
      <p style="color: #c53030; font-weight: 500; margin-top: 0;">What will be deleted:</p>
      <ul style="color: #444; margin-bottom: 0;">
        <li>Your account credentials and profile</li>
        <li>Your coaching sessions and conversation history</li>
        <li>Your pursuit data and artifacts</li>
        <li>Your personal innovation memory records</li>
      </ul>
    </div>
    <div style="background: #f0fff4; border: 1px solid #c6f6d5; border-radius: 6px; padding: 16px; margin: 24px 0;">
      <p style="color: #276749; font-weight: 500; margin-top: 0;">What will be preserved:</p>
      <ul style="color: #444; margin-bottom: 0;">
        <li>Anonymized innovation patterns contributed to the collective knowledge fabric
            (not personal data — cannot be attributed to you)</li>
      </ul>
    </div>
    <p style="color: #c53030; font-size: 0.9em; font-weight: 500;">
      If you did not request this, click the cancellation button above immediately.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em;">
      Cancel URL: <a href="{cancel_url}" style="color: #D4A017;">{cancel_url}</a>
    </p>
  </div>
</body>
</html>
    """.strip()

    return _send_email(to_address, subject, html_body, text_body)


def send_deletion_completed_email(to_address: str, display_name: str) -> bool:
    """Send notification that account has been permanently deleted."""
    subject = "Your InDE account has been deleted"

    text_body = f"""
Hi {display_name},

Your InDE account has been permanently deleted as scheduled.

All personal data has been removed in accordance with GDPR/CCPA requirements.
Anonymized innovation patterns you contributed remain in the collective knowledge fabric
to benefit other innovators, but they cannot be traced back to you.

Thank you for being part of the InDE community.

If you ever want to return, you're welcome to create a new account.

The InDE Team
    """.strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2 style="color: #1A2B5C; margin-top: 0;">Your InDE account has been deleted</h2>
    <p style="color: #333;">Hi {display_name},</p>
    <p style="color: #333;">Your InDE account has been permanently deleted as scheduled.</p>
    <p style="color: #666;">
      All personal data has been removed in accordance with GDPR/CCPA requirements.
      Anonymized innovation patterns you contributed remain in the collective knowledge fabric
      to benefit other innovators, but they cannot be traced back to you.
    </p>
    <p style="color: #333;">Thank you for being part of the InDE community.</p>
    <p style="color: #666; font-style: italic;">
      If you ever want to return, you're welcome to create a new account.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em; text-align: center;">
      The InDE Team
    </p>
  </div>
</body>
</html>
    """.strip()

    return _send_email(to_address, subject, html_body, text_body)


def send_welcome_email(to_address: str, display_name: str, gii_id: str) -> bool:
    """
    Send welcome email with GII (Global Innovator Identifier).
    Called immediately after successful registration.
    v3.16: Added GII surfacing.
    """
    subject = "Welcome to InDE — Your Innovation Identity is Ready"

    text_body = f"""
Hi {display_name},

Welcome to InDE! Your innovation environment is ready.

You've been assigned a Global Innovator Identifier (GII):
{gii_id}

Your GII is a persistent identity that follows your work across pursuits,
organizations, and career transitions. Like a patent inventor record,
it establishes your authorship of every idea, artifact, and insight
you create in InDE.

Keep a record of your GII — it belongs to you.

Get started: {APP_BASE_URL}

The InDE Team
    """.strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2 style="color: #1A2B5C; margin-top: 0;">Welcome to InDE, {display_name}</h2>
    <p style="color: #333;">Your innovation environment is ready. You've been assigned a
    <strong>Global Innovator Identifier (GII)</strong> — a persistent identity
    that follows your work across pursuits, organizations, and career transitions.</p>
    <div style="background: #f0f4ff; border-left: 4px solid #0097A7;
                padding: 16px; margin: 20px 0; border-radius: 4px;">
      <p style="margin: 0; font-size: 12px; color: #666;">Your GII</p>
      <p style="margin: 4px 0; font-family: monospace; font-size: 18px;
                color: #1A2B5C; font-weight: bold;">{gii_id}</p>
      <p style="margin: 8px 0 0; font-size: 12px; color: #666;">
        This identifier belongs to you. Keep a record of it.
      </p>
    </div>
    <p style="color: #333;">Your GII establishes your authorship of every idea, artifact, and
    insight you create in InDE. Like a patent inventor record, it persists
    regardless of where your career takes you.</p>
    <p style="text-align: center; margin: 32px 0;">
      <a href="{APP_BASE_URL}"
         style="background: #0097A7; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; display: inline-block;
                font-weight: 500;">
        Open InDE
      </a>
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em; text-align: center;">
      InDEVerse, Incorporated
    </p>
  </div>
</body>
</html>
    """.strip()

    return _send_email(to_address, subject, html_body, text_body)


def send_invitation_email(
    to_address: str,
    invited_by: str,
    registration_token: str,
    message: Optional[str] = None
) -> bool:
    """
    Send operator-issued invitation with one-time registration link.
    Token expires in 7 days.
    v3.16: New feature.
    """
    invite_url = f"{APP_BASE_URL}/register?invite={registration_token}"
    subject = f"You've been invited to InDE by {invited_by}"

    custom_msg = f'\n\n"{message}"' if message else ""

    text_body = f"""
{invited_by} has invited you to join InDE — an AI-coached innovation environment.
{custom_msg}

Click below to create your account. This invitation link is valid for 7 days
and can only be used once:

{invite_url}

The InDE Team
    """.strip()

    custom_html = f'<p style="font-style: italic; color: #666; padding: 16px; background: #f9f9f9; border-radius: 4px;">"{message}"</p>' if message else ""

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2 style="color: #1A2B5C; margin-top: 0;">You've been invited to InDE</h2>
    <p style="color: #333;"><strong>{invited_by}</strong> has invited you to join InDE —
    an AI-coached innovation environment.</p>
    {custom_html}
    <p style="color: #333;">Click below to create your account. This invitation link is valid for
    <strong>7 days</strong> and can only be used once.</p>
    <p style="text-align: center; margin: 32px 0;">
      <a href="{invite_url}"
         style="background: #0097A7; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; display: inline-block;
                font-weight: 500;">
        Accept Invitation &amp; Create Account
      </a>
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #999; font-size: 0.85em;">
      Or copy this URL: <a href="{invite_url}" style="color: #0097A7;">{invite_url}</a>
    </p>
    <p style="color: #999; font-size: 0.85em; text-align: center;">
      InDEVerse, Incorporated
    </p>
  </div>
</body>
</html>
    """.strip()

    return _send_email(to_address, subject, html_body, text_body)
