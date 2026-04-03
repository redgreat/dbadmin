import os
from typing import Optional

import requests


class WecomBotService:
    @staticmethod
    def _normalize_webhook(channel_target: str) -> str:
        target = (channel_target or "").strip()
        if target.startswith("http://") or target.startswith("https://"):
            return target
        return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={target}"

    @staticmethod
    def _get_key(channel_target: str) -> str:
        target = (channel_target or "").strip()
        if target.startswith("http://") or target.startswith("https://"):
            # webhook url like ...send?key=xxx
            marker = "key="
            idx = target.find(marker)
            if idx >= 0:
                return target[idx + len(marker):].split("&")[0]
        return target

    @classmethod
    def send_text(cls, channel_target: str, content: str) -> dict:
        webhook = cls._normalize_webhook(channel_target)
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
        }
        response = requests.post(webhook, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    @classmethod
    def upload_file(cls, channel_target: str, file_path: str) -> str:
        key = cls._get_key(channel_target)
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
        with open(file_path, "rb") as file_obj:
            files = {
                "media": (os.path.basename(file_path), file_obj, "application/octet-stream"),
            }
            response = requests.post(url, files=files, timeout=60)
        response.raise_for_status()
        data = response.json()
        if data.get("errcode") != 0:
            raise ValueError(f"企业微信群文件上传失败: {data}")
        media_id = data.get("media_id")
        if not media_id:
            raise ValueError(f"企业微信群文件上传返回缺少media_id: {data}")
        return media_id

    @classmethod
    def send_file(cls, channel_target: str, file_path: str) -> dict:
        webhook = cls._normalize_webhook(channel_target)
        media_id = cls.upload_file(channel_target=channel_target, file_path=file_path)
        payload = {
            "msgtype": "file",
            "file": {
                "media_id": media_id,
            },
        }
        response = requests.post(webhook, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
