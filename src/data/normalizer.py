"""
Resilient data normalization engine for Monday.com messy real-world records.
Handles missing values, irregular date formats, currency strings, and cross-board reconciliation.
"""

import re
import logging
from datetime import datetime, date
from typing import Any, Optional
from .schema import DealRecord, WorkOrderRecord, UnifiedBusinessRecord

logger = logging.getLogger(__name__)

# Canonical sector mapping dictionary
SECTOR_MAPPING = {
    "mining": "Mining",
    "mine": "Mining",
    "powerline": "Powerline",
    "power line": "Powerline",
    "transmission": "Powerline",
    "solar": "Solar",
    "wind": "Wind",
    "renewable": "Renewables",
    "renewables": "Renewables",
    "energy": "Energy",
    "infrastructure": "Infrastructure",
    "infra": "Infrastructure",
    "highways": "Infrastructure",
    "roads": "Infrastructure",
    "railways": "Infrastructure",
    "agriculture": "Agriculture",
    "agri": "Agriculture",
    "telecom": "Telecom",
    "urban": "Urban Planning",
    "enterprise": "Enterprise",
}

STAGE_MAPPING = {
    "won": "Won",
    "closed won": "Won",
    "lost": "Lost",
    "closed lost": "Lost",
    "lead": "Lead",
    "qualified": "Qualified",
    "opportunity": "Opportunity",
    "proposal": "Proposal Sent",
    "proposal sent": "Proposal Sent",
    "negotiation": "Negotiation",
    "contract": "Contracting",
    "on hold": "On Hold",
    "in progress": "In Progress",
}


class DataNormalizer:
    """Robust data normalization and cleaning for Deals and Work Orders."""

    @staticmethod
    def parse_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        """Clean and parse numeric/financial fields from string or raw value."""
        if value is None:
            return default

        if isinstance(value, (int, float)):
            return float(value)

        val_str = str(value).strip()
        if not val_str or val_str.lower() in ("nan", "none", "null", "-", "n/a", ""):
            return default

        # Clean common prefixes like Rs., INR, $, ₹
        cleaned = re.sub(r"(?i)\b(rs|inr|usd|eur|gbp)\.?\s*", "", val_str)
        cleaned = re.sub(r"[^\d.,-]", "", cleaned)

        # Handle multiple commas/dots (e.g. 1,234,567.89 vs 1.234.567,89)
        if "," in cleaned and "." in cleaned:
            # Standard US/Indian: commas as thousands, dot as decimal
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned and "." not in cleaned:
            # Could be Indian/US thousands e.g. 1,000 or EU decimal 1,5
            parts = cleaned.split(",")
            if len(parts[-1]) == 2:  # cents/paise
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            # Fallback search for any floating pattern
            match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
            if match:
                return float(match.group(0))
            return default

    @staticmethod
    def parse_probability(value: Any) -> Optional[float]:
        """Normalize closure probability to a float between 0.0 and 1.0."""
        if value is None:
            return None

        val_str = str(value).strip().lower()
        if not val_str or val_str in ("nan", "none", "null", "-", "n/a"):
            return None

        # Text classifications
        if "high" in val_str:
            return 0.8
        if "med" in val_str:
            return 0.5
        if "low" in val_str:
            return 0.2
        if "won" in val_str:
            return 1.0
        if "lost" in val_str:
            return 0.0

        # Percentages or decimal
        num = DataNormalizer.parse_float(val_str, default=None)
        if num is not None:
            if num > 1.0:
                return min(1.0, max(0.0, num / 100.0))
            return min(1.0, max(0.0, num))

        return None

    @staticmethod
    def parse_date(value: Any) -> Optional[date]:
        """Resilient date parser for formats like YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, and month names."""
        if value is None:
            return None

        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()

        val_str = str(value).strip()
        if not val_str or val_str.lower() in ("nan", "none", "null", "-", "n/a"):
            return None

        # Try parsing JSON structure if Monday returned a json value string
        if val_str.startswith("{") and "date" in val_str:
            match = re.search(r'"date"\s*:\s*"([^"]+)"', val_str)
            if match:
                val_str = match.group(1)

        # Standard formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S",
            "%d-%b-%Y",
            "%d %b %Y",
            "%b %Y",
            "%B %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.date()
            except ValueError:
                continue

        # Try regex extraction for YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", val_str)
        if iso_match:
            try:
                y, m, d = map(int, iso_match.groups())
                return date(y, m, d)
            except ValueError:
                pass

        return None

    @staticmethod
    def normalize_sector(sector_raw: Optional[str]) -> str:
        """Map raw sector strings to standard canonical categories."""
        if not sector_raw:
            return "Other"

        clean = str(sector_raw).strip()
        lower = clean.lower()

        for key, canonical in SECTOR_MAPPING.items():
            if key in lower:
                return canonical

        # Fallback to cleaned capitalized title
        return clean.capitalize() if clean else "Other"

    @staticmethod
    def normalize_deal_stage(stage_raw: Optional[str]) -> str:
        """Map deal stage to standard naming."""
        if not stage_raw:
            return "Pipeline"

        clean = str(stage_raw).strip()
        lower = clean.lower()

        for key, canonical in STAGE_MAPPING.items():
            if key in lower:
                return canonical

        return clean.title() if clean else "Pipeline"

    @staticmethod
    def _extract_column_dict(column_values: list[dict[str, Any]]) -> dict[str, str]:
        """Convert Monday item column_values list into title/id lookup dict."""
        col_map = {}
        for cv in column_values:
            cid = cv.get("id", "")
            text = cv.get("text")
            if text is None:
                # Try parsing value
                val = cv.get("value")
                if val is not None and isinstance(val, str) and not val.startswith("{"):
                    text = val.strip('"')
            col_map[cid] = text if text is not None else ""
        return col_map

    @classmethod
    def normalize_deal(cls, item: dict[str, Any]) -> DealRecord:
        """Convert a raw Monday Deal item into a normalized DealRecord."""
        item_id = str(item.get("id", ""))
        name = str(item.get("name", "Unnamed Deal")).strip()
        col_values = item.get("column_values", [])
        
        # Build text lookup by both id and lowercased title/type
        raw_cols: dict[str, Any] = {}
        for cv in col_values:
            cid = cv.get("id", "")
            text = cv.get("text", "")
            raw_cols[cid] = text

        # Find columns by id or matching known keys
        # Known IDs from Monday schema:
        # Owner code: color_mm6qteq9
        # Client Code: dropdown_mm6q6g71
        # Deal Status: color_mm6qh76w
        # Close Date (A): date_mm6qrwpq
        # Closure Probability: color_mm6qnfyb
        # Masked Deal value: numeric_mm6qzeb0
        # Tentative Close Date: date_mm6qkepj
        # Deal Stage: color_mm6q5qf
        # Product deal: color_mm6qzx08
        # Sector/service: color_mm6qgzp3
        # Created Date: date_mm6q5hy

        owner_code = raw_cols.get("color_mm6qteq9") or raw_cols.get("owner_code")
        client_code = raw_cols.get("dropdown_mm6q6g71") or raw_cols.get("client_code")
        deal_status = raw_cols.get("color_mm6qh76w") or raw_cols.get("deal_status")
        close_date_raw = raw_cols.get("date_mm6qrwpq") or raw_cols.get("close_date")
        prob_raw = raw_cols.get("color_mm6qnfyb") or raw_cols.get("closure_probability")
        val_raw = raw_cols.get("numeric_mm6qzeb0") or raw_cols.get("masked_deal_value")
        tentative_date_raw = raw_cols.get("date_mm6qkepj") or raw_cols.get("tentative_close_date")
        stage_raw = raw_cols.get("color_mm6q5qf") or raw_cols.get("deal_stage")
        product_deal = raw_cols.get("color_mm6qzx08") or raw_cols.get("product_deal")
        sector_raw = raw_cols.get("color_mm6qgzp3") or raw_cols.get("sector") or raw_cols.get("sector/service")
        created_date_raw = raw_cols.get("date_mm6q5hy") or raw_cols.get("created_date")

        return DealRecord(
            id=item_id,
            name=name,
            owner_code=owner_code or None,
            client_code=client_code or None,
            deal_status=deal_status or None,
            close_date_actual=cls.parse_date(close_date_raw),
            closure_probability=cls.parse_probability(prob_raw),
            masked_deal_value=cls.parse_float(val_raw, default=0.0),
            tentative_close_date=cls.parse_date(tentative_date_raw),
            deal_stage=cls.normalize_deal_stage(stage_raw),
            product_deal=product_deal or None,
            sector=cls.normalize_sector(sector_raw),
            created_date=cls.parse_date(created_date_raw),
            raw_columns=raw_cols,
        )

    @classmethod
    def normalize_work_order(cls, item: dict[str, Any]) -> WorkOrderRecord:
        """Convert a raw Monday Work Order item into a normalized WorkOrderRecord."""
        item_id = str(item.get("id", ""))
        name = str(item.get("name", "Unnamed Work Order")).strip()
        col_values = item.get("column_values", [])
        
        raw_cols: dict[str, Any] = {}
        for cv in col_values:
            cid = cv.get("id", "")
            text = cv.get("text", "")
            raw_cols[cid] = text

        return WorkOrderRecord(
            id=item_id,
            name=name,
            customer_code=raw_cols.get("dropdown_mm6qj9dg") or None,
            serial_number=raw_cols.get("dropdown_mm6q112a") or None,
            nature_of_work=raw_cols.get("color_mm6qhxkp") or None,
            last_executed_month=raw_cols.get("color_mm6qaf7") or None,
            execution_status=raw_cols.get("color_mm6qw3rk") or None,
            data_delivery_date=cls.parse_date(raw_cols.get("date_mm6qhw8m")),
            po_date=cls.parse_date(raw_cols.get("date_mm6qakh4")),
            document_type=raw_cols.get("color_mm6qj269") or None,
            probable_start_date=cls.parse_date(raw_cols.get("date_mm6qmf90")),
            probable_end_date=cls.parse_date(raw_cols.get("date_mm6q3hx5")),
            bd_kam_code=raw_cols.get("color_mm6qmdaz") or None,
            sector=cls.normalize_sector(raw_cols.get("color_mm6q6ey9")),
            type_of_work=raw_cols.get("color_mm6q2mzd") or None,
            software_platform_included=raw_cols.get("color_mm6qmhp7") or None,
            last_invoice_date=cls.parse_date(raw_cols.get("date_mm6q9fy8")),
            latest_invoice_no=raw_cols.get("dropdown_mm6qhj6q") or None,
            
            # Amounts
            amount_excl_gst=cls.parse_float(raw_cols.get("numeric_mm6qk46b"), 0.0),
            amount_incl_gst=cls.parse_float(raw_cols.get("numeric_mm6q6kc4"), 0.0),
            billed_value_excl_gst=cls.parse_float(raw_cols.get("numeric_mm6q2n6c"), 0.0),
            billed_value_incl_gst=cls.parse_float(raw_cols.get("numeric_mm6qbtb8"), 0.0),
            collected_amount_incl_gst=cls.parse_float(raw_cols.get("numeric_mm6qsq8g"), 0.0),
            amount_to_be_billed_excl_gst=cls.parse_float(raw_cols.get("numeric_mm6q9j2m"), 0.0),
            amount_to_be_billed_incl_gst=cls.parse_float(raw_cols.get("numeric_mm6qpcs0"), 0.0),
            amount_receivable=cls.parse_float(raw_cols.get("numeric_mm6q44nx"), 0.0),
            
            ar_priority=raw_cols.get("color_mm6qjep0") or None,
            quantity_ops=cls.parse_float(raw_cols.get("numeric_mm6q757e"), 0.0),
            quantity_po=cls.parse_float(raw_cols.get("dropdown_mm6qf50c"), 0.0),
            quantity_billed=cls.parse_float(raw_cols.get("numeric_mm6qf854"), 0.0),
            quantity_balance=cls.parse_float(raw_cols.get("numeric_mm6qqkrd"), 0.0),
            
            invoice_status=raw_cols.get("color_mm6qwr4g") or None,
            expected_billing_month=raw_cols.get("text_mm6qyb26") or None,
            actual_billing_month=raw_cols.get("color_mm6q4ca9") or None,
            actual_collection_month=raw_cols.get("text_mm6qf7m3") or None,
            wo_status_billed=raw_cols.get("color_mm6qzxer") or None,
            collection_status=raw_cols.get("text_mm6qdazf") or None,
            collection_date=raw_cols.get("text_mm6q8b8w") or None,
            billing_status=raw_cols.get("color_mm6qwt0n") or None,
            raw_columns=raw_cols,
        )

    @classmethod
    def normalize_deals_batch(cls, raw_items: list[dict[str, Any]]) -> list[DealRecord]:
        """Normalize a batch of raw deal items."""
        return [cls.normalize_deal(item) for item in raw_items]

    @classmethod
    def normalize_work_orders_batch(cls, raw_items: list[dict[str, Any]]) -> list[WorkOrderRecord]:
        """Normalize a batch of raw work order items."""
        return [cls.normalize_work_order(item) for item in raw_items]

    @classmethod
    def reconcile_and_unify(
        cls,
        deals: list[DealRecord],
        work_orders: list[WorkOrderRecord],
    ) -> list[UnifiedBusinessRecord]:
        """
        Reconcile and join Deals with Work Orders on Deal Name and Client/Serial references.
        Provides a 360-degree founder view of pipeline-to-cash realization.
        """
        # Group work orders by normalized deal name
        wo_by_name: dict[str, list[WorkOrderRecord]] = {}
        for wo in work_orders:
            key = wo.name.strip().lower()
            wo_by_name.setdefault(key, []).append(wo)

        unified_records: list[UnifiedBusinessRecord] = []
        matched_wo_names: set[str] = set()

        # Process each deal
        for d in deals:
            key = d.name.strip().lower()
            matched_wos = wo_by_name.get(key, [])
            if matched_wos:
                matched_wo_names.add(key)

            # Aggregate work order figures
            wo_ids = [w.id for w in matched_wos]
            serial_nums = [w.serial_number for w in matched_wos if w.serial_number]
            order_val_excl = sum(w.amount_excl_gst or 0.0 for w in matched_wos)
            order_val_incl = sum(w.amount_incl_gst or 0.0 for w in matched_wos)
            billed_val_excl = sum(w.billed_value_excl_gst or 0.0 for w in matched_wos)
            billed_val_incl = sum(w.billed_value_incl_gst or 0.0 for w in matched_wos)
            collected_val = sum(w.collected_amount_incl_gst or 0.0 for w in matched_wos)
            ar_val = sum(w.amount_receivable or 0.0 for w in matched_wos)
            unbilled_val = sum(w.amount_to_be_billed_excl_gst or 0.0 for w in matched_wos)

            exec_statuses = list({w.execution_status for w in matched_wos if w.execution_status})
            billing_statuses = list({w.billing_status for w in matched_wos if w.billing_status})

            # Check AR risk (overdue / outstanding receivable)
            is_ar_risk = ar_val > 0 and any(w.ar_priority for w in matched_wos if w.ar_priority)

            prob = d.closure_probability if d.closure_probability is not None else (1.0 if d.deal_stage == "Won" else 0.5)
            val = d.masked_deal_value or 0.0
            weighted_val = val * prob

            unified = UnifiedBusinessRecord(
                deal_name=d.name,
                client_code=d.client_code,
                sector=d.sector or (matched_wos[0].sector if matched_wos else "Other"),
                deal_id=d.id,
                deal_stage=d.deal_stage,
                deal_status=d.deal_status,
                closure_probability=d.closure_probability,
                pipeline_value=val,
                weighted_pipeline_value=weighted_val,
                close_date=d.close_date_actual or d.tentative_close_date,
                has_work_orders=bool(matched_wos),
                work_order_ids=wo_ids,
                serial_numbers=serial_nums,
                total_order_value_excl_gst=order_val_excl,
                total_order_value_incl_gst=order_val_incl,
                total_billed_value_excl_gst=billed_val_excl,
                total_billed_value_incl_gst=billed_val_incl,
                total_collected_value=collected_val,
                total_amount_receivable=ar_val,
                total_unbilled_value=unbilled_val,
                execution_statuses=exec_statuses,
                billing_statuses=billing_statuses,
                is_ar_risk=is_ar_risk,
            )
            unified_records.append(unified)

        # Also add standalone work orders that were not matched to any deal
        for name_key, wos in wo_by_name.items():
            if name_key not in matched_wo_names:
                wo_ids = [w.id for w in wos]
                serial_nums = [w.serial_number for w in wos if w.serial_number]
                order_val_excl = sum(w.amount_excl_gst or 0.0 for w in wos)
                order_val_incl = sum(w.amount_incl_gst or 0.0 for w in wos)
                billed_val_excl = sum(w.billed_value_excl_gst or 0.0 for w in wos)
                billed_val_incl = sum(w.billed_value_incl_gst or 0.0 for w in wos)
                collected_val = sum(w.collected_amount_incl_gst or 0.0 for w in wos)
                ar_val = sum(w.amount_receivable or 0.0 for w in wos)
                unbilled_val = sum(w.amount_to_be_billed_excl_gst or 0.0 for w in wos)

                exec_statuses = list({w.execution_status for w in wos if w.execution_status})
                billing_statuses = list({w.billing_status for w in wos if w.billing_status})
                is_ar_risk = ar_val > 0

                unified = UnifiedBusinessRecord(
                    deal_name=wos[0].name,
                    client_code=wos[0].customer_code,
                    sector=wos[0].sector or "Other",
                    deal_id=None,
                    deal_stage="Executed",
                    deal_status="Active Execution",
                    closure_probability=1.0,
                    pipeline_value=order_val_excl,
                    weighted_pipeline_value=order_val_excl,
                    close_date=wos[0].po_date,
                    has_work_orders=True,
                    work_order_ids=wo_ids,
                    serial_numbers=serial_nums,
                    total_order_value_excl_gst=order_val_excl,
                    total_order_value_incl_gst=order_val_incl,
                    total_billed_value_excl_gst=billed_val_excl,
                    total_billed_value_incl_gst=billed_val_incl,
                    total_collected_value=collected_val,
                    total_amount_receivable=ar_val,
                    total_unbilled_value=unbilled_val,
                    execution_statuses=exec_statuses,
                    billing_statuses=billing_statuses,
                    is_ar_risk=is_ar_risk,
                )
                unified_records.append(unified)

        return unified_records
