from __future__ import annotations

"""HTTP helpers used by Viewer components.

The deployed API currently cannot be validated reliably on every customer
workstation because its certificate chain may be incomplete or signed by a
corporate CA unknown to the bundled Python trust store.  Requests therefore
use compatibility mode (certificate verification disabled) consistently.
"""

from typing import Any

import requests
import urllib3

VERIFY_TLS = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get(url: str, **kwargs: Any) -> requests.Response:
    kwargs.setdefault("verify", VERIFY_TLS)
    return requests.get(url, **kwargs)


def post(url: str, **kwargs: Any) -> requests.Response:
    kwargs.setdefault("verify", VERIFY_TLS)
    return requests.post(url, **kwargs)


class CompatibilitySession(requests.Session):
    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("verify", VERIFY_TLS)
        return super().request(method, url, **kwargs)


def create_session() -> requests.Session:
    session = CompatibilitySession()
    session.verify = VERIFY_TLS
    return session
