# PROJECT_CONTEXT

## Назначение проекта

Larix Viewer - отдельное десктопное Windows-приложение на Python/PySide6 для Viewer-сценариев: управление статусами Viewer и синхронизация/экспорт BIM-данных.

Контекст подтвержден файлами `ARCHITECTURE.md`, `viewer_main.py`, `status_viewer_main.py`, `export_viewer_main.py`, модулями `Viewer`, `Sync` и `shared`. В текущей рабочей копии нет `main.py`, `manager_main.py`, `Adapters`, `Sets`, `Matrix`, `Validator`, `api_tools.py` и `importxml`.

## Стек технологий

- Python 3.10+ согласно `ARCHITECTURE.md`.
- GUI: PySide6; в `ARCHITECTURE.md` указан возможный PyQt5 fallback, но в текущих точках входа используются импорты PySide6.
- Работа с данными: pandas, openpyxl, pyarrow.
- HTTP/API: requests, urllib.request.
- База данных: SQL Server через pyodbc; SQLite для локального экспорта.
- Надежность HTTP/операций: tenacity.
- Сборка Windows exe: PyInstaller через `.bat`-скрипты.
- Форматы данных: `.json`, `.parquet`, `.sqlite/.db`, CSV, данные Viewer/локального API.

Зависимости перечислены в `requirements.txt`:

```text
PySide6
pandas
requests
openpyxl
pyodbc
tenacity
pyarrow
certifi
pyinstaller
```

## Архитектура проекта

Проект организован как отдельное Viewer desktop-приложение с тремя точками входа. Общий UI-каркас находится в `shared/app_common.py`, а общие темы, иконки, диалоги и Excel-утилиты вынесены в `shared/`.

Основная навигация строится вокруг общего каркаса `shared/app_common.py`. `viewer_main.py` показывает общий стартовый экран Larix Viewer с карточками "Статусы" и "Элементы". В специализированных entrypoint-ах включен `skip_menu=True`: `status_viewer_main.py` сразу открывает `Viewer/ui.py`, а `export_viewer_main.py` сразу открывает BIM Sync/экспорт.

Архитектурный паттерн:

- точка входа создает `QApplication`;
- применяется синхронизация темы и общая палитра;
- создается главное окно или меню режимов;
- выбранный режим загружает UI-класс из конкретного модуля;
- модули работают с локальным API, внешним Viewer API, табличными файлами или SQL Server в зависимости от сценария.

## Структура директорий и файлов

- `viewer_main.py` - общая точка входа для `Larix Viewer`; стартовый экран с карточками "Статусы" и "Элементы".
- `status_viewer_main.py` - точка входа для `Larix Status Viewer`; загружает `Viewer/ui.py`.
- `export_viewer_main.py` - точка входа для `Larix Export Viewer`; запускает BIM Sync/экспорт через общий каркас.
- `ARCHITECTURE.md` - существующее описание архитектуры, модулей, endpoint-ов и форматов.
- `requirements.txt` - зависимости Python.
- `config_example.txt` - пример конфигурации SQL Server.
- `build_viewer.bat` - сборка общего Larix Viewer через PyInstaller.
- `build_status_viewer.bat` - сборка Status Viewer через PyInstaller.
- `build_export_viewer.bat` - сборка Export Viewer через PyInstaller.
- `icon/` - основной набор иконок и логотипов приложения.
- `shared/` - общие компоненты: тема, диалоги, общий каркас меню, Excel parser/template.
- `Viewer/` - сценарии статусов Viewer и Keycloak-аутентификация.
- `Sync/` - BIM Sync, SQL Server, ODBC/TLS диагностика, экспорт CSV/Parquet/SQLite.
- `build/`, `dist/`, `__pycache__/` - артефакты сборки/кэши; не являются исходным кодом.

## Ключевые модули

- `shared/app_common.py` - общий каркас главного меню, карточки режимов, проверка подключения к API, загрузка модулей, работа с логотипами, версиями и темой.
- `shared/theme_toggle.py` - единая тема, переключатель светлая/темная тема, разрешение иконок, автотонирование и кнопка возврата.
- `shared/dialogs.py` - общие диалоги и QMessageBox-обертки.
- `shared/excel_parser.py` - чтение листов параметров из Excel и определение layout листов.
- `shared/excel_template.py` - экспорт встроенных шаблонов в Excel.
- `Viewer/ui.py` - создание/управление статусами, работа с локальными проектами/контейнерами и внешним Viewer API, токен/Bearer-аутентификация.
- `Viewer/keycloak_auth.py` - Keycloak login/refresh/logout, ROPC и browser-like flow; endpoint `https://keycloak.bim-info.ru`.
- `Sync/ui.py` - крупный модуль BIM Sync: выбор режима, SQL Server синхронизация, экспорт Power BI/CSV/Parquet/SQLite, загрузка проектов/моделей/элементов/свойств через Viewer API.
- `Sync/odbc.py` - диагностика и построение подключения ODBC к SQL Server.
- `Sync/tls.py` - TLS/SSL диагностика, настройка requests session и безопасные запросы.
- `Sync/check.py` - проверка parquet-файлов.

## Основные сущности и доменные понятия

- Project/проект - BIM/Viewer проект, загружается из локального или внешнего API.
- Container/контейнер/модель - модель внутри проекта локального API.
- JIMC/model - модель внешнего Viewer API.
- Element/элемент - элемент BIM-модели.
- Parameter/параметр - определение или значение параметра модели.
- Global component/attribute schema/attribute - структура атрибутов для сопоставления.
- Status - статус элементов Viewer.
- BIM Sync export - выгрузка элементов и свойств в SQL Server, CSV, Parquet или SQLite.

## Точки входа

- `python status_viewer_main.py` - Larix Status Viewer: статусы.
- `python export_viewer_main.py` - Larix Export Viewer: экспорт/синхронизация.
- Некоторые UI-модули имеют самостоятельный `if __name__ == "__main__"`, но их запуск нужно проверять отдельно, так как основной сценарий идет через точки входа выше.

## Команды запуска, сборки и проверок

Установка зависимостей:

```bat
py -3 -m pip install -r requirements.txt
```

Запуск основных приложений:

```bat
py -3 viewer_main.py
py -3 status_viewer_main.py
py -3 export_viewer_main.py
```

Сборка:

```bat
build_viewer.bat
build_status_viewer.bat
build_export_viewer.bat
```

Проверка синтаксиса без запуска GUI:

```bat
py -3 -m compileall .
```

Тесты/линтеры:

- Явных тестов, `pytest`-конфигурации, линтеров (`ruff`, `flake8`, `black`, `mypy`) или CI/CD файлов в проекте не найдено.
- Если после изменений нет возможности запускать GUI, минимальная проверка - `py -3 -m compileall .` и точечный запуск измененного entrypoint/module в подходящем окружении.

## Интеграции, API, БД и внешние сервисы

- Локальный API по умолчанию: `http://localhost:5000`.
- Управление локальным API через `LARIX_API_BASE_URL`/`DEFAULT_API_BASE_URL` в `shared/app_common.py` и модульные helper-ы.
- Внешний Viewer API по умолчанию встречается в разных местах: `https://viewer.larix.ru` в `Viewer/ui.py`, `Sync/ui.py`; `https://bwv.testing.bim-info.ru` в `Viewer/ui.py` как `EXTERNAL_BASE_URL`.
- Keycloak: `https://keycloak.bim-info.ru`, realm `BIMInfo`, redirect `https://viewer.larix.ru/app` в `Viewer/keycloak_auth.py`.
- SQL Server через ODBC/pyodbc; пример подключения в `config_example.txt`.
- SQLite export в `Sync/ui.py`.
- Parquet export через pandas/pyarrow.
- Табличный экспорт/импорт через pandas/openpyxl, если используется конкретным модулем.

Подтвержденные локальные API endpoints из `ARCHITECTURE.md` и текущих модулей:

- `GET /api/project/projects`
- `GET /api/imcContainer/getProjectImcContainers/{id}`
- `GET /api/imcParameterDefinition/imcParameterDefinitions?containerIds=...`
- `GET /api/globalComponent/globalComponent/{id}`
- `GET /api/imcElement/imcElements/{containerId}`
- `PUT /api/imcElement/imcElements`
- `POST /api/imcParameterDefinition/imcParameterDefinition`
- `POST /api/imcParameterValue/setAlternateValueByElements`

Подтвержденные внешние Viewer API endpoints:

- `GET /api/projects/all`
- `GET /api/jimc/projectid?projectId={id}`
- `GET /api/attribute-schema/projectid-jimcid`
- `GET /api/attribute/attributeschemaid-jimcid`
- `GET /api/attribute-value/jimcid-attributeid`
- `POST /api/element/jimcid`
- `POST /api/tree-table/elements`
- `POST /api/element/jimcid-eidarr`
- `GET /api/tree-table/distinct-c...` используется в `Sync/ui.py`, полное назначение требует проверки рядом с кодом вызова.

## Важные конфиги и артефакты

- `requirements.txt` - единственный найденный dependency-файл.
- `.gitignore` - настроен по принципу ignore-all с allowlist исходных директорий и файлов; новые `docs/ai-context/*` могут быть проигнорированы Git, если `.gitignore` не расширить отдельно.
- `config_example.txt` - пример SQL Server credentials; не использовать как реальные секреты.
- `build_export_viewer.bat` - актуально ссылается на `export_viewer_main.py`.
- `dist/`, `build/`, `__pycache__`, логи - артефакты, не опираться на них как на источник истины.

## Соглашения по стилю и структуре

- UI строится на PySide6 widgets, QSS и ресурсах из `icon/`.
- Для темизации использовать `shared/theme_toggle.py`, `enable_theme_sync`, `theme`, `resolve_icon_path`, `ThemeToggle`.
- Для новых общих диалогов использовать `shared/dialogs.py`, если модуль уже не содержит собственные локальные диалоги.
- Для возврата в меню используется паттерн `create_back_button()`/`go_to_main_menu()` из `shared/theme_toggle.py` или общий каркас `shared/app_common.py`.
- Для длительных операций используется `QThread` + worker, чтобы не блокировать GUI.
- API base URL должен идти через `LARIX_API_BASE_URL` или поле UI, а не жестко прописываться в новых местах.
- Стиль кодовой базы смешанный: часть модулей крупные монолитные `ui.py`, часть логики дублируется между модулями. Не рефакторить без отдельной задачи.
- Чекбоксы стилизуются через `icon/check.png` и `icon/select.png`; перед исправлением логики выбора проверять соответствие визуального состояния и `QCheckBox.isChecked()`.

## Известные ограничения

- Не найдено автоматических тестов и CI/CD.
- Нет `README.md` в корне; основная документация - `ARCHITECTURE.md`.
- `.gitignore` по умолчанию игнорирует почти все, кроме allowlist; `docs/ai-context/**` добавлен в allowlist для AI-контекста.
- В проекте есть сгенерированные артефакты `build/`, `dist/`, `__pycache__`, `bim_sync.log`; они не должны использоваться для анализа бизнес-логики.
- `Sync/ui.py` и `Viewer/ui.py` большие; изменения в них требуют точечного анализа связанных функций.
- Несколько мест задают разные external Viewer base URL (`viewer.larix.ru`, `bwv.testing.bim-info.ru`); фактическое production/testing окружение нужно уточнять.

## Текущие пользовательские уточнения

- Пользователь уже разделил проект: текущая рабочая копия содержит Viewer-приложение со статусами и экспортом.
- Ошибка в Larix Status Viewer: при нажатии `Загрузить схемы` появляется предупреждение `Выберите хотя бы одну модель`, хотя пользователь видит отмеченные модели. Первичная точка анализа - `Viewer/ui.py::load_schemas_attrs()` и хранение чекбоксов в `self.checked_models`. Вероятная причина - визуальная инверсия QSS-иконок: `QCheckBox::indicator:unchecked` использует иконку `check`, а `checked` использует `select`.
- Пользователь пока не уточнил различие Viewer API окружений.

## Потенциально опасные места

- `Viewer/keycloak_auth.py` и auth-логика в `Viewer/ui.py` работают с токенами и паролями. Не логировать секреты, не менять flow без проверки с реальным окружением.
- `Sync/ui.py` выполняет операции с SQL Server, CSV/Parquet/SQLite и внешним API; есть риск порчи данных или долгих операций.
- `Sync/odbc.py` и `Sync/tls.py` влияют на подключение к БД/API и пользовательскую диагностику ошибок.
- `shared/theme_toggle.py` и `shared/app_common.py` используются многими entrypoint-ами; изменения могут повлиять на все приложения.
- `.bat`-скрипты сборки удаляют старые exe/build-директории; запускать их осознанно.

## Что нужно уточнить у пользователя

- Какие окружения являются production/test для Viewer API: `https://viewer.larix.ru` или `https://bwv.testing.bim-info.ru`?
- Какие проверки считать обязательными перед сдачей: только `compileall`, ручной запуск GUI, сборка PyInstaller, smoke-тест с API/БД?
- Нужно ли добавить тестовый фреймворк/линтеры в будущем, или проект сознательно работает без них?
