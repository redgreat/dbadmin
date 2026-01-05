from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional
from app.settings.config import settings


class PasswordEncryption:
    """密码加密解密工具类"""
    
    def __init__(self, salt: Optional[bytes] = None):
        """初始化加密工具"""
        if salt is None:
            salt_str = settings.DB_PASSWORD_SALT
            self.salt = salt_str.encode('utf-8')
        else:
            self.salt = salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b'dbadmin_password_key'))
        self.cipher_suite = Fernet(key)
    
    def encrypt_password(self, password: str) -> str:
        """加密密码"""
        if not password:
            return ''
        
        encrypted_password = self.cipher_suite.encrypt(password.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_password).decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        if not encrypted_password:
            return ''
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_password.encode('utf-8'))
            decrypted_password = self.cipher_suite.decrypt(encrypted_data)
            return decrypted_password.decode('utf-8')
        except Exception:
            return ''


password_encryption = PasswordEncryption()


def encrypt_password(password: str) -> str:
    """加密密码的便捷函数"""
    return password_encryption.encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """解密密码的便捷函数"""
    return password_encryption.decrypt_password(encrypted_password)