# Addon Manager - Архитектура приложения

## Обзор

Addon Manager - десктопное приложение на Python/PySide6 для управления адаптерами, параметрами, профилями BIM-моделирования и синхронизацией данных. Приложение поддерживает светлую/тёмную тему и предоставляет модульную структуру для различных задач.

**Версия:** 1.0.0 (03.03.2026)

---

## Структура файлов

```
Addon manager/
├── main.py                       # Точка входа, главное меню с выбором режима
├── ARCHITECTURE.md               # Этот файл
├── .gitignore                    # Исключения Git
├── build_exe.bat                 # Скрипт сборки exe (PyInstaller)
├── Шаблон Excel.xlsx             # Шаблон Excel для экспорта
│
├── icon/                         # Иконки приложения (единая папка)
│   ├── Manager-scaled.png        # Логотип Larix (светлый)
│   ├── Manager-scaled_white.png  # Логотип Larix (тёмный)
│   ├── Larix Viewer_black.png    # Логотип Viewer (светлый)
│   ├── Larix Viewer_white.png    # Логотип Viewer (тёмный)
│   ├── logo.ico / logo.png       # Иконка приложения
│   ├── sun.png / moon.png        # Иконки переключателя темы
│   ├── white/                    # Иконки для тёмной темы (белые)
│   │   ├── arrow-*.png
│   │   ├── check.png
│   │   ├── select.png
│   │   └── poloska.png
│   └── ...                       # Прочие иконки UI (~100 файлов)
│
├── shared/                       # Общие компоненты
│   ├── __init__.py
│   ├── theme_toggle.py           # Переключатель темы, иконки, стили
│   ├── dialogs.py                # Диалоговые окна (ошибка, предупреждение)
│   ├── excel_parser.py           # Парсинг Excel-листов параметров
│   └── excel_template.py         # Экспорт шаблонов в Excel
│
├── Adapters/                     # Модуль адаптеров
│   ├── __init__.py
│   └── ui.py                     # Редактор адаптеров
│
├── Validator/                    # Модуль валидации параметров
│   ├── __init__.py
│   └── ui.py                     # Генерация профилей валидации
│
├── Matrix/                       # Модуль матриц
│   ├── __init__.py
│   └── ui.py                     # Генератор матриц коллизий
│
├── Sets/                         # Модуль наборов
│   ├── __init__.py
│   └── ui.py                     # Управление профилями Larix
│
├── Viewer/                       # Модуль статусов
│   └── ui.py                     # Создание статусов
│
└── Sync/                         # Модуль синхронизации
    ├── ui.py                     # GUI для синхронизации с БД
    ├── odbc.py                   # Управление ODBC-драйверами SQL Server
    ├── tls.py                    # Управление TLS/SSL сертификатами
    └── check.py                  # Утилита проверки parquet-файлов
```

---

## Модули

### 1. main.py — Точка входа

**Назначение:** Главное меню с выбором режима работы

**Классы:**
- `ModeCard` — Карточка режима с анимацией hover/selection
- `AnimatableShadowEffect` — Анимированная тень для карточек
- `PageSwitchSlider` — Переключатель страниц Manager/Viewer
- `MainMenuWidget` — Виджет главного меню
- `MainWindow` — Главное окно приложения

**Режимы:**

| Страница | ID | Название | Title Bar | Модуль |
|----------|----|---------|-----------|--------|
| Manager | `adapters` | Адаптеры | Larix — Адаптеры | `Adapters/ui.py` |
| Manager | `sets` | Наборы | Larix — Наборы | `Sets/ui.py` |
| Manager | `matrix` | Матрицы | Larix — Матрицы | `Matrix/ui.py` |
| Manager | `validator` | Параметры | Larix — Параметры | `Validator/ui.py` |
| Viewer | `viewer` | Статусы | Larix — Статусы | `Viewer/ui.py` |
| Viewer | `sync` | BIM Sync | Larix — Синхронизация | `Sync/ui.py` |

**Функции:**
- `_popup_error()` / `_popup_info()` — Диалоги ошибок и информации
- `_load_symbol_from_dir()` — Динамическая загрузка модулей
- `_check_api_connection()` — Проверка подключения к API
- `get_logo_path()` / `get_viewer_logo_path()` — Пути к логотипам

---

### 2. shared/theme_toggle.py — Тема и иконки

**Назначение:** Единая система темы и иконок для всех модулей

**Классы:**
- `Palette` — Цветовая палитра (dataclass)
- `ThemeToggle` — Анимированный переключатель светлая/тёмная тема
- `RowHoverDelegate` — Делегат подсветки строк в таблицах

**Функции:**
- `theme()` — Применение темы к приложению
- `is_dark_theme()` — Проверка текущей темы
- `load_saved_theme()` / `save_theme()` — Сохранение/загрузка темы
- `resolve_icon_path()` — Разрешение пути к иконке
- `nik_icon()` — Получение иконки с авто-тонированием
- `create_back_button()` — Кнопка возврата в главное меню
- `go_to_main_menu()` — Навигация обратно в main.py
- `apply_dark_titlebar()` — Тёмный заголовок окна (Windows)
- `_tint_pixmap()` — Тонирование QPixmap указанным цветом
- `_ensure_white_copy()` / `_ensure_black_copy()` — Создание тонированных копий

**Цветовая палитра (PALETTE):**
| Константа | Значение | Описание |
|-----------|----------|----------|
| ACCENT | `#F7921E` | Оранжевый акцент |
| ACCENT_HOVER | `#FFA74B` | Акцент при наведении |
| ACCENT_PRESSED | `#E07E12` | Акцент при нажатии |
| SELECTED | `#FFC37A` | Выбранный элемент |
| SOFT_HOVER | `#FFE3C2` | Мягкая подсветка |
| BG_LIGHT / BG_DARK | `#FFFFFF` / `#1E1E1E` | Фон |
| FG_LIGHT / FG_DARK | `#222222` / `#FFFFFF` | Текст |

**Поведение иконок:**
- Иконки автоматически тонируются под тему
- Исключения (не тонируются): logo, ok, none, warning, refresh, gear, folder

---

### 3. shared/dialogs.py — Диалоговые окна

**Назначение:** Переиспользуемые диалоговые компоненты

**Функции:**
- `show_dialog()` — Показ диалога с иконкой приложения
- `show_success()` / `show_error()` / `show_warning()` — Диалоги сообщений
- `message_box()` / `information_box()` / `warning_box()` / `critical_box()` — MessageBox
- `question_box()` — Диалог вопроса
- `wire_dialog_button_box()` — Подключение кнопок диалога
- `wire_message_box_buttons()` — Подключение кнопок QMessageBox
- `install_dialog_icon_patch()` — Патч для автоматической установки иконки

---

### 4. shared/excel_parser.py — Парсинг Excel

**Назначение:** Чтение и анализ листов параметров из Excel

**Классы:**
- `ParameterSheetLayout` — Структура листа параметров (dataclass)
  - `header_row` — Номер строки заголовка
  - `subheader_row` — Номер строки подзаголовка (LOI)
  - `data_start_row` — Номер первой строки данных
  - `columns` — Список имён колонок
  - `filter_columns` — Колонки для фильтрации
  - `param_columns` — Колонки параметров
  - `role_columns` — Ролевые колонки (section, category, ifc, classif_code, classif_desc)
  - `dataframe` — DataFrame с данными

**Функции:**
- `read_parameter_sheet()` — Чтение листа параметров
- `normalize_excel_label()` — Нормализация меток Excel

---

### 5. shared/excel_template.py — Экспорт в Excel

**Назначение:** Генерация форматированных Excel-файлов

**Функции:**
- `export_common_excel(json_path, output_path)` — Экспорт данных в Excel

**Встроенные шаблоны (COMMON_JSON):**
- Наборы для матриц (АР, КР, ВИС, ГП, НИС)
- Матрица коллизий
- Параметры LOI с классификатором
- Адаптер (маппинг параметров)

**Форматирование:**
- Шрифт Tahoma 11pt
- Цветовые заливки для заголовков
- Границы ячеек
- Автоперенос текста

---

### 6. Adapters/ui.py — Редактор адаптеров

**Назначение:** Создание и редактирование адаптеров для связи атрибутов с параметрами моделей

**Title Bar:** `Larix — Адаптеры`

**Классы:**
- `MainWin` — Главное окно редактора
- `AdapterDoc` — Документ адаптера (XML-сериализация)
- `Binding` — Привязка параметра к атрибуту
- `BindingQueue` — Очередь привязок для атрибута
- `TransformSettings` — Настройки преобразования данных
- `TransformDialog` — Диалог настройки преобразований
- `ModelFilterDialog` — Фильтр по моделям
- `RowDragTable` — Таблица с drag&drop строк
- `ErrorDialog` — Диалог ошибки

**API функции:**
- `api_get_projects()` — Получение списка проектов
- `api_get_containers()` — Получение контейнеров проекта
- `api_get_params_for_container()` — Параметры контейнера
- `api_get_global_component()` — Глобальный компонент

**Формат данных:** XML (`Adapter.xml`)

---

### 7. Validator/ui.py — Валидация параметров

**Назначение:** Генерация профилей валидации параметров из Excel

**Title Bar:** `Larix — Параметры`

**Классы:**
- `MainWindow` — Главное окно
- `_MappingRow` — Строка сопоставления параметров

**Функции:**
- `excel_to_pv_profile()` — Генерация PV-профиля из Excel
- `fetch_api_param_types()` — Получение типов параметров из API
- `fetch_global_component()` — Загрузка глобального компонента
- `save_session_mapping_json()` / `load_session_mapping_json()` — Сохранение/загрузка маппинга

**Режимы:**
- `MODE_CATEGORY` — По категориям
- `MODE_CLASSIFIER` — По классификатору
- `MODE_BOTH` — Комбинированный

---

### 8. Matrix/ui.py — Генератор матриц коллизий

**Назначение:** Создание профилей коллизий из Excel-матриц

**Title Bar:** `Larix — Матрицы`

**Классы:**
- `MainWindow` — Главное окно
- `Section` — Композитная секция UI
- `GeneratorWorker` — Worker для генерации в отдельном потоке (QThread)

**XML-шаблоны:**
- `XML_TEMPLATE` — Корневой шаблон профиля
- `FOLDER_TEMPLATE` — Шаблон папки
- `ITEM_TEMPLATE` — Шаблон элемента коллизии

**Параметры:**
- Допуски A/B/C (в метрах)
- Параметр фильтрации (по умолчанию `Категория:\`)

---

### 9. Sets/ui.py — Настройка профилей

**Назначение:** Управление профилями и наборами Larix

**Title Bar:** `Larix — Наборы`

**Классы:**
- `MainWindow` — Главное окно
- `Palette` — Цветовая палитра (встроенная)
- `SyncBadgeTreeDelegate` — Делегат с badge синхронизации
- `TreeBranchProxyStyle` — Стиль веток дерева
- `StatusIndicator` — Индикатор статуса

**Функции:**
- `api_get_projects()` / `api_get_containers()` / `api_get_parameters()` — API запросы
- `compose_badged_icon()` — Создание иконки с badge
- `SheetPickerDialog` — Диалог выбора листа Excel
- `ApiSelectDialog` — Диалог выбора из API

---

### 10. Viewer/ui.py — Создание статусов

**Назначение:** Создание и управление статусами элементов модели

**Title Bar:** `Larix — Статусы`

**Функции:**
- `api_get()` — Универсальный GET-запрос с обработкой ошибок
- `normalize_name()` — Нормализация имени для сопоставления
- `apply_themed_icon()` — Применение тонированной иконки к виджету
- `set_header_logo()` — Установка логотипа в заголовок
- `show_error_dialog()` — Диалог ошибки

---

### 11. Sync/ui.py — BIM Sync

**Назначение:** Синхронизация данных между BIM-моделями и базой данных

**Title Bar:** `Larix — Синхронизация`

**Классы:**
- `ModeSelectDialog` / `ModeSelectWidget` — Выбор режима синхронизации
- `BimSyncWindow` — Окно синхронизации с SQL Server
- `PowerBiExportWindow` — Экспорт в CSV/Parquet/SQLite

**Режимы:**
- SQL Server — синхронизация с базой данных
- Power BI (CSV) — экспорт в CSV
- Parquet — экспорт в Apache Parquet
- SQLite — экспорт в SQLite базу

**Функции:**
- Подключение к SQL Server через ODBC
- Экспорт элементов и свойств модели
- Диагностика подключений

---

### 12. Sync/odbc.py — Управление ODBC

**Назначение:** Управление ODBC-драйверами для SQL Server

**Классы:**
- `ODBCDriver` — Enum драйверов (ODBC 18, ODBC 17, SQL Server Legacy)
- `ODBCConfig` — Конфигурация подключения (dataclass)
- `ODBCDiagnostics` — Диагностика подключения (dataclass)
- `ODBCConnectionManager` — Менеджер подключений
- `ODBCErrors` — Исключения ODBC

**Функции:**
- `classify_odbc_error()` — Классификация ошибок ODBC
- `check_odbc_environment()` — Проверка окружения ODBC
- `get_process_bitness()` — Определение разрядности процесса
- `run_diagnostics()` — Запуск диагностики

---

### 13. Sync/tls.py — Управление TLS

**Назначение:** Управление TLS/SSL сертификатами для HTTPS-запросов

**Классы:**
- `TLSErrorType` — Enum типов TLS-ошибок
- `TLSConfig` — Конфигурация TLS (dataclass)
- `TLSDiagnostics` — Диагностика TLS (dataclass)
- `TLSManager` — Менеджер TLS
- `TLSErrors` — Исключения TLS

**Функции:**
- `classify_ssl_error()` — Классификация SSL-ошибок
- `get_tls_manager()` — Получение менеджера TLS
- `is_production_environment()` — Проверка production-окружения

---

### 14. Sync/check.py — Утилита проверки

**Назначение:** Проверка целостности parquet-файлов

**Проверяет:**
- elements.parquet
- properties_wide.parquet
- projects.parquet
- models.parquet
- properties_eav.parquet

**Выводит:**
- Количество строк и колонок в каждом файле
- Сравнение количества элементов и свойств

---

## Навигация между модулями

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│                  (MainWindow)                       │
│   [Manager] ←── PageSwitchSlider ──→ [Viewer]      │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
   Manager                         Viewer
        │                               │
   ┌────┼────┬────┬────┐          ┌────┴────┐
   ▼    ▼    ▼    ▼    ▼          ▼         ▼
┌─────┐┌─────┐┌─────┐┌────────┐┌──────┐┌──────┐
│Adapt││Matrix││Valid││  Sets  ││Viewer││ Sync │
│ ers ││     ││ator ││        ││      ││      │
│[←]  ││[←]  ││[←]  ││[←]     ││[←]   ││[←]   │
└──┬──┘└──┬──┘└──┬──┘└───┬────┘└──┬───┘└──┬───┘
   │      │      │        │        │       │
   └──────┴──────┴────────┴────────┴───────┘
                     │
                     ▼
            go_to_main_menu()
                  → main.py
```

---

## Зависимости

### Обязательные:
- Python 3.10+
- PySide6 (или PyQt5 как fallback)

### Опциональные:
- `pandas` — Работа с Excel и данными
- `openpyxl` — Экспорт в Excel
- `requests` — HTTP-запросы к API
- `pyodbc` — Подключение к SQL Server (BIM Sync)

---

## API endpoints

### Локальный сервер (Base URL: http://localhost:5000)

```
GET /api/project/projects                    — Список проектов
GET /api/imcContainer/getProjectImcContainers/{id} — Контейнеры проекта
GET /api/imcParameterDefinition/imcParameterDefinitions?containerIds=... — Параметры
GET /api/globalComponent/globalComponent/{id} — Глобальный компонент
GET /api/imcElement/imcElements/{containerId} — Элементы контейнера
PUT /api/imcElement/imcElements              — Batch-обновление элементов
```

### Внешний Viewer API (Base URL: https://bwv.testing.bim-info.ru)

```
GET /api/projects/all                        — Список всех проектов
GET /api/jimc/projectid?projectId={id}      — Модели проекта (jimc)
GET /api/attribute-schema/projectid-jimcid   — Схемы атрибутов
GET /api/attribute/attributeschemaid-jimcid  — Атрибуты схемы
GET /api/attribute-value/jimcid-attributeid  — Значения атрибута (с nativeId)
```

---

## Форматы файлов

| Расширение | Описание |
|------------|----------|
| `.xml` | Адаптеры, профили валидации |
| `.cv` | Профили коллизий (XML-формат) |
| `.set` | Профили Larix |
| `.pv` | Профили экспорта |
| `.xlsx/.xls` | Исходные данные Excel |
| `.json` | Маппинги параметров |
| `.parquet` | Экспорт данных (Apache Parquet) |
| `.sqlite` | Экспорт данных (SQLite) |

---

## Ключевые паттерны

1. **Тема:** Все модули используют `shared/theme_toggle.py` для единообразного UI
2. **Навигация:** Кнопка "Назад" через `create_back_button()` + `go_to_main_menu()`
3. **Сериализация:** XML для адаптеров и профилей
4. **Асинхронность:** `QThread` + Worker для длительных операций
5. **Стилизация:** QSS с PNG-иконками, адаптивными под тему
6. **Сопоставление имён:** `normalize_name()` для нечёткого сравнения
7. **Диалоги:** Единый стиль через `shared/dialogs.py`
8. **Иконки:** Единая папка `icon/` с автотонированием под тему
9. **Title Bar:** Единый формат `Larix — %s` для всех модулей

---

## Сборка

```batch
build_exe.bat
```

Создаёт `dist/Larix_Plugin_Manager.exe` с помощью PyInstaller.
