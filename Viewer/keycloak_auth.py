# -*- coding: utf-8 -*-
import time
import requests
import hashlib
import base64
import secrets
import re

KEYCLOAK_BASE = "https://keycloak.bim-info.ru"
REALM = "bwv-production"
TOKEN_URL = f"{KEYCLOAK_BASE}/realms/{REALM}/protocol/openid-connect/token"
AUTH_URL = f"{KEYCLOAK_BASE}/realms/{REALM}/protocol/openid-connect/auth"
CLIENT_ID = "bwv-front"
REDIRECT_URI = "https://viewer.larix.ru/app"


def _generate_pkce():
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _extract_form_action(html: str) -> str | None:
    match = re.search(r'<form[^>]+action="([^"]+)"', html)
    if match:
        return match.group(1).replace("&amp;", "&")
    return None


class KeycloakAuth:
    def __init__(self):
        self.access_token: str | None = None
        self.refresh_token_value: str | None = None
        self.token_expires_at: float = 0
        self.refresh_expires_at: float = 0
        self._username: str | None = None
        self._password: str | None = None

    def _store_tokens(self, data: dict):
        now = time.time()
        self.access_token = data["access_token"]
        self.refresh_token_value = data.get("refresh_token")
        self.token_expires_at = now + data.get("expires_in", 36000) - 120
        self.refresh_expires_at = now + data.get("refresh_expires_in", 1800) - 60

    def login_password(self, username: str, password: str) -> tuple[bool, str]:
        self._username = username
        self._password = password

        ok, msg = self._try_ropc(username, password)
        if ok:
            return True, msg
        ok, msg = self._try_browser_login(username, password)
        return ok, msg

    def _try_ropc(self, username: str, password: str) -> tuple[bool, str]:
        data = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        try:
            r = requests.post(TOKEN_URL, data=data, timeout=15)
            if r.status_code == 200:
                self._store_tokens(r.json())
                return True, "Авторизация прошла успешно (ROPC)"
            return False, f"ROPC: {r.status_code} — {r.text[:200]}"
        except Exception as e:
            return False, f"ROPC: {e}"

    def _try_browser_login(self, username: str, password: str) -> tuple[bool, str]:
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        code_verifier, code_challenge = _generate_pkce()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "response_mode": "fragment",
            "response_type": "code",
            "scope": "openid",
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        try:
            r1 = sess.get(AUTH_URL, params=params, timeout=15, allow_redirects=True)
            if r1.status_code not in (200, 302):
                return False, f"Browser auth step 1: {r1.status_code}"

            form_url = r1.url
            form_action = _extract_form_action(r1.text)
            if not form_action:
                form_action = form_url

            r2 = sess.post(
                form_action,
                data={"username": username, "password": password, "credentialId": ""},
                timeout=15,
                allow_redirects=False,
            )

            code = None
            for _ in range(10):
                if r2.status_code not in (301, 302, 303, 307):
                    break
                location = r2.headers.get("Location", "")

                if "code=" in location:
                    if "#code=" in location:
                        fragment = location.split("#", 1)[1]
                    elif "?code=" in location:
                        fragment = location.split("?", 1)[1]
                    else:
                        fragment = location
                    for part in fragment.split("&"):
                        if part.startswith("code="):
                            code = part[5:]
                            break
                    break

                sess.headers.pop("Referer", None)
                r2 = sess.get(location, timeout=15, allow_redirects=False)

            if not code:
                return False, "Не удалось получить authorization code"

            token_data = {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "code": code,
                "code_verifier": code_verifier,
            }
            r3 = sess.post(TOKEN_URL, data=token_data, timeout=15)
            if r3.status_code == 200:
                self._store_tokens(r3.json())
                return True, "Авторизация прошла успешно"
            return False, f"Token exchange: {r3.status_code} — {r3.text[:200]}"
        except Exception as e:
            return False, f"Browser login: {e}"

    def refresh(self) -> tuple[bool, str]:
        if not self.refresh_token_value:
            return False, "Нет refresh_token"
        data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": self.refresh_token_value,
        }
        try:
            r = requests.post(TOKEN_URL, data=data, timeout=15)
            if r.status_code == 200:
                self._store_tokens(r.json())
                return True, "Токен обновлён"
            self.refresh_token_value = None
            return False, f"Refresh: {r.status_code}"
        except Exception as e:
            return False, f"Refresh: {e}"

    def get_valid_token(self) -> str | None:
        now = time.time()
        if self.access_token and now < self.token_expires_at:
            return self.access_token
        if self.refresh_token_value and now < self.refresh_expires_at:
            ok, _ = self.refresh()
            if ok:
                return self.access_token
        if self._username and self._password:
            ok, _ = self._try_ropc(self._username, self._password)
            if ok:
                return self.access_token
            ok, _ = self._try_browser_login(self._username, self._password)
            if ok:
                return self.access_token
        return None

    @property
    def is_authenticated(self) -> bool:
        return self.access_token is not None and time.time() < self.token_expires_at

    @property
    def seconds_until_expire(self) -> float:
        if not self.access_token:
            return 0
        return max(0, self.token_expires_at - time.time())

    def logout(self):
        self.access_token = None
        self.refresh_token_value = None
        self.token_expires_at = 0
        self.refresh_expires_at = 0
        self._username = None
        self._password = None
