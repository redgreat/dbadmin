import os
import warnings
import time
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlsplit

# 过滤oss2库的SyntaxWarning
warnings.filterwarnings(
    "ignore",
    message="invalid escape sequence.*",
    category=SyntaxWarning,
)

import oss2
import requests
from urllib.parse import quote

from app.log import logger
from app.settings import settings


class OSSService:
    _identity_token_cache: Optional[str] = None
    _identity_token_expire_at: float = 0

    @staticmethod
    def is_enabled() -> bool:
        return (
            settings.OSS_ENABLED
            and bool(settings.OSS_BUCKET)
            and bool(settings.OSS_APP_CODE)
            and (bool(settings.OSS_UPLOAD_API_URL) or bool(settings.OSS_DIRECT_DOWNLOAD_BASE_URL))
        )

    @staticmethod
    def _build_object_key(file_name: str) -> str:
        now = datetime.now()
        safe_name = file_name.replace("\\", "_").replace("/", "_").replace(":", "_")
        prefix = settings.OSS_PREFIX.strip("/")
        return f"{prefix}/{now.year}/{now.month:02d}/{now.day:02d}/{safe_name}"

    @staticmethod
    def _extract_download_url(payload: Dict[str, Any]) -> Optional[str]:
        candidates = [
            payload.get("url"),
            payload.get("download_url"),
            payload.get("downloadUrl"),
            payload.get("file_url"),
            payload.get("fileUrl"),
        ]
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        candidates.extend(
            [
                data.get("url"),
                data.get("download_url"),
                data.get("downloadUrl"),
                data.get("file_url"),
                data.get("fileUrl"),
            ]
        )
        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return None

    @staticmethod
    def _extract_object_key(payload: Dict[str, Any]) -> Optional[str]:
        candidates = [
            payload.get("object_key"),
            payload.get("objectKey"),
            payload.get("path"),
            payload.get("key"),
            payload.get("name"),
        ]
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        candidates.extend(
            [
                data.get("object_key"),
                data.get("objectKey"),
                data.get("path"),
                data.get("key"),
                data.get("name"),
            ]
        )
        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return None

    @staticmethod
    def _guess_sre_base_url() -> str:
        """
        从 upload_api_url/direct_download_base_url 提取 SRE OPEN API 的 base 域名。
        """
        for raw in [settings.OSS_UPLOAD_API_URL, settings.OSS_DIRECT_DOWNLOAD_BASE_URL]:
            if not raw:
                continue
            try:
                parsed = urlsplit(raw.strip())
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                continue
        return ""

    @classmethod
    def _get_identity_access_token(cls) -> Optional[str]:
        """
        从认证中心获取 access_token（带简单缓存）。
        """
        now = time.time()
        if cls._identity_token_cache and cls._identity_token_expire_at - now > 60:
            return cls._identity_token_cache

        try:
            identity_url = settings.OSS_IDENTITY_URL
            client_id = settings.OSS_CLIENT_ID
            client_secret = settings.OSS_CLIENT_SECRET
            scope = settings.OSS_SCOPE
            if not all([identity_url, client_id, client_secret, scope]):
                logger.error("[OSS] 认证中心参数不完整(identity_url/client_id/client_secret/scope)")
                return None

            token_payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            timeout = max(int(settings.OSS_REQUEST_TIMEOUT_SECONDS), 5)
            resp = requests.post(identity_url, data=token_payload, headers=headers, timeout=timeout)
            if not resp.ok:
                logger.error(f"[OSS] 获取access token失败: status={resp.status_code}, body={resp.text[:500]}")
                return None

            token_data = resp.json() if resp.text else {}
            access_token = token_data.get("access_token")
            expires_in = int(token_data.get("expires_in") or 3600)
            if not access_token:
                logger.error("[OSS] access_token为空")
                return None

            cls._identity_token_cache = access_token
            cls._identity_token_expire_at = now + max(expires_in, 60)
            return access_token
        except Exception as e:
            logger.error(f"[OSS] 获取access token异常: {e}", exc_info=True)
            return None

    @classmethod
    def _get_sts_token(cls) -> Optional[Dict[str, Any]]:
        """获取STS token"""
        try:
            access_token = cls._get_identity_access_token()
            if not access_token:
                return None

            sre_base_url = cls._guess_sre_base_url()
            if not sre_base_url:
                logger.error("[OSS] 无法解析 SRE OPEN API base url")
                return None

            # 获取STS token
            sts_url = f"{sre_base_url}/api/v1/buckets/sts"
            sts_payload = {
                "bucketName": settings.OSS_BUCKET,
                "appCode": settings.OSS_APP_CODE,
            }
            sts_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            timeout = max(int(settings.OSS_REQUEST_TIMEOUT_SECONDS), 5)
            resp = requests.post(sts_url, json=sts_payload, headers=sts_headers, timeout=timeout)
            if not resp.ok:
                logger.error(f"[OSS] 获取STS token失败: status={resp.status_code}, body={resp.text[:500]}")
                return None
            
            sts_data = resp.json()
            sts_info = sts_data.get("sts")
            if not sts_info:
                logger.error("[OSS] STS信息为空")
                return None
            
            return sts_info
            
        except Exception as e:
            logger.error(f"[OSS] 获取STS token异常: {e}", exc_info=True)
            return None

    @classmethod
    def _get_sts_download_url(cls, object_key: str) -> Optional[str]:
        """
        按文档流程获取下载链接：
        1) 认证中心 token
        2) 调 /api/v1/buckets/stsurl
        """
        if not object_key:
            return None
        try:
            access_token = cls._get_identity_access_token()
            if not access_token:
                return None

            sre_base_url = cls._guess_sre_base_url()
            if not sre_base_url:
                logger.error("[OSS] 无法解析 SRE OPEN API base url")
                return None

            stsurl = f"{sre_base_url}/api/v1/buckets/stsurl"
            payload = {
                "bucketName": settings.OSS_BUCKET,
                "appCode": settings.OSS_APP_CODE,
                "objectName": [object_key],
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            timeout = max(int(settings.OSS_REQUEST_TIMEOUT_SECONDS), 5)
            resp = requests.post(stsurl, json=payload, headers=headers, timeout=timeout)
            if not resp.ok:
                logger.error(f"[OSS] 获取STS下载链接失败: status={resp.status_code}, body={resp.text[:500]}")
                return None

            data = resp.json() if resp.text else {}
            url_obj = data.get("url")
            if isinstance(url_obj, dict):
                # 常见是 { "<object_key>": "<download_url>" }
                if object_key in url_obj and isinstance(url_obj[object_key], str):
                    return url_obj[object_key]
                # 兜底取第一项
                for v in url_obj.values():
                    if isinstance(v, str) and v.strip():
                        return v.strip()
            elif isinstance(url_obj, str) and url_obj.strip():
                return url_obj.strip()

            logger.error(f"[OSS] stsurl返回格式无法识别: {data}")
            return None
        except Exception as exc:
            logger.error(f"[OSS] 获取STS下载链接异常: {exc}", exc_info=True)
            return None

    @classmethod
    def upload_file(cls, local_file_path: str, object_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not cls.is_enabled():
            return None
        if not local_file_path or not os.path.exists(local_file_path):
            return None

        try:
            object_key = object_name or cls._build_object_key(os.path.basename(local_file_path))
            
            # 获取STS token
            sts_info = cls._get_sts_token()
            if not sts_info:
                logger.error("[OSS] 无法获取STS token")
                return None
            
            # 使用STS凭证创建OSS客户端
            auth = oss2.StsAuth(
                sts_info["sts_AccessId"],
                sts_info["sts_AccessKeySecret"], 
                sts_info["securityToken"]
            )
            bucket = oss2.Bucket(auth, sts_info["endpoint"], settings.OSS_BUCKET)
            
            # 上传文件
            with open(local_file_path, "rb") as file_obj:
                result = bucket.put_object(object_key, file_obj)
            
            if result.status != 200:
                logger.error(f"[OSS] 上传失败: status={result.status}")
                return None
            
            # 生成下载URL
            remote_url = cls.sign_download_url(object_key)
            
            logger.info(f"[OSS] 上传成功: bucket={settings.OSS_BUCKET}, key={object_key}")
            return {
                "provider": "aliyun_oss_sts",
                "bucket": settings.OSS_BUCKET,
                "key": object_key,
                "url": remote_url,
                "size": os.path.getsize(local_file_path),
                "uploaded_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"[OSS] 上传异常: {e}")
            return None

    @classmethod
    def sign_download_url(cls, object_key: str, expire_seconds: Optional[int] = None) -> Optional[str]:
        if not object_key:
            return None
        if str(object_key).startswith("http://") or str(object_key).startswith("https://"):
            return object_key
        base_url = (settings.OSS_DIRECT_DOWNLOAD_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            return None
        object_key_safe = quote(object_key.lstrip("/"), safe="/")
        return f"{base_url}/{object_key_safe}"

    @staticmethod
    def extract_oss_meta(execution_json: Optional[dict]) -> Optional[Dict[str, Any]]:
        if not execution_json:
            return None
        storage = execution_json.get("storage")
        if not storage:
            return None
        provider = storage.get("provider")
        if provider not in {"aliyun_oss", "sre_open_api_oss", "aliyun_oss_sts"}:
            return None
        return storage

    @classmethod
    def resolve_download_url(cls, storage_meta: Optional[Dict[str, Any]]) -> Optional[str]:
        if not storage_meta:
            return None
        object_key = storage_meta.get("object_key") or storage_meta.get("key")
        # 优先按文档动态获取下载链接
        if isinstance(object_key, str) and object_key.strip():
            sts_url = cls._get_sts_download_url(object_key.strip())
            if sts_url:
                return sts_url
            # 动态获取失败再回退
            fallback = cls.sign_download_url(object_key=object_key.strip())
            if fallback:
                return fallback

        direct = storage_meta.get("download_url") or storage_meta.get("url")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        return None


oss_service = OSSService()
