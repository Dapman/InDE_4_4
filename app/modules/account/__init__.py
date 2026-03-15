"""
InDE Account Management Module
v3.12: Account Trust & Completeness

Provides:
- Account deletion with cooling-off period
- Password reset with secure tokens
"""

from .deletion import AccountDeletionService
from .password_reset import PasswordResetService

__all__ = ['AccountDeletionService', 'PasswordResetService']
