"""
Multi-dimensional Business Intelligence Query Engine for natural language answering.
"""

from typing import Optional, Any
from datetime import date
from ..data.schema import DealRecord, WorkOrderRecord, UnifiedBusinessRecord, DataQualityReport
from ..data.normalizer import DataNormalizer
from ..data.quality_reporter import DataQualityReporter
from .metrics import (
    BusinessMetricsCalculator,
    PipelineHealthKPIs,
    RevenueRealizationKPIs,
    SectorKPIs,
    OperationalKPIs,
)


class BusinessQueryEngine:
    """Analytical engine providing structured queries, filtering, and cross-board aggregations."""

    def __init__(
        self,
        deals: list[DealRecord],
        work_orders: list[WorkOrderRecord],
        unified_records: Optional[list[UnifiedBusinessRecord]] = None,
        quality_report: Optional[DataQualityReport] = None,
    ):
        self.deals = deals
        self.work_orders = work_orders
        self.unified_records = unified_records or DataNormalizer.reconcile_and_unify(deals, work_orders)
        self.quality_report = quality_report or DataQualityReporter.generate_report(deals, work_orders, self.unified_records)

    # --- Filtering Utilities ---

    def filter_deals(
        self,
        sector: Optional[str] = None,
        stage: Optional[str] = None,
        owner: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[DealRecord]:
        """Filter deals by multiple dimensions."""
        results = self.deals

        if sector:
            sec_clean = sector.strip().lower()
            results = [d for d in results if d.sector.lower() == sec_clean]

        if stage:
            stage_clean = stage.strip().lower()
            results = [d for d in results if d.deal_stage and d.deal_stage.lower() == stage_clean]

        if owner:
            owner_clean = owner.strip().lower()
            results = [d for d in results if d.owner_code and d.owner_code.lower() == owner_clean]

        if min_value is not None:
            results = [d for d in results if (d.masked_deal_value or 0.0) >= min_value]

        if max_value is not None:
            results = [d for d in results if (d.masked_deal_value or 0.0) <= max_value]

        if date_from or date_to:
            filtered = []
            for d in results:
                target_date = d.close_date_actual or d.tentative_close_date or d.created_date
                if not target_date:
                    continue
                if date_from and target_date < date_from:
                    continue
                if date_to and target_date > date_to:
                    continue
                filtered.append(d)
            results = filtered

        return results

    def filter_work_orders(
        self,
        sector: Optional[str] = None,
        billing_status: Optional[str] = None,
        execution_status: Optional[str] = None,
        has_ar_only: bool = False,
        ar_priority_only: bool = False,
    ) -> list[WorkOrderRecord]:
        """Filter work orders by operational and financial criteria."""
        results = self.work_orders

        if sector:
            sec_clean = sector.strip().lower()
            results = [w for w in results if w.sector.lower() == sec_clean]

        if billing_status:
            bst_clean = billing_status.strip().lower()
            results = [w for w in results if w.billing_status and w.billing_status.lower() == bst_clean]

        if execution_status:
            est_clean = execution_status.strip().lower()
            results = [w for w in results if w.execution_status and w.execution_status.lower() == est_clean]

        if has_ar_only:
            results = [w for w in results if (w.amount_receivable or 0.0) > 0]

        if ar_priority_only:
            results = [w for w in results if bool(w.ar_priority) and (w.amount_receivable or 0.0) > 0]

        return results

    # --- High-Level Query Methods ---

    def get_executive_summary(self) -> dict[str, Any]:
        """Produce an all-encompassing executive snapshot for leadership."""
        pipe_kpi = BusinessMetricsCalculator.compute_pipeline_health(self.deals)
        rev_kpi = BusinessMetricsCalculator.compute_revenue_realization(self.work_orders)
        sectors = BusinessMetricsCalculator.compute_sector_kpis(self.deals, self.work_orders)
        ops_kpi = BusinessMetricsCalculator.compute_operational_kpis(self.work_orders)

        return {
            "pipeline": pipe_kpi.model_dump(),
            "revenue": rev_kpi.model_dump(),
            "top_sectors": [s.model_dump() for s in sectors[:5]],
            "operations": ops_kpi.model_dump(),
            "data_health_score": self.quality_report.data_health_score,
            "caveats": [c.model_dump() for c in self.quality_report.caveats],
        }

    def query_sector_performance(self, sector_name: Optional[str] = None) -> list[dict[str, Any]]:
        """Query performance metrics for a specific sector or all sectors."""
        sectors = BusinessMetricsCalculator.compute_sector_kpis(self.deals, self.work_orders)
        if sector_name:
            sec_clean = sector_name.strip().lower()
            matched = [s.model_dump() for s in sectors if s.sector_name.lower() == sec_clean]
            if matched:
                return matched
            # Try fuzzy contains
            return [s.model_dump() for s in sectors if sec_clean in s.sector_name.lower()]
        return [s.model_dump() for s in sectors]

    def query_pipeline_health(self) -> dict[str, Any]:
        """Query pipeline volume, weighted pipeline, win rate, and funnel."""
        kpi = BusinessMetricsCalculator.compute_pipeline_health(self.deals)
        top_deals = sorted(
            [d for d in self.deals if d.deal_stage not in ("Won", "Lost")],
            key=lambda x: x.masked_deal_value or 0.0,
            reverse=True,
        )[:10]

        return {
            "kpis": kpi.model_dump(),
            "top_open_deals": [
                {
                    "name": d.name,
                    "client_code": d.client_code,
                    "sector": d.sector,
                    "stage": d.deal_stage,
                    "deal_value": d.masked_deal_value,
                    "probability": d.closure_probability,
                    "close_date": str(d.close_date_actual or d.tentative_close_date or ""),
                }
                for d in top_deals
            ],
        }

    def query_cash_and_ar_risks(self) -> dict[str, Any]:
        """Query cash flow realization, billing status, and high-risk AR accounts."""
        rev_kpi = BusinessMetricsCalculator.compute_revenue_realization(self.work_orders)
        return rev_kpi.model_dump()

    def query_operational_status(self) -> dict[str, Any]:
        """Query execution turnaround, pending PO quantities, and billing requirements."""
        ops_kpi = BusinessMetricsCalculator.compute_operational_kpis(self.work_orders)
        return ops_kpi.model_dump()

    def search_items(self, query: str) -> dict[str, list[dict[str, Any]]]:
        """Search across deals, work orders, and customers."""
        q = query.strip().lower()
        matched_deals: list[dict[str, Any]] = []
        matched_wos: list[dict[str, Any]] = []

        for d in self.deals:
            text = f"{d.name} {d.client_code or ''} {d.sector} {d.owner_code or ''} {d.deal_stage}".lower()
            if q in text:
                matched_deals.append({
                    "id": d.id,
                    "name": d.name,
                    "client_code": d.client_code,
                    "sector": d.sector,
                    "stage": d.deal_stage,
                    "value": d.masked_deal_value,
                })

        for w in self.work_orders:
            text = f"{w.name} {w.customer_code or ''} {w.sector} {w.serial_number or ''} {w.execution_status or ''}".lower()
            if q in text:
                matched_wos.append({
                    "id": w.id,
                    "name": w.name,
                    "customer_code": w.customer_code,
                    "sector": w.sector,
                    "amount_excl_gst": w.amount_excl_gst,
                    "amount_receivable": w.amount_receivable,
                    "execution_status": w.execution_status,
                })

        return {
            "query": query,
            "deals_count": len(matched_deals),
            "work_orders_count": len(matched_wos),
            "deals": matched_deals[:15],
            "work_orders": matched_wos[:15],
        }
