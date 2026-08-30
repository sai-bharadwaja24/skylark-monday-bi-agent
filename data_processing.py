"""
Cleans and normalizes raw monday.com item dicts into pandas DataFrames.

The source data is intentionally messy (per the assignment brief):
- stray rows where every cell literally repeats its own column header
  (an artifact of the export/import round-trip)
- inconsistent date formats / blank dates
- numeric fields arriving as text with stray whitespace or currency symbols
- inconsistent casing / spacing in categorical fields (status, sector, stage)

Every cleaning step that drops or reinterprets data is logged into a
`caveats` list that gets surfaced back to the user, per the "communicate
data quality issues" requirement - we never silently discard information.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CleanResult:
    df: pd.DataFrame
    caveats: list[str] = field(default_factory=list)


def _is_stray_header_row(row: pd.Series, columns: list[str]) -> bool:
    """A row is a stray duplicated header if a majority of its non-null
    cells equal their own column name verbatim."""
    non_null = [(c, row[c]) for c in columns if pd.notna(row.get(c))]
    if not non_null:
        return False
    matches = sum(1 for c, v in non_null if str(v).strip() == c.strip())
    return matches >= max(2, len(non_null) // 2)


def _to_number(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "n/a"):
        return None
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_date(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return pd.NaT
    try:
        return pd.to_datetime(val, errors="coerce")
    except Exception:
        return pd.NaT


def _norm_text(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s else None


DEAL_NUMERIC_COLS = ["Masked Deal value"]
DEAL_DATE_COLS = ["Close Date (A)", "Tentative Close Date", "Created Date"]
DEAL_TEXT_COLS = [
    "Deal Name", "Owner code", "Client Code", "Deal Status",
    "Closure Probability", "Deal Stage", "Product deal", "Sector/service",
]

WO_NUMERIC_COLS = [
    "Amount in Rupees (Excl of GST) (Masked)",
    "Amount in Rupees (Incl of GST) (Masked)",
    "Billed Value in Rupees (Excl of GST.) (Masked)",
    "Billed Value in Rupees (Incl of GST.) (Masked)",
    "Collected Amount in Rupees (Incl of GST.) (Masked)",
    "Amount to be billed in Rs. (Exl. of GST) (Masked)",
    "Amount to be billed in Rs. (Incl. of GST) (Masked)",
    "Amount Receivable (Masked)",
    "Quantity by Ops", "Quantities as per PO",
    "Quantity billed (till date)", "Balance in quantity",
]
WO_DATE_COLS = [
    "Data Delivery Date", "Date of PO/LOI", "Probable Start Date",
    "Probable End Date", "Last invoice date", "Collection Date",
]
WO_TEXT_COLS = [
    "Deal name masked", "Customer Name Code", "Serial #", "Nature of Work",
    "Execution Status", "Document Type", "BD/KAM Personnel code", "Sector",
    "Type of Work", "Invoice Status", "WO Status (billed)",
    "Collection status", "Billing Status",
]


def clean_deals(raw_items: list[dict]) -> CleanResult:
    caveats: list[str] = []
    df = pd.DataFrame(raw_items)
    if df.empty:
        return CleanResult(df, ["Deals board returned no items."])

    id_cols = [c for c in df.columns if c not in ("_item_id",)]
    stray_mask = df.apply(lambda r: _is_stray_header_row(r, id_cols), axis=1)
    n_stray = int(stray_mask.sum())
    if n_stray:
        caveats.append(
            f"Dropped {n_stray} row(s) in Deals that were duplicated header "
            f"rows embedded as data (all cells equal their column name)."
        )
    df = df.loc[~stray_mask].copy()

    for c in DEAL_TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_norm_text)
    for c in DEAL_NUMERIC_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_to_number)
    for c in DEAL_DATE_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_to_date)

    if "Deal Status" in df.columns:
        n_missing = int(df["Deal Status"].isna().sum())
        if n_missing:
            caveats.append(f"{n_missing} deal(s) have no Deal Status recorded.")
    if "Masked Deal value" in df.columns:
        n_missing = int(df["Masked Deal value"].isna().sum())
        if n_missing:
            caveats.append(f"{n_missing} deal(s) have no deal value recorded.")
    if "Sector/service" in df.columns:
        n_missing = int(df["Sector/service"].isna().sum())
        if n_missing:
            caveats.append(f"{n_missing} deal(s) have no sector/service recorded.")

    return CleanResult(df.reset_index(drop=True), caveats)


def clean_work_orders(raw_items: list[dict]) -> CleanResult:
    caveats: list[str] = []
    df = pd.DataFrame(raw_items)
    if df.empty:
        return CleanResult(df, ["Work Orders board returned no items."])

    id_cols = [c for c in df.columns if c not in ("_item_id",)]
    stray_mask = df.apply(lambda r: _is_stray_header_row(r, id_cols), axis=1)
    n_stray = int(stray_mask.sum())
    if n_stray:
        caveats.append(
            f"Dropped {n_stray} row(s) in Work Orders that were duplicated "
            f"header rows embedded as data."
        )
    df = df.loc[~stray_mask].copy()

    for c in WO_TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_norm_text)
    for c in WO_NUMERIC_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_to_number)
    for c in WO_DATE_COLS:
        if c in df.columns:
            df[c] = df[c].apply(_to_date)

    if "Execution Status" in df.columns:
        n_missing = int(df["Execution Status"].isna().sum())
        if n_missing:
            caveats.append(f"{n_missing} work order(s) have no Execution Status recorded.")
    if "Amount Receivable (Masked)" in df.columns:
        n_missing = int(df["Amount Receivable (Masked)"].isna().sum())
        if n_missing:
            caveats.append(f"{n_missing} work order(s) have no receivable amount recorded.")

    return CleanResult(df.reset_index(drop=True), caveats)


# Key fields that most drive whether a record is actually usable for BI -
# used for a simple, transparent data-hygiene score rather than a black-box one.
DEAL_HYGIENE_FIELDS = ["Deal Status", "Masked Deal value", "Sector/service", "Owner code"]
WO_HYGIENE_FIELDS = ["Execution Status", "Amount Receivable (Masked)", "Sector"]


def compute_hygiene_score(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> float:
    """
    Percentage of (record, key-field) cells that are populated, across both
    boards' most decision-relevant fields. Simple and auditable on purpose -
    a founder can see exactly which fields are being checked, rather than a
    score with no clear definition.
    """
    total = 0
    filled = 0
    for df, fields in ((deals_df, DEAL_HYGIENE_FIELDS), (wo_df, WO_HYGIENE_FIELDS)):
        if df.empty:
            continue
        for f in fields:
            if f not in df.columns:
                continue
            total += len(df)
            filled += int(df[f].notna().sum())
    if total == 0:
        return 0.0
    return round(filled / total * 100, 1)
