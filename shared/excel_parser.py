from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ParameterSheetLayout:
    header_row: int
    subheader_row: int | None
    data_start_row: int
    columns: list[str]
    column_labels: dict[str, str]
    filter_columns: list[str]
    param_columns: list[str]
    role_columns: dict[str, str]
    dataframe: Any


_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "section": ("элементы модели", "раздел"),
    "category": ("категория revit", "категория"),
    "ifc": ("пример класса ifc", "ifc"),
    "classif_code": ("код по классификатору", "код классификатора"),
    "classif_desc": ("описание по классификатору", "описание классификатора"),
}


def normalize_excel_label(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower().startswith("unnamed:"):
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    return text.lower().replace("ё", "е")


def _clean_excel_label(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower().startswith("unnamed:"):
        return ""
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def _score_header_row(values: list[str]) -> int:
    score = 0
    for value in values:
        for aliases in _ROLE_ALIASES.values():
            if value in aliases:
                score += 2
                break
        if "loi" in value:
            score += 2
        elif value in {"код", "ifc", "revit"}:
            score += 1
    return score


def _detect_header_rows(raw_df: Any) -> tuple[int, int | None]:
    preview_rows = min(len(raw_df.index), 10)
    best_row = 0
    best_score = -1
    for row_idx in range(preview_rows):
        row_values = [
            normalize_excel_label(raw_df.iat[row_idx, col_idx])
            for col_idx in range(raw_df.shape[1])
            if normalize_excel_label(raw_df.iat[row_idx, col_idx])
        ]
        if not row_values:
            continue
        score = _score_header_row(row_values)
        if score > best_score:
            best_score = score
            best_row = row_idx

    subheader_row = None
    if best_row + 1 < len(raw_df.index):
        loi_cols = [
            idx
            for idx in range(raw_df.shape[1])
            if "loi" in normalize_excel_label(raw_df.iat[best_row, idx])
        ]
        if loi_cols:
            loi_start = loi_cols[0]
            sub_values = [
                _clean_excel_label(raw_df.iat[best_row + 1, idx])
                for idx in range(loi_start, raw_df.shape[1])
            ]
            if any(sub_values):
                subheader_row = best_row + 1
    return best_row, subheader_row


def _make_unique_keys(
    names: list[str],
    priority_flags: list[bool] | None = None,
) -> tuple[list[str], dict[str, str]]:
    if priority_flags is None or len(priority_flags) != len(names):
        priority_flags = [False] * len(names)

    groups: dict[str, list[int]] = {}
    for idx, name in enumerate(names):
        base = name or ""
        if not base:
            continue
        groups.setdefault(base, []).append(idx)

    result = [""] * len(names)
    labels: dict[str, str] = {}
    for idx, name in enumerate(names):
        if not name:
            result[idx] = ""

    for base, indices in groups.items():
        ordered = sorted(indices, key=lambda idx: (0 if priority_flags[idx] else 1, idx))
        assigned: dict[int, str] = {}
        for seq, idx in enumerate(ordered, start=1):
            assigned[idx] = base if seq == 1 else f"__dup_{idx}_{seq}__{base}"
        for idx in indices:
            result[idx] = assigned[idx]
            labels[assigned[idx]] = base

    return result, labels


def _detect_role_positions(
    raw_columns: list[str],
    source_indices: list[int],
    loi_start_col: int | None,
) -> dict[str, int]:
    normalized = [normalize_excel_label(column) for column in raw_columns]
    role_positions: dict[str, int] = {}
    for role, aliases in _ROLE_ALIASES.items():
        fallback_idx = None
        preferred_idx = None
        for pos, (src_idx, column_name) in enumerate(zip(source_indices, normalized)):
            if column_name not in aliases:
                continue
            if fallback_idx is None:
                fallback_idx = pos
            if loi_start_col is not None and src_idx < loi_start_col:
                preferred_idx = pos
                break
        chosen_idx = preferred_idx if preferred_idx is not None else fallback_idx
        if chosen_idx is not None:
            role_positions[role] = chosen_idx
    return role_positions


def _detect_role_columns(columns: list[str]) -> dict[str, str]:
    norm_map = {column: normalize_excel_label(column) for column in columns}
    role_columns: dict[str, str] = {}
    for role, aliases in _ROLE_ALIASES.items():
        for column, normalized in norm_map.items():
            if normalized in aliases:
                role_columns[role] = column
                break
    return role_columns


def read_parameter_sheet(path: str, sheet_name: str, pd_module: Any) -> ParameterSheetLayout:
    raw_df = pd_module.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)
    header_row, subheader_row = _detect_header_rows(raw_df)
    loi_start_col = None
    for col_idx in range(raw_df.shape[1]):
        if "loi" in normalize_excel_label(raw_df.iat[header_row, col_idx]):
            loi_start_col = col_idx
            break

    raw_column_names: list[str] = []
    keep_indices: list[int] = []
    for col_idx in range(raw_df.shape[1]):
        top_name = _clean_excel_label(raw_df.iat[header_row, col_idx])
        sub_name = _clean_excel_label(raw_df.iat[subheader_row, col_idx]) if subheader_row is not None else ""
        if loi_start_col is not None and col_idx >= loi_start_col and sub_name:
            column_name = sub_name
        elif top_name and normalize_excel_label(top_name) != "loi":
            column_name = top_name
        elif sub_name:
            column_name = sub_name
        else:
            column_name = ""
        if column_name:
            keep_indices.append(col_idx)
            raw_column_names.append(column_name)

    role_positions = _detect_role_positions(raw_column_names, keep_indices, loi_start_col)
    priority_flags = [
        bool(loi_start_col is not None and src_idx >= loi_start_col)
        for src_idx in keep_indices
    ]
    column_names, column_labels = _make_unique_keys(raw_column_names, priority_flags=priority_flags)
    data_start_row = (subheader_row + 1) if subheader_row is not None else (header_row + 1)
    dataframe = raw_df.iloc[data_start_row:, keep_indices].copy()
    dataframe.columns = column_names
    dataframe = dataframe.dropna(how="all").reset_index(drop=True)

    role_columns = {
        role: column_names[pos]
        for role, pos in role_positions.items()
        if 0 <= pos < len(column_names)
    }
    if not role_columns:
        role_columns = _detect_role_columns(column_names)
    role_names = set(role_columns.values())
    if loi_start_col is not None:
        filter_columns = [
            name
            for src_idx, name in zip(keep_indices, column_names)
            if src_idx < loi_start_col and name
        ]
        param_columns = [
            name
            for src_idx, name in zip(keep_indices, column_names)
            if src_idx >= loi_start_col and name not in role_names
        ]
    else:
        filter_columns = [name for name in column_names if name]
        param_columns = [name for name in column_names if name and name not in role_names]

    return ParameterSheetLayout(
        header_row=header_row,
        subheader_row=subheader_row,
        data_start_row=data_start_row,
        columns=column_names,
        column_labels=column_labels,
        filter_columns=filter_columns,
        param_columns=param_columns,
        role_columns=role_columns,
        dataframe=dataframe,
    )
