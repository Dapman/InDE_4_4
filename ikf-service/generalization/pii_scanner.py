"""
InDE v3.2 - PII Scanner
Post-generalization PII validation gate.

Checks for residual PII that generalization stages may have missed.
Packages with HIGH-confidence PII cannot be approved without override.
"""

import json
import re
import logging
from typing import Dict, List

logger = logging.getLogger("inde.ikf.pii_scanner")


class PIIScanner:
    """
    Post-generalization PII validation gate.

    Checks for residual PII that generalization stages may have missed.
    Packages with HIGH-confidence PII cannot be approved without override.
    """

    # Regex patterns for common PII
    PATTERNS = {
        "email": {
            "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "confidence": "HIGH",
            "description": "Email address"
        },
        "phone_us": {
            "pattern": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "confidence": "MEDIUM",
            "description": "US phone number"
        },
        "phone_intl": {
            "pattern": r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
            "confidence": "MEDIUM",
            "description": "International phone number"
        },
        "ssn": {
            "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
            "confidence": "HIGH",
            "description": "Social Security Number"
        },
        "url": {
            "pattern": r'https?://[^\s<>"{}|\\^`\[\]]+',
            "confidence": "LOW",
            "description": "URL/web address"
        },
        "ip_address": {
            "pattern": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "confidence": "MEDIUM",
            "description": "IP address"
        },
        "credit_card": {
            "pattern": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "confidence": "HIGH",
            "description": "Credit card number"
        },
        "date_of_birth": {
            "pattern": r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
            "confidence": "MEDIUM",
            "description": "Date (potential DOB)"
        },
    }

    # Patterns that are likely false positives after generalization
    FALSE_POSITIVE_PATTERNS = [
        r'\[email redacted\]',
        r'\[phone redacted\]',
        r'\[url redacted\]',
        r'\[SSN redacted\]',
        r'\[IP redacted\]',
        r'\[Person\]',
        r'\[Organization\]',
        r'\[amount\]',
    ]

    def scan(self, data: dict) -> dict:
        """
        Scan generalized data for residual PII.

        Args:
            data: Generalized data to scan

        Returns: {
            'passed': bool,
            'warnings': [{'type': str, 'match': str, 'confidence': str}],
            'high_confidence_flags': [str]
        }
        """
        text = json.dumps(data, default=str)

        # Remove known false positives
        clean_text = text
        for fp_pattern in self.FALSE_POSITIVE_PATTERNS:
            clean_text = re.sub(fp_pattern, '', clean_text)

        warnings = []
        high_flags = []

        for pii_type, config in self.PATTERNS.items():
            pattern = config["pattern"]
            confidence = config["confidence"]

            matches = re.findall(pattern, clean_text)
            for match in matches:
                # Skip common false positives
                if self._is_false_positive(pii_type, match):
                    continue

                # Truncate long matches for display
                display_match = match[:20] + "..." if len(match) > 20 else match

                warnings.append({
                    "type": pii_type,
                    "match": display_match,
                    "confidence": confidence,
                    "description": config["description"]
                })

                if confidence == "HIGH":
                    high_flags.append(f"{pii_type}: {match[:10]}...")

        # Log results
        if warnings:
            logger.warning(f"PII scan found {len(warnings)} potential issues "
                          f"({len(high_flags)} HIGH confidence)")
        else:
            logger.info("PII scan passed - no issues found")

        return {
            "passed": len(high_flags) == 0,
            "warnings": warnings,
            "high_confidence_flags": high_flags
        }

    def _is_false_positive(self, pii_type: str, match: str) -> bool:
        """Check if a match is likely a false positive."""
        # IP addresses that are local/private
        if pii_type == "ip_address":
            if match.startswith("127.") or match.startswith("192.168.") or match.startswith("10."):
                return True
            # Version numbers like "3.2.0"
            if re.match(r'^\d+\.\d+\.\d+$', match):
                return True

        # URLs that are example/placeholder URLs
        if pii_type == "url":
            if any(x in match.lower() for x in ["example.com", "localhost", "test.com"]):
                return True

        # Phone-like patterns that are actually IDs
        if pii_type == "phone_us":
            # Skip if surrounded by non-phone context
            pass

        return False

    def scan_text(self, text: str) -> dict:
        """
        Scan a text string for PII.

        Args:
            text: Text to scan

        Returns: Same as scan()
        """
        return self.scan({"text": text})

    def get_scan_summary(self, scan_result: dict) -> str:
        """
        Generate human-readable summary of scan results.

        Args:
            scan_result: Result from scan()

        Returns: Summary string
        """
        if scan_result["passed"]:
            if scan_result["warnings"]:
                return (f"PII scan passed with {len(scan_result['warnings'])} low-confidence warnings. "
                       "Human review recommended.")
            return "PII scan passed - no issues detected."

        return (f"PII scan FAILED: {len(scan_result['high_confidence_flags'])} "
               f"high-confidence PII detected. Review required before approval.")
