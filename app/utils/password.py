from passlib import pwd
from passlib.context import CryptContext
from passlib.hash import sha256_crypt, md5_crypt, bcrypt

pwd_context = CryptContext(
    schemes=["sha256_crypt", "md5_crypt", "bcrypt", "plaintext"],
    default="sha256_crypt",
    sha256_crypt__rounds=80000,
    deprecated=["md5_crypt", "plaintext"],
    truncate_error=True
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return plain_password == hashed_password


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_password() -> str:
    return pwd.genword()