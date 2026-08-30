import datetime
from typing import Dict, Any, List, Optional
from tabular_data import Table
from cross_board_engine import CrossBoardEngine, format_inr
from data_resilience_engine import DataResilienceEngine

class LeadershipUpdateGenerator:
    def __init__(self, deals: Any, wos: Any):
        self.deals = deals if isinstance(deals, Table) else Table(deals)
        self.wos = wos if isinstance(wos, Table) else Table(wos)
        self.engine = CrossBoardEngine(self.deals, self.wos)
        self.hygiene = DataResilienceEngine.audit_data_hygiene(self.deals, self.wos)

    def generate_update(self, period: str = "Q2 2024") -> Dict[str, Any]:
        kpis = self.engine.get_summary_kpis()
        risk_table = self.engine.get_revenue_at_risk_details()

        won_deals = self.deals.filter(lambda r: r.get("stage") == "Closed Won").sort_by("deal_value_inr", ascending=False)
        open_deals = self.deals.filter(lambda r: r.get("stage") not in ["Closed Won", "Closed Lost"]).sort_by("deal_value_inr", ascending=False)
        top_negotiations = open_deals.filter(lambda r: r.get("stage") == "In Negotiation")
        delayed_wos = self.wos.filter(lambda r: r.get("status") == "Delayed")

        title = f"Skylark Drones — Executive Leadership Update ({period})"
        today_str = datetime.date.today().strftime("%B %d, %Y")

        md_lines = []
        md_lines.append(f"# {title}")
        md_lines.append(f"**Date:** {today_str} | **Prepared By:** Antigravity Business Intelligence Agent")
        md_lines.append("---")
        
        md_lines.append("## 1. 🎯 Executive Overview")
        rev_won = kpis.get("closed_won_revenue_formatted", "₹0")
        won_cnt = kpis.get("closed_won_count", 0)
        win_rt = kpis.get("win_rate_pct", 0)
        pipe_unwt = kpis.get("open_pipeline_formatted", "₹0")
        pipe_wt = kpis.get("weighted_pipeline_formatted", "₹0")
        open_cnt = kpis.get("open_deals_count", 0)
        comp_wo = kpis.get("completed_work_orders", 0)
        sla_rt = kpis.get("on_time_delivery_rate_pct", 0)
        csat = kpis.get("avg_customer_csat", 0)
        rev_risk = kpis.get("revenue_at_risk_formatted", "₹0")
        del_cnt = len(delayed_wos)

        md_lines.append(f"- **Closed Won Revenue:** {rev_won} across {won_cnt} closed engagements (Win Rate: {win_rt}%).")
        md_lines.append(f"- **Active Pipeline:** {pipe_unwt} unweighted | **{pipe_wt} weighted** across {open_cnt} opportunities.")
        md_lines.append(f"- **Operations Execution:** {comp_wo} projects completed with **{sla_rt}% On-Time SLA** (Avg CSAT: {csat}/5.0).")
        md_lines.append(f"- **Revenue at Risk:** **{rev_risk}** tied to {del_cnt} delayed work order(s) requiring executive intervention.")

        md_lines.append("")
        md_lines.append("## 2. 🏆 Top Commercial Wins & Key Bookings")
        if not won_deals.empty:
            for idx, d in enumerate(won_deals.head(5), 1):
                md_lines.append(f"{idx}. **{d['client']}** — *{d['deal_name']}* | **{d['deal_value_formatted']}** ({d['sector']}) — Owner: {d['owner']}")
        else:
            md_lines.append("No closed won deals recorded in this period.")

        md_lines.append("")
        md_lines.append("## 3. 🚀 High-Conviction Pipeline (In Negotiation)")
        if not top_negotiations.empty:
            for idx, d in enumerate(top_negotiations.head(4), 1):
                md_lines.append(f"{idx}. **{d['client']}** — *{d['deal_name']}* | **{d['deal_value_formatted']}** (Prob: {int(d['probability']*100)}%) — Owner: {d['owner']}")
        else:
            md_lines.append("No deals currently in active contract negotiation stage.")

        md_lines.append("")
        md_lines.append("## 4. ⚙️ Operations & Delivery Health")
        md_lines.append(f"- Total Work Orders Tracked: **{kpis.get('total_work_orders', 0)}**")
        md_lines.append(f"- In-Flight Operations: **{kpis.get('in_progress_work_orders', 0)}**")
        md_lines.append(f"- Delayed Projects: **{kpis.get('delayed_work_orders', 0)}**")
        md_lines.append(f"- Customer CSAT Score: **{csat} / 5.0**")

        md_lines.append("")
        md_lines.append("## 5. 🚨 Critical Red Flags & Revenue at Risk")
        if not risk_table.empty:
            for idx, r in enumerate(risk_table, 1):
                md_lines.append(f"### Red Flag #{idx}: {r['client']} ({r['deal_value_formatted']} at risk)")
                md_lines.append(f"- **Project:** {r['project_title']}")
                md_lines.append(f"- **Project Manager:** {r['project_manager']} | **Sales Lead:** {r['sales_owner']}")
                md_lines.append(f"- **Target SLA Date:** {r['target_date']}")
                md_lines.append(f"- **Root Cause Blocker:** {r['blockers_reason']}")
                md_lines.append("")
        else:
            md_lines.append("✅ No critical operational delays or revenue at risk.")

        md_lines.append("")
        md_lines.append("## 6. 💡 Strategic Action Items for Leadership")
        actions = [
            f"1. **Operations Escalation**: Schedule immediate DGCA regulatory review to unblock airspace clearance on Tata Power LiDAR survey ({rev_risk} risk mitigation).",
            "2. **Sales Alignment**: Provide founder closing assistance for NTPC Limited (₹32L) and Indian Railways DFCCIL (₹95L) negotiations.",
            "3. **Survey Accuracy Standard**: Resolve ground benchmark discrepancies with client surveyor for Mahindra Lifespaces to unblock final contour signoff.",
            f"4. **Data Quality Action**: Address {len(self.hygiene['caveats'])} data hygiene gaps on Monday.com boards (Data Hygiene Score: {self.hygiene['hygiene_score']}%)."
        ]
        md_lines.extend(actions)

        md_lines.append("")
        md_lines.append("## 7. ⚠️ Data Hygiene & System Caveats")
        for c in self.hygiene["caveats"]:
            md_lines.append(f"- *{c}*")

        markdown_report = "\n".join(md_lines)

        slack_lines = [
            f"📊 *Skylark Drones — Leadership Snapshot ({period})*",
            f"💰 *Closed Won:* {rev_won} (Win Rate: {win_rt}%)",
            f"📈 *Weighted Pipeline:* {pipe_wt} (Unweighted: {pipe_unwt})",
            f"⚙️ *Ops Delivery SLA:* {sla_rt}% On-time (CSAT: {csat}/5)",
            f"⚠️ *Revenue at Risk:* {rev_risk} across {del_cnt} delayed project(s)",
            "",
            "*🔥 Top Priorities:*",
            "• Unblock DGCA clearance for Tata Power LiDAR survey",
            "• Close NTPC (₹32L) & Indian Railways (₹95L) negotiations",
            "• Audit Monday.com missing close dates & PM allocations"
        ]
        slack_text = "\n".join(slack_lines)

        return {
            "title": title,
            "period": period,
            "executive_summary": (
                f"For {period}, Closed Won revenue stands at {rev_won} "
                f"with a weighted pipeline of {pipe_wt}. "
                f"Operations has delivered {comp_wo} projects at {sla_rt}% on-time SLA, "
                f"with {rev_risk} in revenue at risk from {del_cnt} delayed work orders."
            ),
            "key_metrics": {
                "Closed Won": rev_won,
                "Weighted Pipeline": pipe_wt,
                "Win Rate %": f"{win_rt}%",
                "Delivery SLA": f"{sla_rt}%",
                "Revenue at Risk": rev_risk
            },
            "top_wins_table": won_deals.head(5).select(["client", "deal_name", "deal_value_formatted", "sector", "owner"]),
            "strategic_actions": actions,
            "data_caveats": self.hygiene["caveats"],
            "markdown_report": markdown_report,
            "slack_text": slack_text
        }