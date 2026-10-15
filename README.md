# Larix Viewer

Windows-приложение на Python/PySide6 для просмотра статусов BIM-моделей и выгрузки данных в CSV, Parquet или Microsoft SQL Server.

## Возможности

- просмотр и работа со статусами BIM-моделей;
- выбор проектов, моделей, свойств и статусных атрибутов;
- выгрузка данных в CSV и Parquet для дальнейшей работы, в том числе в Power BI;
- загрузка и обновление данных в Microsoft SQL Server;
- отдельные режимы Status Viewer и Export Viewer;
- светлая и тёмная темы.

## Требования

- Windows;
- Python 3;
- Microsoft ODBC Driver 18 или 17 for SQL Server — для работы с SQL Server.

## Установка

```powershell
git clone https://github.com/Speshed/Viewer.git
cd Viewer
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Запуск

Общее меню с выбором режима:

```powershell
python viewer_main.py
```

Отдельные приложения:

```powershell
python status_viewer_main.py
python export_viewer_main.py
```

## Настройка SQL Server

В окне Export Viewer можно ввести параметры подключения или импортировать `config.txt`. За основу можно взять `config_example.txt`.

`config.txt` может содержать пароль и поэтому исключён из Git.

## Сборка EXE

Зависимости для PyInstaller входят в `requirements.txt`. В корне проекта есть три сценария сборки:

```powershell
.\build_viewer.bat
.\build_status_viewer.bat
.\build_export_viewer.bat
```

Готовые EXE появляются в `dist`. Каталоги `build`, `dist`, логи и рабочие выгрузки не добавляются в Git.

## Структура проекта

- `Viewer/` — интерфейс просмотра статусов;
- `Sync/` — выгрузка и синхронизация данных;
- `shared/` — общие компоненты и утилиты;
- `icon/` — ресурсы интерфейса.
