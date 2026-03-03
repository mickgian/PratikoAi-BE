"""TOTP 2FA device model (P2)."""

from sqlmodel import Field

from app.models.base import BaseModel


class TOTPDevice(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores TOTP authenticator device configuration per user.

    Attributes:
        id: Auto-increment primary key
        user_id: FK to user (one active device per user)
        secret_encrypted: Fernet-encrypted TOTP secret
        name: Human-readable device name
        confirmed: Whether the user has confirmed setup with a valid code
        backup_codes_json: JSON-serialized list of remaining backup codes
        created_at: Inherited from BaseModel
    """

    __tablename__ = "totp_device"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    secret_encrypted: str = Field(max_length=512)
    name: str = Field(default="Autenticatore", max_length=100)
    confirmed: bool = Field(default=False)
    backup_codes_json: str | None = Field(default=None, max_length=512)
