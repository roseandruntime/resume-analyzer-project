"""
Authentication helpers for Resume Analyzer.

Public registration is limited to student and recruiter roles.
Admin accounts must be created by a trusted administrator, not through
the public registration form. Uses PBKDF2-HMAC-SHA256 password hashing.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3

from database import get_connection

_HASH_NAME = "sha256"
_ITERATIONS = 310_000
_SALT_BYTES = 16
_ALLOWED_PUBLIC_ROLES = {"student", "recruiter"}


def _hash_password(password, salt=None):
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    salt = salt or secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS
    )
    return salt.hex(), digest.hex()


def _verify_password(password, salt_hex, expected_hash):
    try:
        salt = bytes.fromhex(salt_hex)
        _, actual_hash = _hash_password(password, salt)
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def _validate_email(email):
    email = (email or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")
    return email


def register_user(full_name, email, password, role="student"):
    """Register a student or recruiter. Returns (success, message)."""
    full_name = (full_name or "").strip()
    if not full_name:
        return False, "Full name is required."

    try:
        email = _validate_email(email)
        salt_hex, password_hash = _hash_password(password)
    except ValueError as exc:
        return False, str(exc)

    role = (role or "").strip().lower()
    if role not in _ALLOWED_PUBLIC_ROLES:
        return False, "Public registration is allowed only for student or recruiter accounts."

    try:
        with get_connection() as connection:
            connection.execute(
                """INSERT INTO users
                   (full_name, email, password_hash, role)
                   VALUES (?, ?, ?, ?)""",
                (full_name, email, f"{salt_hex}${password_hash}", role),
            )
        return True, "Account created successfully. You can now log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def authenticate_user(email, password):
    """Return safe user details on success, otherwise None."""
    try:
        email = _validate_email(email)
    except ValueError:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """SELECT user_id, full_name, email, password_hash, role, is_active
               FROM users WHERE email = ?""",
            (email,),
        ).fetchone()

    if row is None or row["is_active"] != 1:
        return None

    try:
        salt_hex, expected_hash = row["password_hash"].split("$", 1)
    except (ValueError, AttributeError):
        return None

    if not _verify_password(password, salt_hex, expected_hash):
        return None

    return {
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
    }


def create_admin_account(full_name, email, password):
    """
    Trusted local setup helper. Never expose this function in the public UI.
    """
    full_name = (full_name or "").strip()
    if not full_name:
        return False, "Full name is required."

    try:
        email = _validate_email(email)
        salt_hex, password_hash = _hash_password(password)
    except ValueError as exc:
        return False, str(exc)

    try:
        with get_connection() as connection:
            connection.execute(
                """INSERT INTO users
                   (full_name, email, password_hash, role)
                   VALUES (?, ?, ?, 'admin')""",
                (full_name, email, f"{salt_hex}${password_hash}"),
            )
        return True, "Admin account created successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
