import re
import logging
from typing import Dict, Any, List, Optional
from tabular_data import Table
from cross_board_engine import CrossBoardEngine, format_inr
from data_resilience_engine import DataResilienceEngine

logger = logging.getLogger(__name__)

class BIAgentCore:
    def __init__(self, deals: Any, wos: Any, llm_provider: str = "offline", llm_api_key: Optional[str] = None):
        self.deals = DataResilienceEngine.clean_deals(deals)
        self.wos = DataResilienceEngine.clean_work_orders(wos)
        self.engine = CrossBoardEngine(self.deals, self.wos)
        self.hygiene = DataResilienceEngine.audit_data_hygiene(self.deals, self.wos)
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key

    def process_query(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower().strip()

        # Step 1: Detect Sector
        detected_sector = None
        for sec in ["Energy & Utilities", "Infrastructure", "Mining & Metals", "Agriculture", "Defence & Security", "Forestry & Environment"]:
            for word in sec.lower().replace("&", " ").split():
                if word in q_lower and len(word) > 3:
                    detected_sector = sec
                    break
        if not detected_sector:
            if any(w in q_lower for w in ["energy", "solar", "power", "wind", "thermal", "utilities"]):
                detected_sector = "Energy & Utilities"
            elif any(w in q_lower for w in ["infra", "road", "highway", "railway", "construction", "smart city"]):
                detected_sector = "Infrastructure"
            elif any(w in q_lower for w in ["mining", "mine", "coal", "ore", "limestone", "cement"]):
                detected_sector = "Mining & Metals"
            elif any(w in q_lower for w in ["agri", "crop", "farm"]):
                detected_sector = "Agriculture"
            elif any(w in q_lower for w in ["defence", "defense", "security", "border"]):
                detected_sector = "Defence & Security"

        # Step 2: Detect Quarter
        detected_quarter = None
        q_match = re.search(r"(?i)q([1-4])(?:\s*(\d{4}))?", q_lower)
        if q_match:
            q_num = q_match.group(1)
            year = q_match.group(2) or "2024"
            detected_quarter = f"Q{q_num} {year}"
        elif "this quarter" in q_lower or "current quarter" in q_lower:
            detected_quarter = "Q2 2024"
        elif "next quarter" in q_lower:
            detected_quarter = "Q3 2024"

        # Step 3: Intent Classification (Prioritize Cross-Board Risk and High-Value checks first)
        
        # Cross-Board Risk & High-Value Delayed Clients
        if any(w in q_lower for w in ["risk", "at risk", "revenue at risk", "high-value", "high value", "delayed client", "delayed clients", "delayed account", "delayed accounts", "bottleneck"]):
            return self._handle_revenue_at_risk_query()

        # Leadership Update Query
        if any(w in q_lower for w in ["leadership update", "executive update", "board update", "weekly update", "summary for founders", "c-suite"]):
            return self._handle_leadership_update_intent(detected_quarter)

        # Sector Pipeline Query (e.g. "How is our pipeline looking for energy sector this quarter?")
        if detected_sector and any(w in q_lower for w in ["pipe", "pipeline", "deal", "outlook", "look", "how", "forecast", "funnel"]):
            return self._handle_sector_pipeline_query(detected_sector, detected_quarter, query)

        # General Pipeline & Revenue Overview
        if any(w in q_lower for w in ["pipeline", "pipeline health", "conversion", "funnel", "win rate", "average deal size"]):
            return self._handle_pipeline_overview(detected_quarter)

        # Operational Health / Work Orders SLA / General Operations
        if any(w in q_lower for w in ["work order", "execution", "delivery", "delay", "delayed", "sla", "on-time", "operations", "blocker"]):
            return self._handle_operations_query(detected_sector)

        # Client Drilldown
        clients = self.deals.unique("client")
        matched_client = next((c for c in clients if str(c).lower() in q_lower), None)
        if matched_client:
            return self._handle_client_drilldown(matched_client)

        # Sector Comparison
        if any(w in q_lower for w in ["sector", "industry", "vertical", "market"]):
            return self._handle_sector_comparison_query()

        # Data Hygiene & Quality
        if any(w in q_lower for w in ["data quality", "hygiene", "missing", "caveat", "clean", "accuracy", "audit"]):
            return self._handle_data_hygiene_query()

        return self._handle_ambiguous_query(query)

    def _handle_sector_pipeline_query(self, sector: str, quarter: Optional[str], original_query: str) -> Dict[str, Any]:
        sec_deals = self.deals.filter(lambda r: r.get("sector") == sector)
        if quarter:
            sec_deals = sec_deals.filter(lambda r: r.get("quarter") == quarter)

        won_deals = sec_deals.filter(lambda r: r.get("stage") == "Closed Won")
        open_deals = sec_deals.filter(lambda r: r.get("stage") not in ["Closed Won", "Closed Lost"])

        won_rev = won_deals.sum("deal_value_inr")
        open_pipe = open_deals.sum("deal_value_inr")
        weighted_pipe = open_deals.sum("weighted_value_inr")

        sec_wos = self.wos.filter(lambda r: r.get("sector") == sector)
        delayed_wos = sec_wos.filter(lambda r: r.get("status") == "Delayed")

        q_text = f" for **{quarter}**" if quarter else " (All Quarters)"
        
        summary = (
            f"For **{sector}**{q_text}, total open pipeline stands at **{format_inr(open_pipe)}** "
            f"(weighted: **{format_inr(weighted_pipe)}** across {len(open_deals)} open deals), "
            f"with **{format_inr(won_rev)}** in Closed Won revenue ({len(won_deals)} closed deals)."
        )

        recommendations = []
        if not delayed_wos.empty:
            recommendations.append(
                f"⚠️ **Operational Risk**: {len(delayed_wos)} active work order(s) in {sector} are currently delayed "
                f"(e.g., {delayed_wos[0]['project_title']}). Delivery delays may jeopardize upcoming contract renewals."
            )
        neg_deals = open_deals.filter(lambda r: r.get("stage") == "In Negotiation")
        if not neg_deals.empty:
            top_neg = neg_deals.sort_by("deal_value_inr", ascending=False)[0]
            recommendations.append(
                f"🎯 **Sales Priority**: Focus executive closing support on **{top_neg['deal_name']}** ({top_neg['client']}) valued at {top_neg['deal_value_formatted']}."
            )
        else:
            recommendations.append(f"💡 Accelerate lead generation and proposal submissions in {sector} to bolster downstream conversion.")

        table = sec_deals.select(["deal_name", "client", "deal_value_formatted", "stage", "probability", "owner", "quarter"])
        caveats = [c for c in self.hygiene["caveats"] if sector.lower() in c.lower()]
        if not caveats:
            caveats = ["All values normalized from mixed INR/USD formats into standardized base INR currency."]

        return {
            "intent": "SECTOR_PIPELINE",
            "title": f"📊 {sector} Pipeline Analysis {q_text}",
            "executive_summary": summary,
            "metrics": {
                "Open Pipeline": format_inr(open_pipe),
                "Weighted Pipeline": format_inr(weighted_pipe),
                "Closed Won Revenue": format_inr(won_rev),
                "Active Deals Count": len(open_deals),
                "Sector Work Orders": len(sec_wos),
                "Delayed Work Orders": len(delayed_wos)
            },
            "data_table": table,
            "caveats": caveats,
            "recommendations": recommendations,
            "suggested_followups": [
                f"Show delayed work orders for {sector}",
                f"What is our revenue at risk in {sector}?",
                "Compare pipeline across all sectors",
                "Prepare leadership update"
            ]
        }

    def _handle_pipeline_overview(self, quarter: Optional[str]) -> Dict[str, Any]:
        kpis = self.engine.get_summary_kpis()
        summary = (
            f"Overall sales pipeline comprises **{format_inr(kpis['open_pipeline_value'])}** across {kpis['open_deals_count']} active deals, "
            f"with a probability-weighted valuation of **{format_inr(kpis['weighted_pipeline_value'])}**. "
            f"Cumulative Closed Won revenue is **{format_inr(kpis['closed_won_revenue'])}** ({kpis['closed_won_count']} deals), "
            f"delivering a win rate of **{kpis['win_rate_pct']}%** with an average deal size of **{kpis['avg_deal_size_formatted']}**."
        )

        recommendations = [
            f"🎯 **High-Leverage Pipeline**: Weighted pipeline of {kpis['weighted_pipeline_formatted']} represents ~{(kpis['weighted_pipeline_value']/max(kpis['open_pipeline_value'],1))*100:.0f}% conversion expectation.",
            "💡 Cross-reference open deals against current flight crew bandwidth before committing to Q3 delivery dates."
        ]

        table = self.deals.select(["deal_name", "client", "sector", "deal_value_formatted", "stage", "owner", "quarter"])

        return {
            "intent": "PIPELINE_OVERVIEW",
            "title": "📈 Sales Pipeline & Revenue Velocity Overview",
            "executive_summary": summary,
            "metrics": {
                "Total Open Pipeline": kpis["open_pipeline_formatted"],
                "Weighted Pipeline": kpis["weighted_pipeline_formatted"],
                "Closed Won Revenue": kpis["closed_won_revenue_formatted"],
                "Win Rate %": f"{kpis['win_rate_pct']}%",
                "Average Deal Size": kpis["avg_deal_size_formatted"],
                "Active Deals": kpis["open_deals_count"]
            },
            "data_table": table,
            "caveats": self.hygiene["caveats"],
            "recommendations": recommendations,
            "suggested_followups": [
                "Which sector has the highest weighted pipeline?",
                "Which deals are currently in negotiation?",
                "Show high-value clients with delayed work orders",
                "Prepare leadership update for this quarter"
            ]
        }

    def _handle_operations_query(self, sector: Optional[str]) -> Dict[str, Any]:
        kpis = self.engine.get_summary_kpis()
        target_wos = self.wos if not sector else self.wos.filter(lambda r: r.get("sector") == sector)

        delayed_wos = target_wos.filter(lambda r: r.get("status") == "Delayed")
        completed_wos = target_wos.filter(lambda r: r.get("status") == "Completed")
        in_prog_wos = target_wos.filter(lambda r: r.get("status") == "In Progress")

        summary = (
            f"Operations is tracking **{len(target_wos)} work orders**: **{len(completed_wos)} completed**, "
            f"**{len(in_prog_wos)} in progress**, and **{len(delayed_wos)} delayed**. "
            f"Historical on-time delivery rate is **{kpis['on_time_delivery_rate_pct']}%** with an average customer CSAT of **{kpis['avg_customer_csat']}/5.0**."
        )

        recommendations = []
        if not delayed_wos.empty:
            for d in delayed_wos:
                recommendations.append(
                    f"⚠️ **Critical Delay ({d['client']})**: *{d['project_title']}* managed by **{d['project_manager']}** — Blocker: {d['blockers'] or 'Investigation required'}."
                )
        else:
            recommendations.append("✅ Operations are running smoothly with no active blockers recorded.")

        table = target_wos.select(["wo_id", "client", "project_title", "sector", "status", "project_manager", "target_delivery_date", "blockers"])

        return {
            "intent": "OPERATIONS_HEALTH",
            "title": "⚙️ Operational Delivery & Work Order Tracker",
            "executive_summary": summary,
            "metrics": {
                "Total Work Orders": len(target_wos),
                "Completed WOs": len(completed_wos),
                "In Progress WOs": len(in_prog_wos),
                "Delayed WOs": len(delayed_wos),
                "On-Time Delivery %": f"{kpis['on_time_delivery_rate_pct']}%",
                "Customer CSAT": f"{kpis['avg_customer_csat']} / 5.0"
            },
            "data_table": table,
            "caveats": [c for c in self.hygiene["caveats"] if "work order" in c.lower() or "pm" in c.lower()] or ["No operational data integrity issues found."],
            "recommendations": recommendations,
            "suggested_followups": [
                "What is our revenue at risk from delayed work orders?",
                "Which PM has the highest on-time delivery rate?",
                "Show unlinked operational work orders",
                "Prepare leadership update"
            ]
        }

    def _handle_revenue_at_risk_query(self) -> Dict[str, Any]:
        risk_table = self.engine.get_revenue_at_risk_details()
        if risk_table.empty:
            return {
                "intent": "REVENUE_AT_RISK",
                "title": "🛡️ Cross-Board Revenue at Risk Audit",
                "executive_summary": "No revenue is currently at risk. All active work orders are on schedule.",
                "metrics": {"Revenue at Risk": "₹0", "Delayed Accounts": 0},
                "data_table": Table([]),
                "caveats": [],
                "recommendations": ["Maintain weekly PM milestone check-ins to preempt field delays."],
                "suggested_followups": ["Show overall pipeline health", "Prepare leadership update"]
            }

        total_risk_val = risk_table.sum("deal_value_inr")
        summary = (
            f"Identified **{format_inr(total_risk_val)} in Revenue at Risk** across **{len(risk_table)} delayed work order(s)**. "
            f"These projects have signed deals or active client accounts whose future invoicing, payment milestones, "
            f"or contract renewals are threatened by execution bottlenecks."
        )

        recommendations = []
        for r in risk_table:
            recommendations.append(
                f"🚨 **Action on {r['client']} ({r['deal_value_formatted']})**: Project *{r['project_title']}* is blocked by '{r['blockers_reason']}'. Sales Lead ({r['sales_owner']}) and PM ({r['project_manager']}) must align on revised delivery commitments."
            )

        table = risk_table.select(["client", "project_title", "deal_value_formatted", "deal_stage", "project_manager", "sales_owner", "target_date", "blockers_reason"])

        return {
            "intent": "REVENUE_AT_RISK",
            "title": "⚠️ Cross-Board Revenue at Risk & Delivery Bottlenecks",
            "executive_summary": summary,
            "metrics": {
                "Total Revenue at Risk": format_inr(total_risk_val),
                "Delayed Client Accounts": len(risk_table),
                "Largest Single Account at Risk": f"{risk_table[0]['client']} ({risk_table[0]['deal_value_formatted']})"
            },
            "data_table": table,
            "caveats": [
                "Revenue at risk calculates full deal value linked to delayed work orders regardless of milestone billing structure."
            ],
            "recommendations": recommendations,
            "suggested_followups": [
                "Show details for Tata Power",
                "Show details for Mahindra Lifespaces",
                "How is our pipeline looking for energy sector this quarter?",
                "Prepare leadership update"
            ]
        }

    def _handle_sector_comparison_query(self) -> Dict[str, Any]:
        sec_table = self.engine.get_sector_breakdown()
        top_sec = sec_table[0]["Sector"] if not sec_table.empty else "N/A"
        top_rev = sec_table[0]["Closed Won (Formatted)"] if not sec_table.empty else "₹0"

        summary = (
            f"Portfolio spans **{len(sec_table)} industry verticals**. **{top_sec}** is our highest revenue driver with **{top_rev}** in Closed Won deals, "
            f"followed by **{sec_table[1]['Sector'] if len(sec_table)>1 else 'Others'}** ({sec_table[1]['Closed Won (Formatted)'] if len(sec_table)>1 else ''})."
        )

        recommendations = [
            f"🚀 **Sector Expansion**: Double down on {top_sec} where win velocity and market authority are proven.",
            "🌱 **Emerging Verticals**: Evaluate cross-selling drone inspection packages into Mining and Smart Cities where deal sizes exceed ₹50L."
        ]

        table = sec_table.select(["Sector", "Closed Won (Formatted)", "Open Pipeline (Formatted)", "Weighted Pipeline (Formatted)", "Won Deals", "Active WOs", "Delayed WOs"])

        return {
            "intent": "SECTOR_COMPARISON",
            "title": "🌐 Cross-Sector Performance Benchmark",
            "executive_summary": summary,
            "metrics": {
                "Total Sectors Tracked": len(sec_table),
                "Leading Sector": f"{top_sec} ({top_rev})",
                "Total Portfolio Value": format_inr(sec_table.sum("Closed Won Revenue (INR)") + sec_table.sum("Open Pipeline (INR)"))
            },
            "data_table": table,
            "caveats": self.hygiene["caveats"][:2],
            "recommendations": recommendations,
            "suggested_followups": [
                "How's our pipeline looking for energy sector this quarter?",
                "Show mining sector deals",
                "What is our revenue at risk?",
                "Prepare leadership update"
            ]
        }

    def _handle_client_drilldown(self, client_name: str) -> Dict[str, Any]:
        c_deals = self.deals.filter(lambda r: str(r.get("client")).lower() == client_name.lower())
        c_wos = self.wos.filter(lambda r: str(r.get("client")).lower() == client_name.lower())

        total_val = c_deals.sum("deal_value_inr")
        stages = c_deals.unique("stage") or ["No Deals"]
        wo_status = c_wos.unique("status") or ["No Work Orders"]

        summary = (
            f"**Account 360: {client_name}** | Total Deal Value: **{format_inr(total_val)}** | "
            f"Deal Stages: **{', '.join(stages)}** | Work Orders: **{len(c_wos)} ({', '.join(wo_status)})**."
        )

        recommendations = []
        if any(s == "Delayed" for s in wo_status):
            recommendations.append(f"🚨 **Account Risk**: Work orders for {client_name} are delayed. Prioritize executive check-in.")
        else:
            recommendations.append(f"✅ Account is in good standing. Explore expansion into multi-site drone survey contracts.")

        table = c_deals.select(["deal_name", "deal_value_formatted", "stage", "owner", "close_date"])

        return {
            "intent": "CLIENT_DRILLDOWN",
            "title": f"🏢 Client 360 Profile: {client_name}",
            "executive_summary": summary,
            "metrics": {
                "Total Account Value": format_inr(total_val),
                "Deals Count": len(c_deals),
                "Work Orders Count": len(c_wos)
            },
            "data_table": table,
            "caveats": [],
            "recommendations": recommendations,
            "suggested_followups": [
                "Show all revenue at risk",
                "Compare pipeline across sectors",
                "Prepare leadership update"
            ]
        }

    def _handle_data_hygiene_query(self) -> Dict[str, Any]:
        score = self.hygiene["hygiene_score"]
        summary = (
            f"Overall Monday.com Board Data Hygiene Score is **{score}%** "
            f"({self.hygiene['passed_checks']} of {self.hygiene['total_checks']} validation checks passed across {self.hygiene['total_deals_count']} deals and {self.hygiene['total_wos_count']} work orders)."
        )

        recommendations = [
            "1. Enforce required fields on Monday boards for **Expected Close Date** and **Account Owner**.",
            "2. Ensure all operational Work Orders mandate a valid **Deal Ref** relation to prevent unlinked project costs.",
            "3. Require project managers to fill mandatory **Blockers / Delays** notes whenever a status is marked Delayed."
        ]

        table = Table([{"Data Quality Issue / Caveat": c} for c in self.hygiene["caveats"]])

        return {
            "intent": "DATA_HYGIENE",
            "title": "🛡️ Monday.com Data Quality & Hygiene Audit",
            "executive_summary": summary,
            "metrics": {
                "Hygiene Score": f"{score}%",
                "Deals Audited": self.hygiene["total_deals_count"],
                "Work Orders Audited": self.hygiene["total_wos_count"],
                "Issues Flagged": len(self.hygiene["caveats"])
            },
            "data_table": table,
            "caveats": self.hygiene["caveats"],
            "recommendations": recommendations,
            "suggested_followups": [
                "How is our pipeline looking for energy sector this quarter?",
                "What is our revenue at risk?",
                "Prepare leadership update"
            ]
        }

    def _handle_leadership_update_intent(self, quarter: Optional[str]) -> Dict[str, Any]:
        from leadership_update_generator import LeadershipUpdateGenerator
        gen = LeadershipUpdateGenerator(self.deals, self.wos)
        brief = gen.generate_update(period=quarter or "Q2 2024")

        return {
            "intent": "LEADERSHIP_UPDATE",
            "title": brief["title"],
            "executive_summary": brief["executive_summary"],
            "metrics": brief["key_metrics"],
            "data_table": brief["top_wins_table"],
            "caveats": brief["data_caveats"],
            "recommendations": brief["strategic_actions"],
            "full_briefing_markdown": brief["markdown_report"],
            "suggested_followups": [
                "Show all revenue at risk",
                "How is our pipeline looking for energy sector this quarter?",
                "What is our win rate and average deal size?",
                "Audit Monday.com data quality"
            ]
        }

    def _handle_ambiguous_query(self, query: str) -> Dict[str, Any]:
        kpis = self.engine.get_summary_kpis()
        summary = (
            f"Here is a high-level snapshot across your business: Total open pipeline is **{kpis['open_pipeline_formatted']}** "
            f"(weighted: **{kpis['weighted_pipeline_formatted']}**), Closed Won revenue is **{kpis['closed_won_revenue_formatted']}** "
            f"(win rate: **{kpis['win_rate_pct']}%**), with **{kpis['total_work_orders']} work orders** ({kpis['delayed_work_orders']} delayed; **{kpis['revenue_at_risk_formatted']} at risk**)."
        )

        return {
            "intent": "AMBIGUOUS_QUERY",
            "title": "🔍 Founder Business Intelligence Snapshot",
            "executive_summary": summary,
            "metrics": {
                "Open Pipeline": kpis["open_pipeline_formatted"],
                "Closed Won": kpis["closed_won_revenue_formatted"],
                "Win Rate": f"{kpis['win_rate_pct']}%",
                "On-Time Delivery": f"{kpis['on_time_delivery_rate_pct']}%",
                "Revenue at Risk": kpis["revenue_at_risk_formatted"]
            },
            "data_table": self.engine.get_sector_breakdown().select(["Sector", "Closed Won (Formatted)", "Open Pipeline (Formatted)", "Delayed WOs"]),
            "caveats": [
                "Your question was broad. Please select one of the clarifying options below to drill into specific business drivers."
            ],
            "recommendations": [
                "💡 Select an area of interest below for immediate deep-dive analysis."
            ],
            "suggested_followups": [
                "How's our pipeline looking for energy sector this quarter?",
                "What is our revenue at risk from delayed work orders?",
                "Compare pipeline performance across all sectors",
                "Prepare a leadership update for this quarter"
            ]
        }