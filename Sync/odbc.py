# -*- coding: utf-8 -*-
"""
ODBC Manager - модуль управления ODBC-драйверами для SQL Server.

Автоматически определяет доступные драйверы, поддерживает fallback-логику,
формирует DSN-less строки подключения с корректными параметрами шифрования.
"""
import struct
import sys
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum
import pyodbc


class ODBCDriver(Enum):
    ODBC_18 = "ODBC Driver 18 for SQL Server"
    ODBC_17 = "ODBC Driver 17 for SQL Server"
    SQL_SERVER_LEGACY = "SQL Server"


DRIVER_PRIORITY = [
    ODBCDriver.ODBC_18,
    ODBCDriver.ODBC_17,
    ODBCDriver.SQL_SERVER_LEGACY,
]

DRIVER_FRIENDLY_NAMES = {
    ODBCDriver.ODBC_18: "ODBC Driver 18",
    ODBCDriver.ODBC_17: "ODBC Driver 17",
    ODBCDriver.SQL_SERVER_LEGACY: "SQL Server (legacy)",
}

ERROR_MESSAGES = {
    "IM002": {
        "title": "ODBC-драйвер не найден",
        "message": (
            "Не найден ODBC-драйвер для SQL Server.\n\n"
            "Требуется установка:\n"
            "• ODBC Driver 18 для SQL Server (рекомендуется)\n"
            "• или ODBC Driver 17 для SQL Server\n\n"
            "Скачайте драйвер:\n"
            "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server\n\n"
            "Важно: разрядность драйвера должна совпадать с разрядностью приложения ({bitness})."
        ),
    },
    "ENCRYPT": {
        "title": "Ошибка шифрования соединения",
        "message": (
            "Ошибка TLS/шифрования при подключении к SQL Server.\n\n"
            "Возможные решения:\n"
            "1. Установите последний ODBC Driver 18\n"
            "2. Для тестового окружения добавьте в конфиг:\n"
            "   TrustServerCertificate=yes\n"
            "3. Убедитесь, что SQL Server поддерживает TLS 1.2+\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    "AUTH": {
        "title": "Ошибка аутентификации",
        "message": (
            "Ошибка входа в SQL Server.\n\n"
            "Проверьте:\n"
            "• Имя пользователя и пароль\n"
            "• Для Windows Auth оставьте username/password пустыми\n"
            "• Режим аутентификации на сервере (Mixed/Windows)\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    "CONNECT": {
        "title": "Ошибка подключения",
        "message": (
            "Не удалось подключиться к SQL Server.\n\n"
            "Проверьте:\n"
            "• Адрес сервера: {server}\n"
            "• Имя базы данных: {database}\n"
            "• Сетевую доступность сервера (firewall, порт 1433)\n"
            "• SQL Server Configuration Manager: протокол TCP/IP включен\n\n"
            "Техническая ошибка: {detail}"
        ),
    },
    "TIMEOUT": {
        "title": "Превышено время ожидания",
        "message": (
            "Превышено время ожидания подключения к серверу.\n\n"
            "Проверьте:\n"
            "• Доступность сервера {server}\n"
            "• Сетевое соединение\n"
            "• Увеличьте timeout в конфигурации"
        ),
    },
    "GENERIC": {
        "title": "Ошибка базы данных",
        "message": "Ошибка при работе с базой данных:\n{detail}",
    },
}


@dataclass
class ODBCDiagnostics:
    process_bitness: str
    available_drivers: List[str]
    selected_driver: Optional[str]
    dsn_list: List[str]
    system_dsn_list: List[str]
    user_dsn_list: List[str]


def get_process_bitness() -> str:
    if struct.calcsize("P") * 8 == 64:
        return "x64 (64-bit)"
    return "x86 (32-bit)"


def is_64bit_process() -> bool:
    return struct.calcsize("P") * 8 == 64


def get_installed_drivers() -> List[str]:
    try:
        return pyodbc.drivers()
    except Exception:
        return []


def find_best_driver(preferred_order: Optional[List[ODBCDriver]] = None) -> Optional[ODBCDriver]:
    installed = get_installed_drivers()
    order = preferred_order or DRIVER_PRIORITY
    for driver in order:
        if driver.value in installed:
            return driver
    return None


def get_all_drivers_info() -> Dict[str, bool]:
    installed = get_installed_drivers()
    return {driver.value: driver.value in installed for driver in ODBCDriver}


def get_dsn_list() -> Tuple[List[str], List[str], List[str]]:
    all_dsns = []
    system_dsns = []
    user_dsns = []
    try:
        all_dsns = [dsn[0] for dsn in pyodbc.dataSources().items()]
    except Exception:
        pass
    return all_dsns, system_dsns, user_dsns


def run_diagnostics() -> ODBCDiagnostics:
    all_dsns, system_dsns, user_dsns = get_dsn_list()
    installed = get_installed_drivers()
    best = find_best_driver()
    return ODBCDiagnostics(
        process_bitness=get_process_bitness(),
        available_drivers=installed,
        selected_driver=best.value if best else None,
        dsn_list=all_dsns,
        system_dsn_list=system_dsns,
        user_dsn_list=user_dsns,
    )


@dataclass
class ODBCConfig:
    encrypt: bool = True
    trust_server_certificate: bool = True
    connection_timeout: int = 30
    driver_priority: Optional[List[str]] = None
    force_driver: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "ODBCConfig":
        return cls(
            encrypt=data.get("encrypt", True),
            trust_server_certificate=data.get("trust_server_certificate", True),
            connection_timeout=int(data.get("connection_timeout", 30)),
            driver_priority=data.get("driver_priority"),
            force_driver=data.get("force_driver"),
        )


class ODBCError(Exception):
    def __init__(self, error_type: str, detail: str, server: str = "", database: str = ""):
        self.error_type = error_type
        self.detail = detail
        self.server = server
        self.database = database
        super().__init__(self.get_user_message())
    
    def get_user_message(self) -> str:
        template = ERROR_MESSAGES.get(self.error_type, ERROR_MESSAGES["GENERIC"])
        bitness = get_process_bitness()
        return template["message"].format(
            detail=self.detail,
            server=self.server,
            database=self.database,
            bitness=bitness,
        )
    
    def get_title(self) -> str:
        template = ERROR_MESSAGES.get(self.error_type, ERROR_MESSAGES["GENERIC"])
        return template["title"]


def classify_odbc_error(error: pyodbc.Error, server: str = "", database: str = "") -> ODBCError:
    error_str = str(error)
    error_lower = error_str.lower()
    
    if "IM002" in error_str or "источник данных не найден" in error_lower or "data source name not found" in error_lower:
        return ODBCError("IM002", error_str, server, database)
    
    if any(code in error_str for code in ["08001", "S1T00"]) or "timeout" in error_lower or "истекло время" in error_lower:
        if "ssl" in error_lower or "encrypt" in error_lower or "certificate" in error_lower or "tls" in error_lower:
            return ODBCError("ENCRYPT", error_str, server, database)
        return ODBCError("TIMEOUT", error_str, server, database)
    
    if "18456" in error_str or "login failed" in error_lower or "ошибка входа" in error_lower:
        return ODBCError("AUTH", error_str, server, database)
    
    if "08001" in error_str or "подключение" in error_lower or "connection" in error_lower:
        return ODBCError("CONNECT", error_str, server, database)
    
    if "encrypt" in error_lower or "ssl" in error_lower or "certificate" in error_lower:
        return ODBCError("ENCRYPT", error_str, server, database)
    
    return ODBCError("GENERIC", error_str, server, database)


def build_connection_string(
    server: str,
    database: str,
    driver: ODBCDriver,
    username: Optional[str] = None,
    password: Optional[str] = None,
    config: Optional[ODBCConfig] = None,
) -> str:
    if config is None:
        config = ODBCConfig()
    
    use_windows_auth = not username or not password
    
    parts = [f"DRIVER={{{driver.value}}};", f"SERVER={server};", f"DATABASE={database};"]
    
    if use_windows_auth:
        parts.append("Trusted_Connection=yes;")
    else:
        parts.append(f"UID={username};")
        parts.append(f"PWD={password};")
    
    if driver == ODBCDriver.ODBC_18:
        encrypt_val = "yes" if config.encrypt else "no"
        trust_val = "yes" if config.trust_server_certificate else "no"
        parts.append(f"Encrypt={encrypt_val};")
        parts.append(f"TrustServerCertificate={trust_val};")
    
    return "".join(parts)


class ODBCConnectionManager:
    def __init__(self, config: Optional[ODBCConfig] = None):
        self.config = config or ODBCConfig()
        self._selected_driver: Optional[ODBCDriver] = None
        self._driver_selection_log: List[str] = []
    
    def get_driver(self) -> ODBCDriver:
        if self._selected_driver:
            return self._selected_driver
        
        if self.config.force_driver:
            for d in ODBCDriver:
                if d.value == self.config.force_driver:
                    installed = get_installed_drivers()
                    if d.value in installed:
                        self._selected_driver = d
                        self._driver_selection_log.append(f"Force driver: {d.value}")
                        return d
                    raise ODBCError(
                        "IM002",
                        f"Принудительно указанный драйвер '{self.config.force_driver}' не установлен. "
                        f"Доступные драйверы: {', '.join(installed) or 'нет'}",
                    )
        
        priority = DRIVER_PRIORITY
        if self.config.driver_priority:
            custom_priority = []
            for name in self.config.driver_priority:
                for d in ODBCDriver:
                    if d.value == name or d.name == name:
                        custom_priority.append(d)
                        break
            if custom_priority:
                priority = custom_priority + [d for d in DRIVER_PRIORITY if d not in custom_priority]
        
        installed = get_installed_drivers()
        for driver in priority:
            if driver.value in installed:
                self._selected_driver = driver
                self._driver_selection_log.append(
                    f"Selected driver: {driver.value} (priority order)"
                )
                return driver
        
        raise ODBCError(
            "IM002",
            f"Не найден ни один поддерживаемый ODBC-драйвер. "
            f"Доступные драйверы: {', '.join(installed) or 'нет'}. "
            f"Разрядность процесса: {get_process_bitness()}",
        )
    
    def build_connection_string(
        self,
        server: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        driver = self.get_driver()
        return build_connection_string(
            server=server,
            database=database,
            driver=driver,
            username=username,
            password=password,
            config=self.config,
        )
    
    def test_connection(
        self,
        server: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[ODBCDriver]]:
        try:
            driver = self.get_driver()
            conn_str = self.build_connection_string(server, database, username, password)
            timeout = self.config.connection_timeout
            
            with pyodbc.connect(conn_str, timeout=timeout) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            
            return True, "Успешно", driver
        except ODBCError:
            raise
        except pyodbc.Error as e:
            odbc_error = classify_odbc_error(e, server, database)
            return False, odbc_error.get_user_message(), None
        except Exception as e:
            return False, str(e), None
    
    def connect(
        self,
        server: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        try:
            driver = self.get_driver()
            conn_str = self.build_connection_string(server, database, username, password)
            return pyodbc.connect(conn_str, timeout=self.config.connection_timeout)
        except ODBCError:
            raise
        except pyodbc.Error as e:
            raise classify_odbc_error(e, server, database)
    
    def get_diagnostics_info(self) -> str:
        diag = run_diagnostics()
        lines = [
            f"Разрядность процесса: {diag.process_bitness}",
            f"Доступные драйверы: {', '.join(diag.available_drivers) or 'нет'}",
            f"Выбранный драйвер: {diag.selected_driver or 'не определён'}",
        ]
        if self._driver_selection_log:
            lines.append("Лог выбора драйвера:")
            lines.extend(f"  - {entry}" for entry in self._driver_selection_log)
        return "\n".join(lines)
    
    @staticmethod
    def get_installation_instructions() -> str:
        bitness = "x64" if is_64bit_process() else "x86"
        return (
            f"Для работы приложения требуется ODBC-драйвер для SQL Server.\n\n"
            f"Текущая разрядность приложения: {bitness}\n\n"
            f"Рекомендуемый порядок установки:\n"
            f"1. ODBC Driver 18 для SQL Server ({bitness})\n"
            f"   https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server\n\n"
            f"2. Альтернатива: ODBC Driver 17 для SQL Server ({bitness})\n\n"
            f"Важно: разрядность драйвера должна совпадать с разрядностью приложения!"
        )


def get_connection_string_with_fallback(
    db_config: dict,
    odbc_config: Optional[ODBCConfig] = None,
    log_func=None,
) -> Tuple[str, ODBCDriver]:
    manager = ODBCConnectionManager(odbc_config)
    driver = manager.get_driver()
    conn_str = manager.build_connection_string(
        server=db_config.get("server", ""),
        database=db_config.get("database", ""),
        username=db_config.get("username"),
        password=db_config.get("password"),
    )
    if log_func:
        log_func(f"ODBC: driver={driver.value}, bitness={get_process_bitness()}")
    return conn_str, driver


def check_odbc_environment() -> Tuple[bool, str, Optional[ODBCDriver]]:
    driver = find_best_driver()
    if driver:
        return True, f"Доступен драйвер: {DRIVER_FRIENDLY_NAMES[driver]}", driver
    installed = get_installed_drivers()
    return False, f"ODBC-драйвер SQL Server не найден. Установленные драйверы: {', '.join(installed) or 'нет'}", None
