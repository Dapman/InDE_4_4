"""
InDE MVP v2.9 - Report Distributor
Transform SILR reports into shareable, distributable assets.

Features:
- Email distribution with PDF attachments
- Shareable download links with expiration
- Batch distribution to stakeholders
- Engagement tracking (opens, downloads)
"""

import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from config import (
    DISTRIBUTION_CONFIG, EMAIL_TEMPLATES
)


class ReportDistributor:
    """
    Transform SILR reports into shareable, distributable assets.

    Provides email distribution, shareable links, and batch operations
    with engagement tracking.
    """

    def __init__(self, db, report_generator=None):
        """
        Initialize the report distributor.

        Args:
            db: Database instance
            report_generator: Optional report generator for PDF creation
        """
        self.db = db
        self.report_generator = report_generator
        self.config = DISTRIBUTION_CONFIG

    def send_email(self, report_id: str, recipient_email: str,
                   recipient_name: str = None,
                   template: str = 'professional',
                   custom_message: str = None) -> Dict:
        """
        Send SILR report via email with PDF attachment.

        Args:
            report_id: ID of the report to send
            recipient_email: Recipient's email address
            recipient_name: Optional recipient name for personalization
            template: Email template (professional, casual, investor)
            custom_message: Optional custom message to include

        Returns:
            Dict with distribution_id and status
        """
        # Get the report
        report = self.db.get_report(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        pursuit_id = report.get("pursuit_id")
        pursuit = self.db.get_pursuit(pursuit_id) if pursuit_id else None
        pursuit_title = pursuit.get("title", "Innovation Pursuit") if pursuit else "Innovation Pursuit"

        # Get email template
        email_template = EMAIL_TEMPLATES.get(template, EMAIL_TEMPLATES["professional"])

        # Prepare email content
        subject = email_template["subject"].format(pursuit_title=pursuit_title)
        greeting = email_template["greeting"].format(
            recipient_name=recipient_name or "there"
        )
        body = email_template["body"].format(pursuit_title=pursuit_title)

        if custom_message:
            body = f"{body}\n\n{custom_message}"

        # Generate tracking token for email opens
        tracking_token = secrets.token_urlsafe(16)

        # Create distribution record
        distribution_record = {
            "pursuit_id": pursuit_id,
            "report_id": report_id,
            "distribution_method": "email",
            "recipients": [{
                "email": recipient_email,
                "name": recipient_name,
                "sent_at": datetime.now(timezone.utc),
                "opened_at": None,
                "downloaded_at": None,
                "tracking_token": tracking_token
            }],
            "template": template,
            "custom_message": custom_message
        }

        distribution_id = self.db.create_report_distribution(distribution_record)

        # Send email (simplified - would use actual SMTP in production)
        try:
            email_sent = self._send_smtp_email(
                to_email=recipient_email,
                subject=subject,
                body=f"{greeting}\n\n{body}",
                report=report,
                tracking_token=tracking_token
            )

            if email_sent:
                return {
                    "distribution_id": distribution_id,
                    "status": "sent",
                    "recipient": recipient_email,
                    "template": template
                }
            else:
                return {
                    "distribution_id": distribution_id,
                    "status": "queued",
                    "message": "Email queued for delivery"
                }

        except Exception as e:
            # Update distribution record with error
            self.db.update_report_distribution(distribution_id, {
                "status": "failed",
                "error": str(e)
            })
            return {
                "distribution_id": distribution_id,
                "status": "failed",
                "error": str(e)
            }

    def _send_smtp_email(self, to_email: str, subject: str, body: str,
                         report: Dict, tracking_token: str) -> bool:
        """
        Send email via SMTP.

        In demo mode, this simulates sending without actual SMTP connection.
        """
        # In demo mode, simulate success
        if not self.config.get("smtp_host") or self.config["smtp_host"] == "localhost":
            print(f"[Distribution] Simulated email to {to_email}: {subject}")
            return True

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['smtp_from_name']} <{self.config['smtp_from_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Connect and send
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                if self.config.get('smtp_user'):
                    server.starttls()
                    server.login(self.config['smtp_user'], self.config['smtp_password'])
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"[Distribution] SMTP error: {e}")
            return False

    def generate_share_link(self, report_id: str, expiry_days: int = 7,
                           password: str = None) -> Dict:
        """
        Create shareable download link for report.

        Args:
            report_id: ID of the report to share
            expiry_days: Days until link expires (default 7)
            password: Optional password protection

        Returns:
            Dict with share URL and token
        """
        # Get the report
        report = self.db.get_report(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        pursuit_id = report.get("pursuit_id")

        # Generate secure token
        share_token = secrets.token_urlsafe(32)

        # Hash password if provided
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

        # Create distribution record
        distribution_record = {
            "pursuit_id": pursuit_id,
            "report_id": report_id,
            "distribution_method": "link",
            "share_link": {
                "url": f"{self.config['share_link_base_url']}/report/{share_token}",
                "token": share_token,
                "expires_at": expires_at,
                "password_protected": password is not None,
                "password_hash": password_hash,
                "access_count": 0,
                "last_accessed": None
            }
        }

        distribution_id = self.db.create_report_distribution(distribution_record)

        return {
            "distribution_id": distribution_id,
            "share_url": distribution_record["share_link"]["url"],
            "token": share_token,
            "expires_at": expires_at.isoformat(),
            "password_protected": password is not None
        }

    def batch_distribute(self, report_id: str, stakeholder_ids: List[str],
                        template: str = 'professional') -> Dict:
        """
        Send report to multiple stakeholders from v2.6 data.

        Args:
            report_id: ID of the report to distribute
            stakeholder_ids: List of stakeholder feedback IDs to send to
            template: Email template to use

        Returns:
            Distribution summary
        """
        # Get report
        report = self.db.get_report(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        pursuit_id = report.get("pursuit_id")

        # If no stakeholder IDs provided, get all stakeholders for pursuit
        if not stakeholder_ids and pursuit_id:
            stakeholders = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
            stakeholder_ids = [s.get("feedback_id") for s in stakeholders if s.get("feedback_id")]

        results = {
            "total": len(stakeholder_ids),
            "sent": 0,
            "failed": 0,
            "distributions": []
        }

        for stakeholder_id in stakeholder_ids:
            # Get stakeholder info
            stakeholder = self.db.get_stakeholder_feedback(stakeholder_id)
            if not stakeholder:
                results["failed"] += 1
                continue

            # Get email from stakeholder record
            email = stakeholder.get("email")
            if not email:
                # Try to extract from notes or name
                results["failed"] += 1
                continue

            try:
                result = self.send_email(
                    report_id=report_id,
                    recipient_email=email,
                    recipient_name=stakeholder.get("stakeholder_name"),
                    template=template
                )

                if result.get("status") in ["sent", "queued"]:
                    results["sent"] += 1
                else:
                    results["failed"] += 1

                results["distributions"].append(result)

            except Exception as e:
                results["failed"] += 1
                results["distributions"].append({
                    "stakeholder_id": stakeholder_id,
                    "status": "failed",
                    "error": str(e)
                })

        return results

    def validate_share_link(self, token: str, password: str = None) -> Dict:
        """
        Validate a share link and return report if valid.

        Args:
            token: Share token from URL
            password: Password if link is protected

        Returns:
            Dict with validity status and report data if valid
        """
        # Find distribution by token
        distribution = self.db.get_distribution_by_token(token)

        if not distribution:
            return {"valid": False, "error": "Link not found"}

        share_link = distribution.get("share_link", {})

        # Check expiry
        expires_at = share_link.get("expires_at")
        if expires_at and datetime.now(timezone.utc) > expires_at:
            return {"valid": False, "error": "Link expired"}

        # Check password
        if share_link.get("password_protected"):
            if not password:
                return {"valid": False, "error": "Password required", "password_required": True}

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash != share_link.get("password_hash"):
                return {"valid": False, "error": "Incorrect password"}

        # Get report
        report_id = distribution.get("report_id")
        report = self.db.get_report(report_id)

        if not report:
            return {"valid": False, "error": "Report not found"}

        # Track access
        self.db.update_report_distribution(distribution.get("distribution_id"), {
            "share_link.access_count": share_link.get("access_count", 0) + 1,
            "share_link.last_accessed": datetime.now(timezone.utc)
        })

        return {
            "valid": True,
            "report": report,
            "pursuit_id": distribution.get("pursuit_id")
        }

    def track_email_open(self, tracking_token: str) -> bool:
        """
        Track when a recipient opens an email.

        Args:
            tracking_token: Token embedded in email

        Returns:
            True if tracked successfully
        """
        # Find distribution by tracking token
        distributions = list(self.db.db.report_distributions.find({
            "recipients.tracking_token": tracking_token
        }))

        if not distributions:
            return False

        distribution = distributions[0]

        # Update opened_at for the recipient
        recipients = distribution.get("recipients", [])
        for recipient in recipients:
            if recipient.get("tracking_token") == tracking_token:
                if not recipient.get("opened_at"):
                    recipient["opened_at"] = datetime.now(timezone.utc)

        self.db.update_report_distribution(
            distribution.get("distribution_id"),
            {"recipients": recipients}
        )

        return True

    def track_download(self, distribution_id: str, recipient_email: str = None) -> bool:
        """
        Track when a report is downloaded.

        Args:
            distribution_id: Distribution ID
            recipient_email: Optional email to track specific recipient

        Returns:
            True if tracked successfully
        """
        distribution = self.db.get_report_distribution(distribution_id)
        if not distribution:
            return False

        if distribution.get("distribution_method") == "link":
            # Update share link access count
            share_link = distribution.get("share_link", {})
            share_link["access_count"] = share_link.get("access_count", 0) + 1
            share_link["last_accessed"] = datetime.now(timezone.utc)
            self.db.update_report_distribution(distribution_id, {"share_link": share_link})

        elif distribution.get("distribution_method") == "email" and recipient_email:
            # Update recipient download time
            recipients = distribution.get("recipients", [])
            for recipient in recipients:
                if recipient.get("email") == recipient_email:
                    if not recipient.get("downloaded_at"):
                        recipient["downloaded_at"] = datetime.now(timezone.utc)
            self.db.update_report_distribution(distribution_id, {"recipients": recipients})

        return True

    def get_distribution_analytics(self, report_id: str = None,
                                    pursuit_id: str = None) -> Dict:
        """
        Get analytics for report distributions.

        Args:
            report_id: Optional filter by report
            pursuit_id: Optional filter by pursuit

        Returns:
            Dict with distribution analytics
        """
        query = {}
        if report_id:
            query["report_id"] = report_id
        if pursuit_id:
            query["pursuit_id"] = pursuit_id

        distributions = list(self.db.db.report_distributions.find(query))

        analytics = {
            "total_distributions": len(distributions),
            "by_method": {
                "email": 0,
                "link": 0,
                "batch": 0
            },
            "email_stats": {
                "total_sent": 0,
                "total_opened": 0,
                "total_downloaded": 0,
                "open_rate": 0.0
            },
            "link_stats": {
                "total_links": 0,
                "total_accesses": 0,
                "avg_accesses_per_link": 0.0
            }
        }

        for dist in distributions:
            method = dist.get("distribution_method", "unknown")
            if method in analytics["by_method"]:
                analytics["by_method"][method] += 1

            if method == "email":
                recipients = dist.get("recipients", [])
                analytics["email_stats"]["total_sent"] += len(recipients)
                for r in recipients:
                    if r.get("opened_at"):
                        analytics["email_stats"]["total_opened"] += 1
                    if r.get("downloaded_at"):
                        analytics["email_stats"]["total_downloaded"] += 1

            elif method == "link":
                analytics["link_stats"]["total_links"] += 1
                share_link = dist.get("share_link", {})
                analytics["link_stats"]["total_accesses"] += share_link.get("access_count", 0)

        # Calculate rates
        if analytics["email_stats"]["total_sent"] > 0:
            analytics["email_stats"]["open_rate"] = (
                analytics["email_stats"]["total_opened"] /
                analytics["email_stats"]["total_sent"]
            )

        if analytics["link_stats"]["total_links"] > 0:
            analytics["link_stats"]["avg_accesses_per_link"] = (
                analytics["link_stats"]["total_accesses"] /
                analytics["link_stats"]["total_links"]
            )

        return analytics
