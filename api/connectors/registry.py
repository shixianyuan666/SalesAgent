from __future__ import annotations

from dataclasses import dataclass

from api.connectors.base import PlatformConnector
from api.connectors.feishu import FeishuConfig, FeishuConnector
from api.connectors.mock import MockConnector
from api.repos.settings_repo import SettingsRepo


@dataclass(frozen=True)
class ConnectorRegistry:
    def get(self, platform: str) -> PlatformConnector:
        raw = SettingsRepo().get_json("connectors", {})
        if not isinstance(raw, dict):
            raw = {}

        cfg = raw.get(platform)
        if not isinstance(cfg, dict):
            cfg = {}

        if platform == "feishu":
            enabled = bool(cfg.get("enabled", True))
            if not enabled:
                return MockConnector()
            base_url = str(cfg.get("base_url") or "https://open.feishu.cn")
            token = str(cfg.get("access_token") or "") if cfg.get("access_token") else None
            app_id = str(cfg.get("app_id") or "") if cfg.get("app_id") else None
            app_secret = str(cfg.get("app_secret") or "") if cfg.get("app_secret") else None
            if not token and not (app_id and app_secret):
                return MockConnector()
            return FeishuConnector(
                FeishuConfig(base_url=base_url, access_token=token, app_id=app_id, app_secret=app_secret)
            )

        return MockConnector()
