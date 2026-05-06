"""UTP MCP Server — Authentication module.

Handles Keycloak SSO ROPC auth + automatic token refresh.
"""

import time
import httpx
import os


TOKEN_URL = "https://sso.utp.edu.pe/auth/realms/Xpedition/protocol/openid-connect/token"

# Config per platform
CLIENTS = {
    "portal": {
        "client_id": "utpmas-web",
        "scope": "openid profile email roles-client-utpmas-web",
    },
    "class": {
        "client_id": "pao-web",
        "scope": "openid profile email roles-client-pao-web",
    },
}


class AuthManager:
    """Manages SSO tokens for both Portal and Class platforms."""

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._tokens: dict[str, dict] = {}
        self._http = httpx.Client(timeout=15)

    def _fetch_token(self, platform: str) -> dict:
        cfg = CLIENTS[platform]
        resp = self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": cfg["client_id"],
                "username": self._username,
                "password": self._password,
                "scope": cfg["scope"],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        data["_fetched_at"] = time.time()
        return data

    def get_token(self, platform: str) -> str:
        """Get a valid access token, refreshing if needed."""
        cached = self._tokens.get(platform)
        if cached:
            elapsed = time.time() - cached["_fetched_at"]
            expires_in = cached.get("expires_in", 300)
            if elapsed < (expires_in - 60):
                return cached["access_token"]

            # Try refresh
            if cached.get("refresh_token"):
                try:
                    return self._refresh(platform, cached["refresh_token"])
                except Exception:
                    pass

        token_data = self._fetch_token(platform)
        self._tokens[platform] = token_data
        return token_data["access_token"]

    def _refresh(self, platform: str, refresh_token: str) -> str:
        cfg = CLIENTS[platform]
        resp = self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": cfg["client_id"],
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        data["_fetched_at"] = time.time()
        self._tokens[platform] = data
        return data["access_token"]

    def close(self):
        self._http.close()
