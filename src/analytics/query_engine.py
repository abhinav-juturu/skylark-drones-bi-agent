"""
Multi-dimensional Business Intelligence Query Engine for natural language answering.
Supports smart sector clustering, multi-dimensional filtering, and cross-board aggregations.
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

# Macro sector clusters mapping user terminology to CRM board categories
SECTOR_CLUSTERS: dict[str, list[str]] = {
    "energy": ["Renewables", "Powerline", "Solar", "Wind"],
    "renewable": ["Renewables", "Solar", "Wind"],
    "renewables": ["Renewables", "Solar", "Wind"],
    "solar": ["Renewables", "Solar"],
    "powerline": ["Powerline"],
    "power": ["Powerline", "Renewables"],
    "transmission": ["Powerline"],
    "mining": ["Mining"],
    "infrastructure": ["Infrastructure", "Railways", "Construction"],
    "infra": ["Infrastructure", "Railways", "Construction"],
    "railways": ["Infrastructure", "Railways"],
    "railway": ["Infrastructure", "Railways"],
    "construction": ["Construction", "Infrastructure"],
    "enterprise": ["Dsp", "Security and surveillance", "Aviation", "Manufacturing"],
    "tech": ["Dsp", "Security and surveillance"],
}


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

    @staticmethod
    def resolve_sector_targets(sector: str) -> list[str]:
        """Resolve a user-provided sector keyword to corresponding CRM sector tags."""
        sec_clean = sector.strip().lower()
        if sec_clean in SECTOR_CLUSTERS:
            return [s.lower() for s in SECTOR_CLUSTERS[sec_clean]]
        return [sec_clean]

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
        """Filter deals by multiple dimensions with smart sector clustering."""
        results = self.deals

        if sector:
            targets = self.resolve_sector_targets(sector)
            results = [d for d in results if d.sector.lower() in targets or any(t in d.sector.lower() for t in targets)]

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
        """Filter work orders by operational and financial criteria with smart sector clustering."""
        results = self.work_orders

        if sector:
            targets = self.resolve_sector_targets(sector)
            results = [w for w in results if w.sector.lower() in targets or any(t in w.sector.lower() for t in targets)]

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
        """Query performance metrics for a specific sector or all sectors, resolving macro clusters."""
        sectors = BusinessMetricsCalculator.compute_sector_kpis(self.deals, self.work_orders)
        if not sector_name:
            return [s.model_dump() for s in sectors]

        targets = self.resolve_sector_targets(sector_name)
        matched = [s.model_dump() for s in sectors if s.sector_name.lower() in targets or any(t in s.sector_name.lower() for t in targets)]
        
        if len(matched) > 1 and sector_name.strip().lower() in SECTOR_CLUSTERS:
            # Build a consolidated cluster summary object
            consolidated = {
                "sector_name": f"Consolidated {sector_name.capitalize()} Sector (Combined: {', '.join(m['sector_name'] for m in matched)})",
                "deals_count": sum(m["deals_count"] for m in matched),
                "pipeline_value": round(sum(m["pipeline_value"] for m in matched), 2),
                "weighted_pipeline_value": round(sum(m["weighted_pipeline_value"] for m in matched), 2),
                "won_deals": sum(m["won_deals"] for m in matched),
                "work_orders_count": sum(m["work_orders_count"] for m in matched),
                "total_contracted": round(sum(m["total_contracted"] for m in matched), 2),
                "total_billed": round(sum(m["total_billed"] for m in matched), 2),
                "total_collected": round(sum(m["total_collected"] for m in matched), 2),
                "total_ar_outstanding": round(sum(m["total_ar_outstanding"] for m in matched), 2),
                "sub_sectors": matched,
            }
            return [consolidated] + matched

        return matched if matched else [s.model_dump() for s in sectors if sector_name.lower() in s.sector_name.lower()]

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
