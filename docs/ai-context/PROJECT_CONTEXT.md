# PROJECT_CONTEXT

## Назначение проекта

Addon Manager - десктопное Windows-приложение на Python/PySide6 для работы с Larix/BIM-сценариями: управление адаптерами, наборами, матрицами коллизий, профилями параметров/валидации, статусами Viewer и синхронизацией/экспортом BIM-данных.

Контекст подтвержден файлами `ARCHITECTURE.md`, `main.py`, `manager_main.py`, `status_viewer_main.py`, `export_viewer_main.py`, модулями `Adapters`, `Sets`, `Matrix`, `Validator`, `Viewer`, `Sync`, `shared` и `importxml`.

## Стек технологий

- Python 3.10+ согласно `ARCHITECTURE.md`.
- GUI: PySide6; в `ARCHITECTURE.md` указан возможный PyQt5 fallback, но в текущих точках входа используются импорты PySide6.
- Работа с данными: pandas, openpyxl, pyarrow.
- HTTP/API: requests, urllib.request.
- База данных: SQL Server через pyodbc; SQLite для локального экспорта.
- Надежность HTTP/операций: tenacity.
- Сборка Windows exe: PyInstaller через `.bat`-скрипты и `.spec`.
- Форматы данных: XML, `.cv`, `.set`, `.pv`, `.xlsx/.xls`, `.json`, `.parquet`, `.sqlite/.db`, CSV.

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

Проект организован как модульное desktop-приложение с несколькими точками входа. Общий UI-каркас находится в `shared/app_common.py`, а общие темы, иконки, диалоги и Excel-утилиты вынесены в `shared/`.

Основная навигация строится вокруг карточек режимов. Карточка выбирает модуль, модуль динамически загружается из директории через `importlib.util.spec_from_file_location`. В старом объединенном входе `main.py` и новом общем каркасе `shared/app_common.py` есть схожая логика загрузки модулей и проверки API.

Архитектурный паттерн:

- точка входа создает `QApplication`;
- применяется синхронизация темы и общая палитра;
- создается главное окно или меню режимов;
- выбранный режим загружает UI-класс из конкретного модуля;
- модули работают с локальным API, внешним Viewer API, Excel/XML-файлами или SQL Server в зависимости от сценария.

## Структура директорий и файлов

- `main.py` - объединенная точка входа с режимами Manager/Viewer, описана в `ARCHITECTURE.md`; содержит дублирующуюся с `shared/app_common.py` логику меню и загрузки модулей.
- `manager_main.py` - точка входа для `Larix Plugin Manager`; загружает `Adapters`, `Sets`, `Matrix`, `Validator`.
- `status_viewer_main.py` - точка входа для `Larix Status Viewer`; загружает `Viewer/ui.py`.
- `export_viewer_main.py` - точка входа для `Larix Export Viewer`; запускает BIM Sync/экспорт через общий каркас.
- `api_tools.py` - каталог API-оберток и JSON-схем tools для AI-агента; содержит локальные и внешние Viewer API endpoints.
- `ARCHITECTURE.md` - существующее описание архитектуры, модулей, endpoint-ов и форматов.
- `requirements.txt` - зависимости Python.
- `config_example.txt` - пример конфигурации SQL Server.
- `build_exe.bat` - сборка Manager и Viewer через PyInstaller.
- `build_export_viewer.bat` - сборка Export Viewer через PyInstaller.
- `Larix_Export_Viewer.spec` - сгенерированный/ручной spec PyInstaller для Export Viewer; содержит абсолютные пути текущей машины.
- `Шаблон Excel.xlsx` - Excel-шаблон для пользовательских сценариев импорта/экспорта.
- `icon/` - основной набор иконок и логотипов приложения.
- `shared/` - общие компоненты: тема, диалоги, общий каркас меню, Excel parser/template.
- `Adapters/` - редактор адаптеров и XML-сериализация привязок параметров.
- `Sets/` - управление профилями/наборами Larix.
- `Matrix/` - генератор матриц коллизий.
- `Validator/` - генерация профилей параметров/валидации из Excel.
- `Viewer/` - сценарии статусов Viewer и Keycloak-аутентификация.
- `Sync/` - BIM Sync, SQL Server, ODBC/TLS диагностика, экспорт CSV/Parquet/SQLite.
- `importxml/` - отдельные утилиты для загрузки XML change list и импорта/экспорта параметров; `README.md` почти пустой.
- `viewer subd/` - дополнительный/старый подмодуль viewer sync GUI; назначение требует уточнения, так как имя директории нетипичное и не описано в `ARCHITECTURE.md`.
- `build/`, `dist/`, `__pycache__/` - артефакты сборки/кэши; не являются исходным кодом.

## Ключевые модули

- `shared/app_common.py` - общий каркас главного меню, карточки режимов, проверка подключения к API, загрузка модулей, работа с логотипами, версиями и темой.
- `shared/theme_toggle.py` - единая тема, переключатель светлая/темная тема, разрешение иконок, автотонирование и кнопка возврата.
- `shared/dialogs.py` - общие диалоги и QMessageBox-обертки.
- `shared/excel_parser.py` - чтение листов параметров из Excel и определение layout листов.
- `shared/excel_template.py` - экспорт встроенных шаблонов в Excel.
- `Adapters/ui.py` - редактор адаптеров, `AdapterDoc`, `Binding`, `BindingQueue`, `TransformSettings`, API-загрузка проектов/контейнеров/параметров, XML `Adapter.xml`.
- `Sets/ui.py` - UI профилей/наборов Larix, API-загрузка проектов/контейнеров/параметров, Excel sheet picker, API select dialog.
- `Matrix/ui.py` - генератор `.cv`/XML профилей коллизий из Excel-матриц; использует шаблоны XML и worker в `QThread`.
- `Validator/ui.py` и `Validator/Parameters.py` - генерация `.pv`/XML профилей параметров из Excel, маппинг Excel/API параметров, сохранение маппингов JSON.
- `Viewer/ui.py` - создание/управление статусами, работа с локальными проектами/контейнерами и внешним Viewer API, токен/Bearer-аутентификация.
- `Viewer/keycloak_auth.py` - Keycloak login/refresh/logout, ROPC и browser-like flow; endpoint `https://keycloak.bim-info.ru`.
- `Sync/ui.py` - крупный модуль BIM Sync: выбор режима, SQL Server синхронизация, экспорт Power BI/CSV/Parquet/SQLite, загрузка проектов/моделей/элементов/свойств через Viewer API.
- `Sync/odbc.py` - диагностика и построение подключения ODBC к SQL Server.
- `Sync/tls.py` - TLS/SSL диагностика, настройка requests session и безопасные запросы.
- `Sync/check.py` - проверка parquet-файлов.
- `api_tools.py` - отдельный каталог API endpoints для AI/автоматизации; может выполнять mutating-запросы, например создание параметров и batch update элементов.

## Основные сущности и доменные понятия

- Project/проект - BIM/Viewer проект, загружается из локального или внешнего API.
- Container/контейнер/модель - модель внутри проекта локального API.
- JIMC/model - модель внешнего Viewer API.
- Element/элемент - элемент BIM-модели.
- Parameter/параметр - определение или значение параметра модели.
- Global component/attribute schema/attribute - структура атрибутов для сопоставления.
- Adapter - XML-документ привязки атрибутов к параметрам и преобразований.
- Binding - привязка параметра к атрибуту адаптера.
- Set/profile - профиль Larix/наборы.
- Matrix/collision profile - матрица коллизий и генерируемый XML `.cv`.
- PV profile - профиль параметров/валидации `.pv`.
- Status - статус элементов Viewer.
- BIM Sync export - выгрузка элементов и свойств в SQL Server, CSV, Parquet или SQLite.

## Точки входа

- `python main.py` - объединенное приложение Manager/Viewer, исторически описанное в `ARCHITECTURE.md`.
- `python manager_main.py` - Larix Plugin Manager: адаптеры, наборы, матрицы, параметры.
- `python status_viewer_main.py` - Larix Status Viewer: статусы.
- `python export_viewer_main.py` - Larix Export Viewer: экспорт/синхронизация.
- `python -m importxml.XML` или `python importxml/XML.py` - отдельная утилита XML change list uploader; подтверждено наличием `main()` и `if __name__ == "__main__"`.
- Некоторые UI-модули имеют самостоятельный `if __name__ == "__main__"`, но их запуск нужно проверять отдельно, так как основной сценарий идет через точки входа выше.

## Команды запуска, сборки и проверок

Установка зависимостей:

```bat
py -3 -m pip install -r requirements.txt
```

Запуск основных приложений:

```bat
py -3 manager_main.py
py -3 status_viewer_main.py
py -3 export_viewer_main.py
py -3 main.py
```

Сборка:

```bat
build_exe.bat
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
- Управление локальным API через `LARIX_API_BASE_URL` в `main.py`, `shared/app_common.py`, `Validator`, `Matrix`, `Sets`, `api_tools.py`.
- Внешний Viewer API по умолчанию в разных местах:
  - `https://viewer.larix.ru` в `api_tools.py`, `Viewer/ui.py`, `Sync/ui.py`;
  - `https://bwv.testing.bim-info.ru` в `Viewer/ui.py` как `EXTERNAL_BASE_URL`.
- Keycloak: `https://keycloak.bim-info.ru`, realm `BIMInfo`, redirect `https://viewer.larix.ru/app` в `Viewer/keycloak_auth.py`.
- SQL Server через ODBC/pyodbc; пример подключения в `config_example.txt`.
- SQLite export в `Sync/ui.py`.
- Parquet export через pandas/pyarrow.
- Excel import/export через pandas/openpyxl и `Шаблон Excel.xlsx`.

Подтвержденные локальные API endpoints из `ARCHITECTURE.md` и `api_tools.py`:

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
- `build_exe.bat` - ожидает `viewer_main.py`, но такой файл не найден при обзоре. Возможно, это устаревшая ссылка или файл отсутствует в рабочей копии.
- `build_export_viewer.bat` - актуально ссылается на `export_viewer_main.py`.
- `Larix_Export_Viewer.spec` - содержит абсолютные пути `X:\Projects\IBIM\Addon-manager`; при переносе проекта может потребовать регенерации.
- `dist/`, `build/`, `.spec`, `__pycache__`, логи - артефакты, не опираться на них как на источник истины.

## Соглашения по стилю и структуре

- UI строится на PySide6 widgets, QSS и ресурсах из `icon/`.
- Для темизации использовать `shared/theme_toggle.py`, `enable_theme_sync`, `theme`, `resolve_icon_path`, `ThemeToggle`.
- Для новых общих диалогов использовать `shared/dialogs.py`, если модуль уже не содержит собственные локальные диалоги.
- Для возврата в меню используется паттерн `create_back_button()`/`go_to_main_menu()` из `shared/theme_toggle.py` или общий каркас `shared/app_common.py`.
- Для длительных операций используется `QThread` + worker, чтобы не блокировать GUI.
- API base URL должен идти через `LARIX_API_BASE_URL` или поле UI, а не жестко прописываться в новых местах.
- Стиль кодовой базы смешанный: часть модулей крупные монолитные `ui.py`, часть логики дублируется между модулями. Не рефакторить без отдельной задачи.

## Известные ограничения

- Не найдено автоматических тестов и CI/CD.
- Нет `README.md` в корне; основная документация - `ARCHITECTURE.md`.
- `importxml/README.md` содержит только заголовок.
- `build_exe.bat` ссылается на `viewer_main.py`, которого не найдено; сборка обоих exe через этот скрипт может падать.
- `.gitignore` по умолчанию игнорирует почти все, кроме allowlist; `docs/ai-context/**` добавлен в allowlist для AI-контекста.
- В проекте есть сгенерированные артефакты `build/`, `dist/`, `__pycache__`, `bim_sync.log`; они не должны использоваться для анализа бизнес-логики.
- `Sync/ui.py`, `Validator/Parameters.py`, `Adapters/ui.py` и другие UI-файлы очень большие; изменения в них требуют точечного анализа связанных функций.
- Несколько мест задают разные external Viewer base URL (`viewer.larix.ru`, `bwv.testing.bim-info.ru`); фактическое production/testing окружение нужно уточнять.

## Текущие пользовательские уточнения

- Пользователь хочет разделить проект на два отдельных приложения: одно для всего, что связано с Viewer, второе - для всего остального.
- `viewer_main.py`, вероятно, должен существовать как отдельная программа Viewer, но его нельзя создавать или восстанавливать без отдельного явного промта на реализацию.
- Пользователь пока не определил обязательный набор проверок и не уточнил различие Viewer API окружений.

## Потенциально опасные места

- `api_tools.py` содержит mutating API wrappers: создание параметров, установка значений и batch update элементов. Не вызывать без явного разрешения пользователя и тестового окружения.
- `Viewer/keycloak_auth.py` и auth-логика в `Viewer/ui.py` работают с токенами и паролями. Не логировать секреты, не менять flow без проверки с реальным окружением.
- `Sync/ui.py` выполняет операции с SQL Server, CSV/Parquet/SQLite и внешним API; есть риск порчи данных или долгих операций.
- `Sync/odbc.py` и `Sync/tls.py` влияют на подключение к БД/API и пользовательскую диагностику ошибок.
- XML/PV/CV/SET генераторы в `Adapters`, `Validator`, `Matrix`, `Sets` формируют файлы для внешних Larix/BIM-инструментов; формат менять только после проверки совместимости.
- `shared/theme_toggle.py` и `shared/app_common.py` используются многими entrypoint-ами; изменения могут повлиять на все приложения.
- `.bat`-скрипты сборки удаляют старые exe/build-директории; запускать их осознанно.
- `Larix_Export_Viewer.spec` содержит абсолютные пути; ручные изменения могут ломать сборку на других машинах.

## Что нужно уточнить у пользователя

- Как именно разделить Viewer-приложение и Manager-приложение: какие режимы должны войти в Viewer, а какие остаться в Manager?
- Должен ли `viewer_main.py` объединять `status_viewer_main.py` и `export_viewer_main.py`, или это должен быть отдельный вход только для одного Viewer-сценария?
- Какие окружения являются production/test для Viewer API: `https://viewer.larix.ru` или `https://bwv.testing.bim-info.ru`?
- Какие проверки считать обязательными перед сдачей: только `compileall`, ручной запуск GUI, сборка PyInstaller, smoke-тест с API/БД?
- Нужно ли добавить тестовый фреймворк/линтеры в будущем, или проект сознательно работает без них?
- Какой статус у `viewer subd/`: актуальный модуль, эксперимент или устаревший код?
