"""
Best-effort linkage between the Deals board and the Work Orders board.

There is no shared unique ID between the two real boards. The closest
available link is name-based: "Deal Name" on Deals and "Deal name masked"
on Work Orders use the same masked-name convention (e.g. "Sakura",
"Scooby-Doo") - but names are NOT unique (the same name is reused across
multiple distinct deals/work orders), so this is an approximate,
many-to-many join, not a reliable foreign key.

We deliberately did NOT try to invent a synthetic unique ID (e.g. by
pairing owner-code-like fields) after finding that approach produces
false-positive joins on the real data. Instead this module does the
join at the *name* level and is explicit in its output about the
imprecision, rather than presenting a confident 1:1 mapping that isn't
actually there.
"""

from __future__ import annotations

import pandas as pd


def deals_with_open_work_orders(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """
    Returns (subset of open deals whose name matches at least one
    non-completed work order, caveat string).
    """
    if deals_df.empty or wo_df.empty:
        return deals_df.iloc[0:0], "No linkage possible - one of the boards is empty."
    if "Deal Name" not in deals_df.columns or "Deal name masked" not in wo_df.columns:
        return deals_df.iloc[0:0], "Linkage columns not found on one of the boards."

    open_deals = deals_df[deals_df.get("Deal Status") == "Open"] if "Deal Status" in deals_df.columns else deals_df
    active_wo_names = set(
        wo_df.loc[wo_df.get("Execution Status") != "Completed", "Deal name masked"].dropna().str.strip().str.lower()
    )
    matched = open_deals[open_deals["Deal Name"].dropna().str.strip().str.lower().isin(active_wo_names)] \
        if not open_deals.empty else open_deals

    caveat = (
        "Deal↔Work Order matching is name-based only (no shared unique ID exists on these boards), "
        "so it's approximate - the same name can refer to more than one deal or work order."
    )
    return matched, caveat
