"""
Secure credential management for Monarch Money.

Stores encrypted credentials in ~/.finance_pui/credentials.enc
Uses Fernet symmetric encryption with a user-provided password.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict
from getpass import getpass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class CredentialManager:
    """
    Manages encrypted Monarch Money credentials.

    Credentials are stored in ~/.finance_pui/credentials.enc
    and encrypted with a user-provided password using Fernet.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize credential manager.

        Args:
            config_dir: Optional custom config directory.
                       Defaults to ~/.finance_pui
        """
        if config_dir is None:
            config_dir = Path.home() / ".finance_pui"

        self.config_dir = config_dir
        self.credentials_file = config_dir / "credentials.enc"
        self.salt_file = config_dir / "salt"

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(mode=0o700, exist_ok=True)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: User password
            salt: Cryptographic salt

        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _get_or_create_salt(self) -> bytes:
        """
        Get existing salt or create new one.

        Returns:
            16-byte salt
        """
        if self.salt_file.exists():
            with open(self.salt_file, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, "wb") as f:
                f.write(salt)
            # Ensure only user can read
            os.chmod(self.salt_file, 0o600)
            return salt

    def credentials_exist(self) -> bool:
        """Check if credentials file exists."""
        return self.credentials_file.exists()

    def save_credentials(
        self, email: str, password: str, mfa_secret: str, encryption_password: Optional[str] = None
    ) -> None:
        """
        Save encrypted credentials to disk.

        Args:
            email: Monarch Money email
            password: Monarch Money password
            mfa_secret: OTP/TOTP secret for 2FA
            encryption_password: Password to encrypt credentials.
                                If None, will prompt user.
        """
        # Get encryption password
        if encryption_password is None:
            print("Set a password to encrypt your Monarch credentials:")
            encryption_password = getpass("Encryption password: ")
            confirm = getpass("Confirm password: ")

            if encryption_password != confirm:
                raise ValueError("Passwords do not match!")

        # Get or create salt
        salt = self._get_or_create_salt()

        # Derive encryption key
        key = self._derive_key(encryption_password, salt)
        fernet = Fernet(key)

        # Prepare credentials
        credentials = {"email": email, "password": password, "mfa_secret": mfa_secret}

        # Encrypt and save
        encrypted = fernet.encrypt(json.dumps(credentials).encode())

        with open(self.credentials_file, "wb") as f:
            f.write(encrypted)

        # Ensure only user can read
        os.chmod(self.credentials_file, 0o600)

        print(f"✓ Credentials saved to {self.credentials_file}")

    def load_credentials(self, encryption_password: Optional[str] = None) -> Dict[str, str]:
        """
        Load and decrypt credentials from disk.

        Args:
            encryption_password: Password to decrypt credentials.
                                If None, will prompt user.

        Returns:
            Dictionary with 'email', 'password', and 'mfa_secret' keys

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If password is incorrect
        """
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n"
                "Run with --setup-credentials to create one."
            )

        # Get encryption password
        if encryption_password is None:
            encryption_password = getpass("Encryption password: ")

        # Load salt
        salt = self._get_or_create_salt()

        # Derive encryption key
        key = self._derive_key(encryption_password, salt)
        fernet = Fernet(key)

        # Load and decrypt
        with open(self.credentials_file, "rb") as f:
            encrypted = f.read()

        try:
            decrypted = fernet.decrypt(encrypted)
            credentials = json.loads(decrypted.decode())
            return credentials
        except InvalidToken:
            raise ValueError("Incorrect password!")

    def delete_credentials(self) -> None:
        """Delete stored credentials."""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
            print(f"✓ Credentials deleted from {self.credentials_file}")

        if self.salt_file.exists():
            self.salt_file.unlink()


def setup_credentials_interactive() -> None:
    """
    Interactive setup for storing Monarch credentials.

    This walks the user through entering their credentials
    and setting up encryption.
    """
    print("=" * 70)
    print("Monarch Money Credential Setup")
    print("=" * 70)
    print()
    print("This will securely store your Monarch Money credentials")
    print("encrypted with a password of your choice.")
    print()
    print("IMPORTANT: You'll need your 2FA/OTP secret key for automatic login.")
    print("This is the BASE32 secret shown when you first set up 2FA")
    print("(usually a long string like: JBSWY3DPEHPK3PXP)")
    print()
    print("How to find your OTP secret:")
    print("  1. Log into Monarch Money on the web")
    print("  2. Go to Settings -> Security")
    print("  3. Disable 2FA, then re-enable it")
    print("  4. When shown the QR code, click 'Can't scan?' or 'Manual entry'")
    print("  5. Copy the secret key (base32 string)")
    print()
    print("=" * 70)
    print()

    # Get Monarch credentials
    email = input("Monarch Money email: ")
    password = getpass("Monarch Money password: ")

    print()
    mfa_secret = getpass("2FA/TOTP Secret Key: ").strip().replace(" ", "").upper()

    # Save credentials
    manager = CredentialManager()
    manager.save_credentials(email, password, mfa_secret)

    print()
    print("=" * 70)
    print("✓ Setup Complete!")
    print("=" * 70)
    print()
    print(f"Your credentials are encrypted and stored at:")
    print(f"  {manager.credentials_file}")
    print()
    print("Next steps:")
    print("  1. Run the TUI: uv run python -m monarch_tui")
    print("  2. You'll only need to enter your encryption password")
    print()
    print("To reset credentials:")
    print(f"  rm {manager.credentials_file}")
    print("  uv run monarch-setup")
    print()
    print("=" * 70)


if __name__ == "__main__":
    # Allow running this module directly to set up credentials
    setup_credentials_interactive()
