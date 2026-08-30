"""
Leadership update report generator.

Design decision (see DECISION_LOG.md): the reference example report shown
for this assignment included fields (CSAT scores, named root-cause
blockers, SLA target dates, unmasked company names) that simply do not
exist as columns on the real Deals / Work Orders boards. Rather than
inventing plausible-looking numbers for fields we don't have, this
generator computes a leadership update strictly from fields that are
actually present, and explicitly calls out which classic BI questions
(e.g. CSAT, contractual SLA dates) can't be answered with the current
board schema. That gap-naming is itself a "leadership update" a founder
can act on (add the missing columns).

Assumptions made explicit here:
- "Won" = Deal Status == "Won". "Lost" = Deal Status == "Dead".
  Win rate = Won / (Won + Dead) among deals with a terminal status.
- Weighted pipeline uses Closure Probability buckets: High=75%,
  Medium=50%, Low=25%, unspecified=0% (excluded from weighted sum but
  included in unweighted sum, flagged as a caveat).
- "Revenue at risk" on the ops side is proxied by outstanding
  "Amount Receivable (Masked)" on work orders whose Execution Status
  is not "Completed" - there's no explicit red-flag/blocker field on
  the real board, so this is the closest available signal, and is
  labeled as such rather than presented as a literal red-flag list.
"""

from __future__ import annotations

import pandas as pd

import cross_link
import data_processing as dp

PROB_WEIGHTS = {"High": 0.75, "Medium": 0.50, "Low": 0.25}


def _fmt_inr(x: float) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.2f} L"
    return f"₹{x:,.0f}"


def build_leadership_report(deals: pd.DataFrame, work_orders: pd.DataFrame,
                             deal_caveats: list[str], wo_caveats: list[str]) -> str:
    lines: list[str] = []
    lines.append("# Skylark Drones — Leadership Update")
    lines.append("_Generated live from monday.com Deals + Work Orders boards._\n")

    # --- Sales / pipeline ---
    won = deals[deals["Deal Status"] == "Won"] if "Deal Status" in deals else deals.iloc[0:0]
    lost = deals[deals["Deal Status"] == "Dead"] if "Deal Status" in deals else deals.iloc[0:0]
    open_deals = deals[deals["Deal Status"] == "Open"] if "Deal Status" in deals else deals.iloc[0:0]

    won_revenue = won["Masked Deal value"].sum(skipna=True) if not won.empty else 0.0
    terminal = len(won) + len(lost)
    win_rate = (len(won) / terminal * 100) if terminal else None

    open_unweighted = open_deals["Masked Deal value"].sum(skipna=True) if not open_deals.empty else 0.0
    n_unweighted_prob = 0
    weighted_total = 0.0
    if not open_deals.empty and "Closure Probability" in open_deals.columns:
        for _, row in open_deals.iterrows():
            val = row.get("Masked Deal value")
            prob = row.get("Closure Probability")
            if pd.isna(val):
                continue
            weight = PROB_WEIGHTS.get(prob)
            if weight is None:
                n_unweighted_prob += 1
                continue
            weighted_total += val * weight

    lines.append("## 1. Sales & Pipeline")
    lines.append(f"- **Closed Won Revenue:** {_fmt_inr(won_revenue)} across {len(won)} deal(s)")
    if win_rate is not None:
        lines.append(f"- **Win Rate:** {win_rate:.1f}% ({len(won)} won / {terminal} closed)")
    else:
        lines.append("- **Win Rate:** not computable (no closed deals with a Won/Dead status)")
    lines.append(f"- **Active Pipeline:** {_fmt_inr(open_unweighted)} unweighted across {len(open_deals)} open deal(s)")
    lines.append(f"- **Weighted Pipeline:** {_fmt_inr(weighted_total)} "
                  f"(using High/Medium/Low closure-probability weights of 75/50/25%)")
    if n_unweighted_prob:
        lines.append(f"  - _{n_unweighted_prob} open deal(s) have no closure probability set and are "
                      f"excluded from the weighted figure._")

    if "Sector/service" in deals.columns and not open_deals.empty:
        by_sector = (open_deals.groupby("Sector/service")["Masked Deal value"]
                     .sum(min_count=1).sort_values(ascending=False))
        lines.append("\n**Open pipeline by sector:**")
        for sector, val in by_sector.items():
            if pd.isna(sector):
                continue
            lines.append(f"- {sector}: {_fmt_inr(val)}")

    # --- Top wins ---
    if not won.empty:
        lines.append("\n## 2. Top Commercial Wins")
        top_wins = won.sort_values("Masked Deal value", ascending=False).head(5)
        for i, (_, row) in enumerate(top_wins.iterrows(), 1):
            name = row.get("Deal Name") or "Unnamed deal"
            sector = row.get("Sector/service") or "Sector unknown"
            owner = row.get("Owner code") or "Owner unassigned"
            lines.append(f"{i}. **{name}** — {_fmt_inr(row.get('Masked Deal value'))} "
                         f"({sector}) — Owner: {owner}")

    # --- High conviction pipeline ---
    if not open_deals.empty:
        neg_stages = ["F. Negotiations", "H. Work Order Received", "E. Proposal/Commercials Sent"]
        conviction = open_deals[open_deals["Deal Stage"].isin(neg_stages)] if "Deal Stage" in open_deals else open_deals.iloc[0:0]
        conviction = conviction.sort_values("Masked Deal value", ascending=False).head(5)
        if not conviction.empty:
            lines.append("\n## 3. High-Conviction Pipeline (Negotiation / Proposal / WO Received)")
            for i, (_, row) in enumerate(conviction.iterrows(), 1):
                name = row.get("Deal Name") or "Unnamed deal"
                stage = row.get("Deal Stage") or "Stage unknown"
                owner = row.get("Owner code") or "Owner unassigned"
                lines.append(f"{i}. **{name}** — {_fmt_inr(row.get('Masked Deal value'))} "
                             f"({stage}) — Owner: {owner}")

    # --- Operations ---
    lines.append("\n## 4. Operations & Delivery")
    total_wo = len(work_orders)
    lines.append(f"- Total Work Orders Tracked: **{total_wo}**")
    if "Execution Status" in work_orders.columns:
        status_counts = work_orders["Execution Status"].value_counts(dropna=True)
        for status, count in status_counts.items():
            lines.append(f"  - {status}: {count}")

    if "Amount Receivable (Masked)" in work_orders.columns and "Execution Status" in work_orders.columns:
        at_risk = work_orders[
            (work_orders["Execution Status"] != "Completed") &
            (work_orders["Amount Receivable (Masked)"].fillna(0) > 0)
        ].sort_values("Amount Receivable (Masked)", ascending=False)
        total_receivable_at_risk = at_risk["Amount Receivable (Masked)"].sum(skipna=True)
        lines.append(f"\n## 5. Outstanding Receivables on Incomplete Work ({_fmt_inr(total_receivable_at_risk)})")
        lines.append("_Proxy for 'revenue at risk' — no explicit blocker/red-flag field exists on this "
                     "board, so this lists incomplete work orders with the largest uncollected amounts._")
        for i, (_, row) in enumerate(at_risk.head(5).iterrows(), 1):
            name = row.get("Deal name masked") or "Unnamed project"
            cust = row.get("Customer Name Code") or "Customer unknown"
            amt = row.get("Amount Receivable (Masked)")
            status = row.get("Execution Status") or "status unknown"
            lines.append(f"{i}. **{name}** ({cust}) — {_fmt_inr(amt)} receivable — {status}")

    # --- Sales momentum already in delivery ---
    linked, link_caveat = cross_link.deals_with_open_work_orders(deals, work_orders)
    if not linked.empty:
        lines.append(f"\n## 6. Open Deals Already in Active Delivery ({len(linked)})")
        lines.append(f"_{link_caveat}_")
        for _, row in linked.sort_values("Masked Deal value", ascending=False).head(5).iterrows():
            lines.append(f"- **{row.get('Deal Name') or 'Unnamed deal'}** — "
                         f"{_fmt_inr(row.get('Masked Deal value'))} — {row.get('Sector/service') or 'sector unknown'}")

    # --- Data hygiene ---
    hygiene_score = dp.compute_hygiene_score(deals, work_orders)
    lines.append(f"\n## 7. Data Quality Caveats (Data Hygiene Score: {hygiene_score}%)")
    lines.append("_Score = % of records with their key decision fields populated "
                 f"({', '.join(dp.DEAL_HYGIENE_FIELDS)} on Deals; {', '.join(dp.WO_HYGIENE_FIELDS)} on Work Orders)._")
    all_caveats = deal_caveats + wo_caveats
    if all_caveats:
        for c in all_caveats:
            lines.append(f"- {c}")
    else:
        lines.append("- No data quality issues detected in this pull.")

    lines.append("\n## 8. What This Report Can't Tell You (Yet)")
    lines.append("- No CSAT / customer satisfaction field exists on either board.")
    lines.append("- No contractual SLA target date field exists on Work Orders, so on-time-delivery "
                  "% can't be computed as given - only Execution Status counts are available.")
    lines.append("- No named root-cause/blocker field exists for delayed work, so blockers can't be "
                 "auto-summarized without a free-text notes column being added to the board.")

    return "\n".join(lines)
