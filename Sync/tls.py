# -*- coding: utf-8 -*-
"""
TLS Manager - модуль управления TLS/SSL сертификатами для HTTPS-запросов.

Обеспечивает безопасное подключение к API с поддержкой:
- Стандартной валидации сертификатов (по умолчанию)
- Пользовательского CA bundle (корпоративные сертификаты)
- Диагностики TLS-ошибок с user-friendly сообщениями
- Защиты от случайного отключения проверки в production
"""
import os
import sys
import ssl
import socket
from typing import Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import urllib3

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class TLSErrorType(Enum):
    CERT_VERIFY_FAILED = "CERT_VERIFY_FAILED"
    SELF_SIGNED = "SELF_SIGNED"
    CERT_CHAIN_ERROR = "CERT_CHAIN_ERROR"
    CERT_EXPIRED = "CERT_EXPIRED"
    CERT_UNTRUSTED = "CERT_UNTRUSTED"
    HOSTNAME_MISMATCH = "HOSTNAME_MISMATCH"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT = "TIMEOUT"
    GENERIC = "GENERIC"


TLS_ERROR_MESSAGES = {
    TLSErrorType.CERT_VERIFY_FAILED: {
        "title": "Сертификат сервера не доверен",
        "message": (
            "Не удалось проверить SSL-сертификат сервера.\n\n"
            "Возможные причины:\n"
            "• Сервер использует самоподписанный сертификат\n"
            "• Цепочка сертификатов неполная\n"
            "• Корневой CA не добавлен в доверенные\n\n"
            "Решение:\n"
            "1. Получите корневой сертификат у администратора\n"
            "2. Добавьте путь к файлу в config.txt:\n"
            "   [TLS]\n"
            "   ca_bundle_path = C:\\path\\to\\corporate-ca.pem\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.SELF_SIGNED: {
        "title": "Самоподписанный сертификат",
        "message": (
            "Сервер использует самоподписанный сертификат.\n\n"
            "Для безопасного подключения:\n"
            "1. Получите файл сертификата (.pem/.crt) у администратора\n"
            "2. Добавьте в config.txt:\n"
            "   [TLS]\n"
            "   ca_bundle_path = C:\\path\\to\\certificate.pem\n\n"
            "Важно: Не отключайте проверку сертификата в production!\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.CERT_CHAIN_ERROR: {
        "title": "Ошибка цепочки сертификатов",
        "message": (
            "Цепочка SSL-сертификатов неполная или некорректная.\n\n"
            "Решение:\n"
            "1. Убедитесь, что сервер отправляет полную цепочку\n"
            "2. Добавьте промежуточные CA в ca_bundle_path\n"
            "3. Обратитесь к администратору сервера\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.CERT_EXPIRED: {
        "title": "Сертификат истёк",
        "message": (
            "SSL-сертификат сервера истёк.\n\n"
            "Обратитесь к администратору сервера для обновления сертификата.\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.CERT_UNTRUSTED: {
        "title": "Сертификат не доверен",
        "message": (
            "Сертификат сервера не подписан доверенным центром.\n\n"
            "Возможно, используется корпоративный CA.\n"
            "Добавьте корневой сертификат в config.txt:\n"
            "   [TLS]\n"
            "   ca_bundle_path = C:\\path\\to\\corporate-root-ca.pem\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.HOSTNAME_MISMATCH: {
        "title": "Несоответствие имени хоста",
        "message": (
            "Имя хоста в сертификате не совпадает с адресом сервера.\n\n"
            "Проверьте правильность URL в config.txt.\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.CONNECTION_ERROR: {
        "title": "Ошибка подключения",
        "message": (
            "Не удалось подключиться к серверу.\n\n"
            "Проверьте:\n"
            "• Правильность URL: {url}\n"
            "• Доступность сервера\n"
            "• Настройки сети и прокси\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    TLSErrorType.TIMEOUT: {
        "title": "Превышено время ожидания",
        "message": (
            "Сервер не ответил в течение {timeout} секунд.\n\n"
            "Проверьте:\n"
            "• Сетевое подключение\n"
            "• Доступность сервера\n"
            "• Увеличьте timeout в config.txt если сервер медленный"
        ),
    },
    TLSErrorType.GENERIC: {
        "title": "Ошибка TLS/SSL",
        "message": (
            "Произошла ошибка при защищённом подключении.\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
}


class TLSError(Exception):
    def __init__(
        self,
        error_type: TLSErrorType,
        detail: str,
        url: str = "",
        timeout: int = 30,
    ):
        self.error_type = error_type
        self.detail = detail
        self.url = url
        self.timeout = timeout
        super().__init__(self.get_user_message())

    def get_user_message(self) -> str:
        template = TLS_ERROR_MESSAGES.get(
            self.error_type, TLS_ERROR_MESSAGES[TLSErrorType.GENERIC]
        )
        safe_url = self._safe_url_for_log(self.url)
        return template["message"].format(
            detail=self.detail,
            url=safe_url,
            timeout=self.timeout,
        )

    def get_title(self) -> str:
        template = TLS_ERROR_MESSAGES.get(
            self.error_type, TLS_ERROR_MESSAGES[TLSErrorType.GENERIC]
        )
        return template["title"]

    @staticmethod
    def _safe_url_for_log(url: str) -> str:
        if not url:
            return ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception:
            return url[:100]


def classify_ssl_error(error: Exception, url: str = "") -> TLSError:
    error_str = str(error)
    error_lower = error_str.lower()

    if "self signed" in error_lower or "self-signed" in error_lower or "self_signed" in error_lower:
        return TLSError(TLSErrorType.SELF_SIGNED, error_str, url)

    if "certificate verify failed" in error_lower or "CERTIFICATE_VERIFY_FAILED" in error_str:
        if "self signed" in error_lower:
            return TLSError(TLSErrorType.SELF_SIGNED, error_str, url)
        if "unable to get local issuer" in error_lower:
            return TLSError(TLSErrorType.CERT_CHAIN_ERROR, error_str, url)
        if "certificate has expired" in error_lower:
            return TLSError(TLSErrorType.CERT_EXPIRED, error_str, url)
        return TLSError(TLSErrorType.CERT_VERIFY_FAILED, error_str, url)

    if "unable to get local issuer certificate" in error_lower:
        return TLSError(TLSErrorType.CERT_CHAIN_ERROR, error_str, url)

    if "certificate has expired" in error_lower or "not valid after" in error_lower:
        return TLSError(TLSErrorType.CERT_EXPIRED, error_str, url)

    if "hostname mismatch" in error_lower or "hostname" in error_lower and "doesn't match" in error_lower:
        return TLSError(TLSErrorType.HOSTNAME_MISMATCH, error_str, url)

    if "unable to get issuer certificate" in error_lower:
        return TLSError(TLSErrorType.CERT_UNTRUSTED, error_str, url)

    if "sslv3 alert" in error_lower or "tlsv1 alert" in error_lower:
        return TLSError(TLSErrorType.CERT_VERIFY_FAILED, error_str, url)

    return TLSError(TLSErrorType.GENERIC, error_str, url)


@dataclass
class TLSConfig:
    verify: bool = True
    ca_bundle_path: Optional[str] = None
    allow_insecure_dev: bool = False
    request_timeout: int = 30
    connect_timeout: int = 10
    max_retries: int = 3
    retry_on_ssl_error: bool = False

    _is_production: bool = field(default=True, repr=False)

    @classmethod
    def from_dict(cls, data: dict, is_production: bool = True) -> "TLSConfig":
        verify = data.get("verify", True)
        if isinstance(verify, str):
            verify = verify.lower() in ("true", "yes", "1")

        allow_insecure = data.get("allow_insecure_dev", False)
        if isinstance(allow_insecure, str):
            allow_insecure = allow_insecure.lower() in ("true", "yes", "1")

        ca_path = data.get("ca_bundle_path")
        if ca_path:
            ca_path = ca_path.strip()
            if not ca_path:
                ca_path = None

        return cls(
            verify=verify,
            ca_bundle_path=ca_path,
            allow_insecure_dev=allow_insecure,
            request_timeout=int(data.get("request_timeout", 30)),
            connect_timeout=int(data.get("connect_timeout", 10)),
            max_retries=int(data.get("max_retries", 3)),
            retry_on_ssl_error=data.get("retry_on_ssl_error", False),
            _is_production=is_production,
        )

    def get_verify_param(self) -> bool | str:
        if not self.verify and self.allow_insecure_dev and not self._is_production:
            return False
        if self.ca_bundle_path and os.path.isfile(self.ca_bundle_path):
            return self.ca_bundle_path
        return True

    def is_insecure_mode(self) -> bool:
        return not self.verify or (self.allow_insecure_dev and not self._is_production)

    def validate(self) -> List[str]:
        warnings = []

        if self.ca_bundle_path:
            if not os.path.exists(self.ca_bundle_path):
                warnings.append(
                    f"CA bundle файл не найден: {self.ca_bundle_path}"
                )
            elif not os.path.isfile(self.ca_bundle_path):
                warnings.append(
                    f"CA bundle путь не является файлом: {self.ca_bundle_path}"
                )

        if not self.verify:
            if self._is_production:
                warnings.append(
                    "КРИТИЧНО: verify=false в production! Это небезопасно."
                )
            else:
                warnings.append(
                    "ВНИМАНИЕ: verify=false — проверка сертификата отключена. "
                    "Используйте только для разработки!"
                )

        if self.allow_insecure_dev and self._is_production:
            warnings.append(
                "allow_insecure_dev=true в production будет проигнорировано."
            )

        return warnings


@dataclass
class TLSDiagnostics:
    url: str
    verify_enabled: bool
    ca_bundle_path: Optional[str]
    ca_bundle_exists: bool
    certificate_valid: bool
    certificate_subject: Optional[str]
    certificate_issuer: Optional[str]
    certificate_expires: Optional[str]
    tls_version: Optional[str]
    error_message: Optional[str]
    recommendations: List[str]

    def is_ok(self) -> bool:
        return self.certificate_valid and self.error_message is None


def is_production_environment() -> bool:
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env in ("production", "prod", "live"):
        return True
    if env in ("development", "dev", "test", "testing", "local"):
        return False
    if hasattr(sys, "frozen"):
        return True
    return True


class TLSManager:
    def __init__(self, config: Optional[TLSConfig] = None):
        self.config = config or TLSConfig()
        self._session: Optional[requests.Session] = None
        self._insecure_warning_shown = False

    def get_verify_param(self) -> bool | str:
        return self.config.get_verify_param()

    def check_insecure_and_warn(self, log_func=None) -> bool:
        if not self.config.is_insecure_mode():
            return False

        if self._insecure_warning_shown:
            return True

        self._insecure_warning_shown = True
        msg = (
            "ВНИМАНИЕ: Проверка SSL-сертификата отключена!\n"
            "Это небезопасно и должно использоваться только для разработки/тестирования.\n"
            "Никогда не используйте verify=false в production!"
        )
        if log_func:
            log_func(msg)
        else:
            print(f"[TLS WARNING] {msg}")

        return True

    def create_session(self) -> requests.Session:
        session = requests.Session()

        verify = self.get_verify_param()

        if verify is False:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        retry_strategy = requests.adapters.Retry(
            total=self.config.max_retries,
            connect=self.config.connect_timeout,
            read=self.config.request_timeout,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.verify = verify

        return session

    def test_connection(self, url: str, timeout: Optional[int] = None) -> Tuple[bool, str]:
        if timeout is None:
            timeout = self.config.request_timeout

        session = self.create_session()

        try:
            response = session.get(url, timeout=timeout)
            return True, f"Успешно (HTTP {response.status_code})"
        except requests.exceptions.SSLError as e:
            tls_error = classify_ssl_error(e, url)
            return False, tls_error.get_user_message()
        except requests.exceptions.Timeout:
            return False, f"Превышено время ожидания ({timeout} сек)"
        except requests.exceptions.ConnectionError as e:
            safe_url = TLSError._safe_url_for_log(url)
            return False, f"Не удалось подключиться к {safe_url}\n{str(e)[:200]}"
        except Exception as e:
            return False, f"Ошибка: {str(e)[:200]}"
        finally:
            session.close()

    def diagnose_tls(self, url: str) -> TLSDiagnostics:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or 443

        verify = self.get_verify_param()
        verify_enabled = verify is not False and verify is not True

        ca_exists = False
        if self.config.ca_bundle_path:
            ca_exists = os.path.isfile(self.config.ca_bundle_path)

        cert_valid = False
        cert_subject = None
        cert_issuer = None
        cert_expires = None
        tls_version = None
        error_msg = None
        recommendations = []

        try:
            context = ssl.create_default_context()

            if self.config.ca_bundle_path and ca_exists:
                context.load_verify_locations(self.config.ca_bundle_path)

            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cert_valid = True
                    cert_subject = str(dict(x[0] for x in cert.get("subject", ())))
                    cert_issuer = str(dict(x[0] for x in cert.get("issuer", ())))

                    not_after = cert.get("notAfter")
                    if not_after:
                        cert_expires = str(not_after)

                    tls_version = ssock.version()

        except ssl.SSLCertVerificationError as e:
            error_msg = str(e)
            if "self signed" in str(e).lower():
                recommendations.append(
                    "Добавьте самоподписанный сертификат в ca_bundle_path"
                )
            elif "unable to get local issuer" in str(e).lower():
                recommendations.append(
                    "Цепочка сертификатов неполная. Добавьте промежуточный CA."
                )
            recommendations.append("Обратитесь к администратору за файлом сертификата")
        except ssl.SSLError as e:
            error_msg = str(e)
            recommendations.append("Проверьте поддержку TLS на сервере")
        except socket.timeout:
            error_msg = "Превышено время ожидания подключения"
            recommendations.append("Проверьте доступность сервера")
        except socket.gaierror as e:
            error_msg = f"Не удалось разрешить имя хоста: {host}"
            recommendations.append("Проверьте правильность URL и DNS")
        except ConnectionRefusedError:
            error_msg = f"Соединение отклонено: {host}:{port}"
            recommendations.append("Проверьте, что сервер запущен и порт доступен")
        except Exception as e:
            error_msg = str(e)[:200]

        if not self.config.verify:
            recommendations.append(
                "ВНИМАНИЕ: verify=false — проверка сертификата отключена!"
            )

        if self.config.ca_bundle_path and not ca_exists:
            recommendations.append(
                f"CA bundle файл не найден: {self.config.ca_bundle_path}"
            )

        return TLSDiagnostics(
            url=url,
            verify_enabled=verify is not False,
            ca_bundle_path=self.config.ca_bundle_path,
            ca_bundle_exists=ca_exists,
            certificate_valid=cert_valid,
            certificate_subject=str(cert_subject) if cert_subject else None,
            certificate_issuer=str(cert_issuer) if cert_issuer else None,
            certificate_expires=cert_expires,
            tls_version=tls_version,
            error_message=error_msg,
            recommendations=recommendations,
        )

    def get_config_summary(self) -> str:
        lines = [
            f"Проверка сертификата: {'включена' if self.config.verify else 'ОТКЛЮЧЕНА'}",
        ]

        if self.config.ca_bundle_path:
            exists = "найден" if os.path.isfile(self.config.ca_bundle_path) else "НЕ НАЙДЕН"
            lines.append(f"CA bundle: {self.config.ca_bundle_path} ({exists})")
        else:
            lines.append("CA bundle: системный (не указан)")

        lines.append(f"Таймаут запроса: {self.config.request_timeout} сек")
        lines.append(f"Макс. повторов: {self.config.max_retries}")

        if self.config.is_insecure_mode():
            lines.append("⚠️ РЕЖИМ НЕБЕЗОПАСНОГО ПОДКЛЮЧЕНИЯ!")

        return "\n".join(lines)


_tls_manager: Optional[TLSManager] = None


def get_tls_manager(config_dict: Optional[dict] = None) -> TLSManager:
    global _tls_manager
    if config_dict is not None:
        is_prod = is_production_environment()
        config = TLSConfig.from_dict(config_dict, is_production=is_prod)
        _tls_manager = TLSManager(config)
    elif _tls_manager is None:
        _tls_manager = TLSManager()
    return _tls_manager


def create_tls_session(config_dict: Optional[dict] = None) -> requests.Session:
    manager = get_tls_manager(config_dict)
    manager.check_insecure_and_warn()
    return manager.create_session()


def safe_request(
    method: str,
    url: str,
    config_dict: Optional[dict] = None,
    **kwargs,
) -> requests.Response:
    manager = get_tls_manager(config_dict)
    manager.check_insecure_and_warn()

    session = manager.create_session()

    timeout = kwargs.pop("timeout", manager.config.request_timeout)

    try:
        response = session.request(method, url, timeout=timeout, **kwargs)
        return response
    except requests.exceptions.SSLError as e:
        tls_error = classify_ssl_error(e, url)
        raise tls_error from e
    finally:
        session.close()


def run_tls_diagnostics(url: str, config_dict: Optional[dict] = None) -> TLSDiagnostics:
    manager = get_tls_manager(config_dict)
    return manager.diagnose_tls(url)
