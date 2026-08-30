"""
Data Quality and Caveats Reporting Engine.
Analyzes data health, identifies missing fields, and provides executive transparency warnings.
"""

import logging
from typing import Optional
from .schema import DealRecord, WorkOrderRecord, UnifiedBusinessRecord, DataQualityReport, DataCaveat

logger = logging.getLogger(__name__)


class DataQualityReporter:
    """Evaluates data resilience and produces audit caveats for business intelligence."""

    @classmethod
    def generate_report(
        cls,
        deals: list[DealRecord],
        work_orders: list[WorkOrderRecord],
        unified_records: Optional[list[UnifiedBusinessRecord]] = None,
    ) -> DataQualityReport:
        """Analyze dataset completeness and generate a comprehensive quality report."""
        total_deals = len(deals)
        total_wos = len(work_orders)
        caveats: list[DataCaveat] = []

        # 1. Deals with missing/zero value
        deals_missing_val = sum(1 for d in deals if not d.masked_deal_value or d.masked_deal_value == 0.0)
        pct_missing_val = (deals_missing_val / total_deals * 100) if total_deals > 0 else 0
        if deals_missing_val > 0:
            caveats.append(
                DataCaveat(
                    level="WARNING" if pct_missing_val > 30 else "INFO",
                    category="MISSING_VALUE",
                    message=f"{deals_missing_val} out of {total_deals} deals ({pct_missing_val:.1f}%) have unassigned deal values. Pipeline aggregates reflect recorded values only.",
                    impacted_records_count=deals_missing_val,
                    impacted_records_pct=round(pct_missing_val, 1),
                )
            )

        # 2. Deals missing close dates
        deals_missing_dates = sum(1 for d in deals if not d.close_date_actual and not d.tentative_close_date)
        pct_missing_dates = (deals_missing_dates / total_deals * 100) if total_deals > 0 else 0
        if deals_missing_dates > 0:
            caveats.append(
                DataCaveat(
                    level="WARNING",
                    category="MISSING_VALUE",
                    message=f"{deals_missing_dates} deals ({pct_missing_dates:.1f}%) lack both actual and tentative close dates, impacting quarterly forecasting precision.",
                    impacted_records_count=deals_missing_dates,
                    impacted_records_pct=round(pct_missing_dates, 1),
                )
            )

        # 3. Work orders with unbilled amounts
        wos_unbilled = sum(1 for w in work_orders if (w.amount_to_be_billed_excl_gst or 0.0) > 0)
        pct_unbilled = (wos_unbilled / total_wos * 100) if total_wos > 0 else 0
        if wos_unbilled > 0:
            total_unbilled_amt = sum(w.amount_to_be_billed_excl_gst or 0.0 for w in work_orders)
            caveats.append(
                DataCaveat(
                    level="INFO",
                    category="OPERATIONAL_GAP",
                    message=f"{wos_unbilled} work orders ({pct_unbilled:.1f}%) have unbilled backlog totaling {total_unbilled_amt:,.2f}.",
                    impacted_records_count=wos_unbilled,
                    impacted_records_pct=round(pct_unbilled, 1),
                )
            )

        # 4. Work orders with overdue/outstanding AR
        wos_ar = sum(1 for w in work_orders if (w.amount_receivable or 0.0) > 0)
        pct_ar = (wos_ar / total_wos * 100) if total_wos > 0 else 0
        if wos_ar > 0:
            total_ar_amt = sum(w.amount_receivable or 0.0 for w in work_orders)
            caveats.append(
                DataCaveat(
                    level="CRITICAL" if total_ar_amt > 1000000 else "WARNING",
                    category="CASH_FLOW_RISK",
                    message=f"{wos_ar} work orders ({pct_ar:.1f}%) have pending Accounts Receivable (AR) totaling {total_ar_amt:,.2f}.",
                    impacted_records_count=wos_ar,
                    impacted_records_pct=round(pct_ar, 1),
                )
            )

        # 5. Cross-board matching gaps
        deal_names_crm = {d.name.strip().lower() for d in deals}
        unmatched_wos = sum(1 for w in work_orders if w.name.strip().lower() not in deal_names_crm)
        pct_unmatched = (unmatched_wos / total_wos * 100) if total_wos > 0 else 0
        if unmatched_wos > 0:
            caveats.append(
                DataCaveat(
                    level="INFO",
                    category="RECONCILIATION_GAP",
                    message=f"{unmatched_wos} execution work orders ({pct_unmatched:.1f}%) originated without a corresponding deal in the CRM Deals board.",
                    impacted_records_count=unmatched_wos,
                    impacted_records_pct=round(pct_unmatched, 1),
                )
            )

        # Calculate weighted health score
        # Base 100, deduct penalties for missing critical fields
        score = 100.0
        score -= min(30.0, pct_missing_val * 0.3)
        score -= min(20.0, pct_missing_dates * 0.2)
        score -= min(15.0, pct_unmatched * 0.15)
        health_score = max(10.0, min(100.0, round(score, 1)))

        return DataQualityReport(
            total_deals=total_deals,
            total_work_orders=total_wos,
            deals_with_missing_value=deals_missing_val,
            deals_with_missing_dates=deals_missing_dates,
            work_orders_with_unbilled=wos_unbilled,
            work_orders_with_overdue_ar=wos_ar,
            unmatched_work_orders=unmatched_wos,
            data_health_score=health_score,
            caveats=caveats,
        )

    @classmethod
    def format_caveats_for_prompt(cls, report: DataQualityReport) -> str:
        """Format report into concise text for agent context."""
        lines = [
            f"DATA QUALITY & HEALTH: {report.data_health_score}% | Deals: {report.total_deals} | Work Orders: {report.total_work_orders}",
            "Active Caveats:",
        ]
        for c in report.caveats:
            prefix = "⚠️" if c.level == "WARNING" else ("🚨" if c.level == "CRITICAL" else "ℹ️")
            lines.append(f" - {prefix} [{c.category}] {c.message}")
        return "\n".join(lines)
