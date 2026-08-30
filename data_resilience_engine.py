import re
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
from tabular_data import Table

logger = logging.getLogger(__name__)

USD_TO_INR = 83.0

SECTOR_TAXONOMY = {
    "Energy & Utilities": [
        "energy", "solar", "renewable", "renewables", "power", "utility", "utilities",
        "thermal", "wind", "turbine", "oil", "gas", "pipeline", "transmission", "bhadla", "khavda"
    ],
    "Infrastructure": [
        "infra", "infrastructure", "construction", "highway", "road", "railway", "freight",
        "corridor", "bridge", "smart city", "smart cities", "cadastral", "township", "real estate", "jetty"
    ],
    "Mining & Metals": [
        "mining", "metal", "metals", "quarry", "iron ore", "coal", "limestone", "pit", "stockpile",
        "steel", "cement", "materials"
    ],
    "Agriculture": [
        "agri", "agriculture", "crop", "farm", "farming", "yield", "multispectral", "harvest"
    ],
    "Defence & Security": [
        "defence", "defense", "security", "border", "perimeter", "surveillance", "tactical"
    ],
    "Forestry & Environment": [
        "forest", "forestry", "environment", "mangrove", "conservation", "wildlife", "canopy"
    ]
}

STAGE_PROBABILITIES = {
    "Closed Won": 1.0,
    "In Negotiation": 0.75,
    "Proposal Sent": 0.50,
    "Under Review": 0.50,
    "Discovery": 0.25,
    "Closed Lost": 0.0
}

class DataResilienceEngine:
    @staticmethod
    def parse_flexible_date(val: Any) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        if val is None:
            return None, None, None
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ["nan", "none", "null", "-", "tbd"]:
            return None, None, None

        q_match = re.match(r"(?i)Q([1-4])[\s\-_]*(\d{4})", val_str)
        if q_match:
            q_num = int(q_match.group(1))
            year = int(q_match.group(2))
            month = (q_num - 1) * 3 + 1
            iso_date = f"{year:04d}-{month:02d}-01"
            return iso_date, f"Q{q_num} {year}", year

        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%Y", "%B %Y", "%b %Y", "%d %b %Y", "%d %B %Y"
        ]

        dm_match = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", val_str)
        if dm_match:
            d, m, y = int(dm_match.group(1)), int(dm_match.group(2)), int(dm_match.group(3))
            try:
                if d > 12 and m <= 12:
                    dt = datetime.date(y, m, d)
                elif m > 12 and d <= 12:
                    dt = datetime.date(y, d, m)
                else:
                    dt = datetime.date(y, m, d)
                q = (dt.month - 1) // 3 + 1
                return dt.strftime("%Y-%m-%d"), f"Q{q} {dt.year}", dt.year
            except ValueError:
                pass

        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(val_str, fmt).date()
                q = (dt.month - 1) // 3 + 1
                return dt.strftime("%Y-%m-%d"), f"Q{q} {dt.year}", dt.year
            except ValueError:
                continue

        return None, None, None

    @staticmethod
    def parse_currency_amount(val: Any) -> Tuple[float, str]:
        if val is None:
            return 0.0, "₹0"
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ["nan", "none", "null", "-", "tbd", "0"]:
            return 0.0, "₹0"

        is_usd = "$" in val_str or "usd" in val_str.lower()
        cleaned = re.sub(r"[₹$,\s]", "", val_str)
        multiplier = 1.0

        if re.search(r"(?i)cr(ore)?s?", cleaned):
            multiplier = 10000000.0
            cleaned = re.sub(r"(?i)cr(ore)?s?", "", cleaned)
        elif re.search(r"(?i)lakh?s?|lac", cleaned):
            multiplier = 100000.0
            cleaned = re.sub(r"(?i)lakh?s?|lac", "", cleaned)
        elif re.search(r"(?i)m(illion)?", cleaned):
            multiplier = 1000000.0
            cleaned = re.sub(r"(?i)m(illion)?", "", cleaned)
        elif re.search(r"(?i)k", cleaned):
            multiplier = 1000.0
            cleaned = re.sub(r"(?i)k", "", cleaned)

        try:
            num = float(cleaned) * multiplier
            if is_usd:
                inr_value = num * USD_TO_INR
                display_str = f"${num:,.0f} (₹{inr_value/100000:,.1f}L)"
                return inr_value, display_str
            else:
                if num >= 10000000:
                    display_str = f"₹{num/10000000:.2f} Cr"
                elif num >= 100000:
                    display_str = f"₹{num/100000:.1f} Lakhs"
                else:
                    display_str = f"₹{num:,.0f}"
                return num, display_str
        except Exception:
            return 0.0, "₹0"

    @staticmethod
    def parse_probability(val: Any, stage: Optional[str] = None) -> float:
        if val is not None:
            val_str = str(val).strip().replace("%", "")
            try:
                p = float(val_str)
                if p > 1.0:
                    return min(p / 100.0, 1.0)
                return max(0.0, min(p, 1.0))
            except ValueError:
                pass
        if stage and stage in STAGE_PROBABILITIES:
            return STAGE_PROBABILITIES[stage]
        return 0.5

    @classmethod
    def canonicalize_sector(cls, sector_raw: Any) -> str:
        if sector_raw is None:
            return "Other / Uncategorized"
        s = str(sector_raw).lower().strip()
        if not s or s in ["nan", "none", "null", "-", "n/a"]:
            return "Other / Uncategorized"

        scores = {}
        for canonical, keywords in SECTOR_TAXONOMY.items():
            score = 0
            for kw in keywords:
                if kw in s:
                    score += 1
            if score > 0:
                scores[canonical] = score

        if scores:
            return max(scores, key=scores.get)
        return "Other / Uncategorized"

    @staticmethod
    def canonicalize_stage(stage_raw: Any) -> str:
        if stage_raw is None:
            return "Discovery"
        s = str(stage_raw).lower().strip()
        if any(w in s for w in ["won", "closed won", "closed-won", "signed", "deal won"]):
            return "Closed Won"
        if any(w in s for w in ["lost", "closed lost", "closed-lost", "dropped"]):
            return "Closed Lost"
        if any(w in s for w in ["negotiat", "contract", "legal", "closing"]):
            return "In Negotiation"
        if any(w in s for w in ["proposal", "quote", "pitched", "rfp"]):
            return "Proposal Sent"
        if any(w in s for w in ["review", "tender", "audit", "eval"]):
            return "Under Review"
        if any(w in s for w in ["discovery", "lead", "qualif", "initial"]):
            return "Discovery"
        return "Discovery"

    @staticmethod
    def canonicalize_work_order_status(status_raw: Any) -> str:
        if status_raw is None:
            return "Planning"
        s = str(status_raw).lower().strip()
        if any(w in s for w in ["completed", "delivered", "done", "finished", "signoff"]):
            return "Completed"
        if any(w in s for w in ["delay", "blocked", "behind", "stalled", "hold", "pause", "struck", "pending from client"]):
            return "Delayed"
        if any(w in s for w in ["progress", "ongoing", "processing", "flight", "active", "executed"]):
            return "In Progress"
        if any(w in s for w in ["plan", "scheduled", "upcoming"]):
            return "Planning"
        return "In Progress"

    @classmethod
    def clean_deals(cls, raw_input: Any) -> Table:
        records = raw_input.to_records() if isinstance(raw_input, Table) else list(raw_input)
        if not records:
            return Table([])

        cols = list(records[0].keys())

        def get_col(candidates):
            for c in candidates:
                for col in cols:
                    if c.lower() in col.lower():
                        return col
            return None

        c_id = get_col(["deal id", "id", "deal_id", "code"]) or "_item_id"
        c_name = get_col(["deal name", "name", "title", "deal"]) or "_item_name"
        c_client = get_col(["client", "account", "customer", "company"])
        c_sector = get_col(["sector", "industry", "vertical"])
        c_val = get_col(["value", "amount", "deal value", "revenue", "price", "size"])
        c_stage = get_col(["stage", "status", "phase"])
        c_close = get_col(["close date", "expected close", "date", "closing"])
        c_owner = get_col(["owner", "rep", "salesperson", "assignee", "lead"])
        c_prob = get_col(["probability", "prob", "confidence"])
        c_quarter = get_col(["quarter", "delivery quarter", "timeline", "period"])
        c_notes = get_col(["notes", "description", "details", "comments"])

        cleaned_records = []
        for idx, row in enumerate(records):
            raw_val = row.get(c_val) if c_val else 0
            val_inr, val_disp = cls.parse_currency_amount(raw_val)

            raw_stage = row.get(c_stage) if c_stage else "Discovery"
            clean_stage = cls.canonicalize_stage(raw_stage)

            raw_prob = row.get(c_prob) if c_prob else None
            clean_prob = cls.parse_probability(raw_prob, clean_stage)

            raw_date = row.get(c_close) if c_close else None
            iso_date, quarter, year = cls.parse_flexible_date(raw_date)

            if not quarter and c_quarter and row.get(c_quarter):
                _, quarter, year = cls.parse_flexible_date(row.get(c_quarter))

            raw_sector = row.get(c_sector) if c_sector else None
            if (not raw_sector or str(raw_sector).strip() in ["", "nan", "None"]) and c_name:
                raw_sector = f"{row.get(c_name, '')} {row.get(c_notes, '') if c_notes else ''}"
            clean_sector = cls.canonicalize_sector(raw_sector)

            deal_id = str(row.get(c_id, f"D-{idx+1}")).strip()
            client_name = str(row.get(c_client, row.get(c_name, "Unknown Client"))).strip()
            deal_name = str(row.get(c_name, f"Deal {deal_id}")).strip()
            owner = str(row.get(c_owner, "Unassigned")).strip()
            if owner.lower() in ["", "nan", "none", "null"]:
                owner = "Unassigned"

            weighted_inr = val_inr * clean_prob

            cleaned_records.append({
                "deal_id": deal_id,
                "deal_name": deal_name,
                "client": client_name,
                "sector": clean_sector,
                "deal_value_inr": val_inr,
                "deal_value_formatted": val_disp,
                "stage": clean_stage,
                "probability": clean_prob,
                "weighted_value_inr": weighted_inr,
                "close_date": iso_date,
                "quarter": quarter or "Unscheduled",
                "year": year or 2024,
                "owner": owner,
                "notes": str(row.get(c_notes, "")) if c_notes else ""
            })

        return Table(cleaned_records)

    @classmethod
    def clean_work_orders(cls, raw_input: Any) -> Table:
        records = raw_input.to_records() if isinstance(raw_input, Table) else list(raw_input)
        if not records:
            return Table([])

        cols = list(records[0].keys())

        def get_col(candidates):
            for c in candidates:
                for col in cols:
                    if c.lower() in col.lower():
                        return col
            return None

        c_wo_id = get_col(["work order id", "wo id", "wo_id", "order id", "id"]) or "_item_id"
        c_deal_ref = get_col(["deal ref", "deal id", "deal_id", "linked deal", "deal"])
        c_title = get_col(["project title", "title", "project", "name", "order"]) or "_item_name"
        c_client = get_col(["client name", "client", "account", "customer"])
        c_sector = get_col(["sector", "industry", "vertical"])
        c_status = get_col(["status", "progress", "state", "delivery status"])
        c_start = get_col(["start date", "start", "commenced"])
        c_target = get_col(["target delivery date", "target date", "deadline", "target", "due date"])
        c_actual = get_col(["actual delivery date", "actual date", "completed date", "delivery date"])
        c_pm = get_col(["project manager", "pm", "lead", "owner", "engineer"])
        c_feedback = get_col(["feedback score", "feedback", "rating", "score", "csat"])
        c_blockers = get_col(["blockers", "delays", "issues", "notes", "risk"])

        cleaned_records = []
        for idx, row in enumerate(records):
            wo_id = str(row.get(c_wo_id, f"WO-{idx+1}")).strip()
            deal_ref = str(row.get(c_deal_ref, "")).strip() if c_deal_ref else ""
            if deal_ref.lower() in ["nan", "none", "null", "unlinked", "-"]:
                deal_ref = ""

            title = str(row.get(c_title, f"Work Order {wo_id}")).strip()
            client = str(row.get(c_client, "Unknown Client")).strip()

            raw_sector = row.get(c_sector) if c_sector else None
            if (not raw_sector or str(raw_sector).strip() in ["", "nan", "None"]) and title:
                raw_sector = title
            clean_sector = cls.canonicalize_sector(raw_sector)

            raw_status = row.get(c_status) if c_status else "In Progress"
            clean_status = cls.canonicalize_work_order_status(raw_status)

            start_iso, start_q, _ = cls.parse_flexible_date(row.get(c_start) if c_start else None)
            target_iso, target_q, _ = cls.parse_flexible_date(row.get(c_target) if c_target else None)
            actual_iso, actual_q, _ = cls.parse_flexible_date(row.get(c_actual) if c_actual else None)

            pm = str(row.get(c_pm, "Unassigned")).strip()
            if pm.lower() in ["", "nan", "none", "null"]:
                pm = "Unassigned"

            feedback = None
            if c_feedback and row.get(c_feedback):
                try:
                    feedback = float(str(row.get(c_feedback)).strip())
                except ValueError:
                    feedback = None

            blockers = str(row.get(c_blockers, "")).strip() if c_blockers else ""
            if blockers.lower() in ["none", "none.", "nan", "null"]:
                blockers = ""

            is_delayed = clean_status == "Delayed"
            if target_iso and actual_iso:
                if actual_iso > target_iso:
                    is_delayed = True

            cleaned_records.append({
                "wo_id": wo_id,
                "deal_ref": deal_ref,
                "project_title": title,
                "client": client,
                "sector": clean_sector,
                "status": clean_status,
                "is_delayed": is_delayed,
                "start_date": start_iso,
                "target_delivery_date": target_iso,
                "actual_delivery_date": actual_iso,
                "delivery_quarter": target_q or "Unscheduled",
                "project_manager": pm,
                "feedback_score": feedback,
                "blockers": blockers
            })

        return Table(cleaned_records)

    @classmethod
    def audit_data_hygiene(cls, deals: Table, wos: Table) -> Dict[str, Any]:
        caveats = []
        total_checks = 0
        passed_checks = 0

        if not deals.empty:
            zero_val_deals = deals.filter(lambda r: r.get("deal_value_inr", 0) <= 0)
            total_checks += len(deals)
            passed_checks += (len(deals) - len(zero_val_deals))
            if len(zero_val_deals) > 0:
                caveats.append(f"{len(zero_val_deals)} deal(s) have missing or zero valuation and are excluded from revenue totals.")

            missing_dates = deals.filter(lambda r: not r.get("close_date"))
            total_checks += len(deals)
            passed_checks += (len(deals) - len(missing_dates))
            if len(missing_dates) > 0:
                caveats.append(f"{len(missing_dates)} deal(s) have unrecorded close dates and defaulted to quarterly estimation.")

            unassigned_reps = deals.filter(lambda r: r.get("owner") == "Unassigned")
            total_checks += len(deals)
            passed_checks += (len(deals) - len(unassigned_reps))
            if len(unassigned_reps) > 0:
                caveats.append(f"{len(unassigned_reps)} deal(s) lack an assigned sales account owner.")

        if not wos.empty:
            orphan_wos = wos.filter(lambda r: not r.get("deal_ref"))
            total_checks += len(wos)
            passed_checks += (len(wos) - len(orphan_wos))
            if len(orphan_wos) > 0:
                caveats.append(f"{len(orphan_wos)} operational work order(s) are unlinked to any CRM deal record.")

            delayed_wos = wos.filter(lambda r: r.get("status") == "Delayed")
            delayed_no_reason = delayed_wos.filter(lambda r: not r.get("blockers"))
            total_checks += max(len(delayed_wos), 1)
            passed_checks += (max(len(delayed_wos), 1) - len(delayed_no_reason))
            if len(delayed_no_reason) > 0:
                caveats.append(f"{len(delayed_no_reason)} delayed work order(s) do not have recorded root cause / blocker notes.")

            unassigned_pms = wos.filter(lambda r: r.get("project_manager") == "Unassigned")
            total_checks += len(wos)
            passed_checks += (len(wos) - len(unassigned_pms))
            if len(unassigned_pms) > 0:
                caveats.append(f"{len(unassigned_pms)} work order(s) have unassigned Project Managers.")

        hygiene_score = round((passed_checks / max(total_checks, 1)) * 100, 1)

        return {
            "hygiene_score": hygiene_score,
            "total_deals_count": len(deals),
            "total_wos_count": len(wos),
            "caveats": caveats,
            "passed_checks": passed_checks,
            "total_checks": total_checks
        }