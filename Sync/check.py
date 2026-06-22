import pandas as pd
import os
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else "."

files = {
    "elements": None,
    "properties_wide": None,
    "projects": None,
    "models": None,
    "properties_eav": None
}

ext = "parquet"
for name in files:
    path = os.path.join(folder, f"{name}.{ext}")
    if os.path.exists(path):
        files[name] = path

print(f"Папка: {os.path.abspath(folder)}\n")
print(f"{'Файл':<25} {'Строк':>10} {'Колонок':>10}")
print("-" * 50)

for name, path in files.items():
    if path and os.path.exists(path):
        df = pd.read_parquet(path)
        print(f"{name}.{ext:<15} {len(df):>10} {len(df.columns):>10}")
    else:
        print(f"{name}.{ext:<15} {'нет файла':>10}")

print()
if files["elements"] and files["properties_wide"]:
    df_el = pd.read_parquet(files["elements"])
    df_wide = pd.read_parquet(files["properties_wide"])
    
    if len(df_el) == len(df_wide):
        print(f"OK: Количество строк совпадает ({len(df_el)})")
    else:
        print(f"РАЗЛИЧИЕ: elements={len(df_el)}, properties_wide={len(df_wide)}")
        diff = len(df_el) - len(df_wide)
        print(f"  Элементов без свойств: {diff}")
