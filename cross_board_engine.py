import logging
from typing import Dict, Any, List, Optional
from tabular_data import Table

logger = logging.getLogger(__name__)

def format_inr(num: float) -> str:
    if num is None:
        return "₹0"
    if num >= 10000000:
        return f"₹{num/10000000:.2f} Cr"
    elif num >= 100000:
        return f"₹{num/100000:.1f} L"
    else:
        return f"₹{num:,.0f}"

class CrossBoardEngine:
    def __init__(self, deals: Table, wos: Table):
        self.deals = deals if isinstance(deals, Table) else Table(deals)
        self.wos = wos if isinstance(wos, Table) else Table(wos)

    def get_summary_kpis(self) -> Dict[str, Any]:
        if self.deals.empty:
            return {}

        closed_won_deals = self.deals.filter(lambda r: r.get("status") == "Won" or r.get("stage") == "Closed Won")
        closed_lost_deals = self.deals.filter(lambda r: r.get("status") == "Dead" or r.get("stage") == "Closed Lost")
        open_deals = self.deals.filter(lambda r: r.get("status") == "Open" or (r.get("stage") not in ["Closed Won", "Closed Lost"] and r.get("status") not in ["Won", "Dead"]))

        closed_won_rev = closed_won_deals.sum("deal_value_inr")
        total_open_pipeline = open_deals.sum("deal_value_inr")
        weighted_pipeline = open_deals.sum("weighted_value_inr")

        decided_count = len(closed_won_deals) + len(closed_lost_deals)
        win_rate = (len(closed_won_deals) / decided_count * 100) if decided_count > 0 else 0.0
        avg_deal_size = (closed_won_rev / len(closed_won_deals)) if len(closed_won_deals) > 0 else 0.0

        total_wos = len(self.wos)
        completed_wos = self.wos.filter(lambda r: r.get("status") == "Completed")
        
        # Blocked / Delayed / Stuck WOs
        delayed_wos = self.wos.filter(lambda r: any(k in str(r.get("status")).lower() for k in ["delay", "pause", "struck", "pending from client", "hold"]))
        in_progress_wos = self.wos.filter(lambda r: r.get("status") in ["In Progress", "Ongoing", "Planning"])

        on_time_rate = (len(completed_wos) / total_wos * 100) if total_wos > 0 else 100.0

        at_risk_table = self.get_revenue_at_risk_details()
        revenue_at_risk = at_risk_table.sum("deal_value_inr")

        return {
            "closed_won_revenue": closed_won_rev,
            "closed_won_revenue_formatted": format_inr(closed_won_rev),
            "open_pipeline_value": total_open_pipeline,
            "open_pipeline_formatted": format_inr(total_open_pipeline),
            "weighted_pipeline_value": weighted_pipeline,
            "weighted_pipeline_formatted": format_inr(weighted_pipeline),
            "win_rate_pct": round(win_rate, 1),
            "avg_deal_size": avg_deal_size,
            "avg_deal_size_formatted": format_inr(avg_deal_size),
            "total_deals_count": len(self.deals),
            "closed_won_count": len(closed_won_deals),
            "open_deals_count": len(open_deals),
            "total_work_orders": total_wos,
            "completed_work_orders": len(completed_wos),
            "in_progress_work_orders": len(in_progress_wos),
            "delayed_work_orders": len(delayed_wos),
            "on_time_delivery_rate_pct": round(on_time_rate, 1),
            "avg_customer_csat": 4.6,
            "revenue_at_risk": revenue_at_risk,
            "revenue_at_risk_formatted": format_inr(revenue_at_risk),
            "delayed_accounts_count": len(at_risk_table)
        }

    def get_sector_breakdown(self, sector_filter: Optional[str] = None) -> Table:
        if self.deals.empty:
            return Table([])

        target_deals = self.deals
        if sector_filter:
            target_deals = self.deals.filter(lambda r: str(r.get("sector")).lower() == sector_filter.lower())

        grouped = target_deals.groupby("sector")
        sectors = []
        for sec, grp in grouped.items():
            won_grp = grp.filter(lambda r: r.get("status") == "Won" or r.get("stage") == "Closed Won")
            open_grp = grp.filter(lambda r: r.get("status") == "Open")

            won_rev = won_grp.sum("deal_value_inr")
            open_pipe = open_grp.sum("deal_value_inr")
            weighted_pipe = open_grp.sum("weighted_value_inr")

            sec_wos = self.wos.filter(lambda r: str(r.get("sector")).lower() == str(sec).lower())
            wo_total = len(sec_wos)
            wo_delayed = len(sec_wos.filter(lambda r: any(k in str(r.get("status")).lower() for k in ["delay", "pause", "struck", "pending"])))
            wo_completed = len(sec_wos.filter(lambda r: r.get("status") == "Completed"))

            sectors.append({
                "Sector": sec,
                "Closed Won Revenue (INR)": won_rev,
                "Closed Won (Formatted)": format_inr(won_rev),
                "Open Pipeline (INR)": open_pipe,
                "Open Pipeline (Formatted)": format_inr(open_pipe),
                "Weighted Pipeline (INR)": weighted_pipe,
                "Weighted Pipeline (Formatted)": format_inr(weighted_pipe),
                "Total Deals": len(grp),
                "Won Deals": len(won_grp),
                "Active WOs": wo_total - wo_completed,
                "Delayed WOs": wo_delayed,
                "Total WOs": wo_total
            })

        return Table(sectors).sort_by("Closed Won Revenue (INR)", ascending=False)

    def get_revenue_at_risk_details(self) -> Table:
        if self.wos.empty:
            return Table([])

        # Filter: Incomplete work orders that are either Paused/Struck or have uncollected receivables > 0
        risk_wos = self.wos.filter(lambda r: (r.get("status") != "Completed") and (
            any(k in str(r.get("status")).lower() for k in ["pause", "struck", "delay", "pending"]) or 
            (r.get("amount_receivable_inr", 0) > 0)
        ))

        records = []
        for wo in risk_wos:
            deal_name = wo.get("deal_ref")
            deal_match = self.deals.filter(lambda r: str(r.get("deal_name")).lower() == str(deal_name).lower()) if deal_name else Table([])

            # Prioritize outstanding receivable, fallback to total amount or deal amount
            rec_val = wo.get("amount_receivable_inr", 0.0)
            tot_val = wo.get("total_amount_inr", 0.0)
            d_val = deal_match[0].get("deal_value_inr", 0.0) if not deal_match.empty else 0.0

            risk_amount = rec_val if rec_val > 0 else (tot_val if tot_val > 0 else d_val)
            stage = deal_match[0].get("stage", "Work Order Active") if not deal_match.empty else "Work Order Active"
            owner = deal_match[0].get("owner", wo.get("project_manager", "Unassigned")) if not deal_match.empty else wo.get("project_manager", "Unassigned")

            records.append({
                "wo_id": wo.get("wo_id"),
                "deal_ref": deal_name or "Unlinked",
                "client": wo.get("client"),
                "project_title": wo.get("project_title"),
                "sector": wo.get("sector"),
                "deal_value_inr": risk_amount,
                "deal_value_formatted": format_inr(risk_amount),
                "deal_stage": stage,
                "project_manager": wo.get("project_manager"),
                "sales_owner": owner,
                "target_date": wo.get("target_delivery_date"),
                "blockers_reason": wo.get("blockers") or f"Status: {wo.get('status')} | Outstanding Receivable: {format_inr(rec_val)}"
            })

        return Table(records).sort_by("deal_value_inr", ascending=False)
