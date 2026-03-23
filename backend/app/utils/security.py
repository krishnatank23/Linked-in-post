from passlib.context import CryptContext

try:
    import bcrypt as _bcrypt
except Exception:  # pragma: no cover - optional fallback
    _bcrypt = None

# Use pbkdf2_sha256 for broad runtime compatibility (avoids bcrypt backend issues on some environments).
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    if not hashed_password:
        return False

    # Support legacy bcrypt hashes generated before pbkdf2 migration.
    if hashed_password.startswith("$2") and _bcrypt is not None:
        try:
            return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
