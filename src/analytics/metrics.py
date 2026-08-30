"""
Business Intelligence Metrics Calculator for Skylark Drones.
Computes executive-level KPIs across pipeline, revenue realization, AR risks, and operations.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from ..data.schema import DealRecord, WorkOrderRecord, UnifiedBusinessRecord


class PipelineHealthKPIs(BaseModel):
    """Pipeline Health KPIs for Executive Briefings."""
    total_deals: int = 0
    active_pipeline_deals: int = 0
    total_pipeline_value: float = 0.0
    weighted_pipeline_value: float = 0.0
    won_deals_count: int = 0
    lost_deals_count: int = 0
    win_rate_pct: float = 0.0
    avg_deal_size: float = 0.0
    stage_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sector_breakdown: dict[str, float] = Field(default_factory=dict)
    owner_breakdown: dict[str, float] = Field(default_factory=dict)


class RevenueRealizationKPIs(BaseModel):
    """Revenue Realization & Accounts Receivable KPIs."""
    total_contracted_excl_gst: float = 0.0
    total_contracted_incl_gst: float = 0.0
    total_billed_excl_gst: float = 0.0
    total_billed_incl_gst: float = 0.0
    total_collected_incl_gst: float = 0.0
    total_unbilled_backlog: float = 0.0
    total_ar_outstanding: float = 0.0
    collection_rate_pct: float = 0.0
    billing_rate_pct: float = 0.0
    high_risk_ar_count: int = 0
    high_risk_ar_amount: float = 0.0
    ar_priority_accounts: list[dict[str, Any]] = Field(default_factory=list)


class SectorKPIs(BaseModel):
    """Detailed KPI breakdown for a specific industry sector."""
    sector_name: str
    deals_count: int = 0
    pipeline_value: float = 0.0
    weighted_pipeline_value: float = 0.0
    won_deals: int = 0
    work_orders_count: int = 0
    total_contracted: float = 0.0
    total_billed: float = 0.0
    total_collected: float = 0.0
    total_ar_outstanding: float = 0.0
    conversion_rate_pct: float = 0.0


class OperationalKPIs(BaseModel):
    """Operational execution and fulfillment metrics."""
    total_work_orders: int = 0
    execution_status_breakdown: dict[str, int] = Field(default_factory=dict)
    billing_status_breakdown: dict[str, int] = Field(default_factory=dict)
    total_quantity_po: float = 0.0
    total_quantity_billed: float = 0.0
    total_quantity_balance: float = 0.0
    turnaround_notes: list[str] = Field(default_factory=list)


class BusinessMetricsCalculator:
    """Computes high-level business intelligence metrics from normalized records."""

    @staticmethod
    def compute_pipeline_health(deals: list[DealRecord]) -> PipelineHealthKPIs:
        """Calculate pipeline volume, weighted pipeline, win rates, and stage funnels."""
        total_deals = len(deals)
        if total_deals == 0:
            return PipelineHealthKPIs()

        won_deals = sum(1 for d in deals if d.deal_stage == "Won")
        lost_deals = sum(1 for d in deals if d.deal_stage == "Lost")
        closed_deals = won_deals + lost_deals
        win_rate = (won_deals / closed_deals * 100) if closed_deals > 0 else 0.0

        active_deals = [d for d in deals if d.deal_stage not in ("Won", "Lost")]
        total_pipeline_val = sum(d.masked_deal_value or 0.0 for d in active_deals)
        
        # Weighted pipeline
        weighted_val = 0.0
        for d in active_deals:
            prob = d.closure_probability if d.closure_probability is not None else 0.5
            weighted_val += (d.masked_deal_value or 0.0) * prob

        deals_with_val = [d for d in deals if (d.masked_deal_value or 0.0) > 0]
        avg_deal_size = (sum(d.masked_deal_value for d in deals_with_val) / len(deals_with_val)) if deals_with_val else 0.0

        # Stage breakdown
        stage_map: dict[str, dict[str, Any]] = {}
        for d in deals:
            st = d.deal_stage or "Unspecified"
            if st not in stage_map:
                stage_map[st] = {"count": 0, "total_value": 0.0}
            stage_map[st]["count"] += 1
            stage_map[st]["total_value"] += (d.masked_deal_value or 0.0)

        # Sector breakdown
        sector_map: dict[str, float] = {}
        for d in active_deals:
            sec = d.sector or "Other"
            sector_map[sec] = sector_map.get(sec, 0.0) + (d.masked_deal_value or 0.0)

        # Owner breakdown
        owner_map: dict[str, float] = {}
        for d in active_deals:
            own = d.owner_code or "Unassigned"
            owner_map[own] = owner_map.get(own, 0.0) + (d.masked_deal_value or 0.0)

        return PipelineHealthKPIs(
            total_deals=total_deals,
            active_pipeline_deals=len(active_deals),
            total_pipeline_value=round(total_pipeline_val, 2),
            weighted_pipeline_value=round(weighted_val, 2),
            won_deals_count=won_deals,
            lost_deals_count=lost_deals,
            win_rate_pct=round(win_rate, 1),
            avg_deal_size=round(avg_deal_size, 2),
            stage_breakdown=stage_map,
            sector_breakdown={k: round(v, 2) for k, v in sector_map.items()},
            owner_breakdown={k: round(v, 2) for k, v in owner_map.items()},
        )

    @staticmethod
    def compute_revenue_realization(work_orders: list[WorkOrderRecord]) -> RevenueRealizationKPIs:
        """Calculate financial execution KPIs: contracted, billed, collected, and AR exposure."""
        total_contracted_excl = sum(w.amount_excl_gst or 0.0 for w in work_orders)
        total_contracted_incl = sum(w.amount_incl_gst or 0.0 for w in work_orders)
        total_billed_excl = sum(w.billed_value_excl_gst or 0.0 for w in work_orders)
        total_billed_incl = sum(w.billed_value_incl_gst or 0.0 for w in work_orders)
        total_collected = sum(w.collected_amount_incl_gst or 0.0 for w in work_orders)
        total_unbilled = sum(w.amount_to_be_billed_excl_gst or 0.0 for w in work_orders)
        total_ar = sum(w.amount_receivable or 0.0 for w in work_orders)

        billing_rate = (total_billed_excl / total_contracted_excl * 100) if total_contracted_excl > 0 else 0.0
        collection_rate = (total_collected / total_billed_incl * 100) if total_billed_incl > 0 else 0.0

        # High priority AR accounts
        high_risk_wos = [w for w in work_orders if (w.amount_receivable or 0.0) > 0 and w.ar_priority]
        high_risk_count = len(high_risk_wos)
        high_risk_amount = sum(w.amount_receivable or 0.0 for w in high_risk_wos)

        # Top AR priority accounts summary
        ar_accounts: list[dict[str, Any]] = []
        # Sort work orders with AR descending
        ar_wos = sorted(
            [w for w in work_orders if (w.amount_receivable or 0.0) > 0],
            key=lambda x: x.amount_receivable or 0.0,
            reverse=True,
        )
        for w in ar_wos[:10]:
            ar_accounts.append({
                "deal_name": w.name,
                "customer_code": w.customer_code or "Unknown",
                "sector": w.sector or "Other",
                "amount_receivable": round(w.amount_receivable or 0.0, 2),
                "billed_amount": round(w.billed_value_incl_gst or 0.0, 2),
                "collected_amount": round(w.collected_amount_incl_gst or 0.0, 2),
                "is_priority": bool(w.ar_priority),
                "billing_status": w.billing_status or "Pending",
            })

        return RevenueRealizationKPIs(
            total_contracted_excl_gst=round(total_contracted_excl, 2),
            total_contracted_incl_gst=round(total_contracted_incl, 2),
            total_billed_excl_gst=round(total_billed_excl, 2),
            total_billed_incl_gst=round(total_billed_incl, 2),
            total_collected_incl_gst=round(total_collected, 2),
            total_unbilled_backlog=round(total_unbilled, 2),
            total_ar_outstanding=round(total_ar, 2),
            collection_rate_pct=round(collection_rate, 1),
            billing_rate_pct=round(billing_rate, 1),
            high_risk_ar_count=high_risk_count,
            high_risk_ar_amount=round(high_risk_amount, 2),
            ar_priority_accounts=ar_accounts,
        )

    @staticmethod
    def compute_sector_kpis(
        deals: list[DealRecord],
        work_orders: list[WorkOrderRecord],
    ) -> list[SectorKPIs]:
        """Compute performance scorecard grouped by industry sector."""
        sectors: set[str] = {d.sector for d in deals if d.sector} | {w.sector for w in work_orders if w.sector}
        results: list[SectorKPIs] = []

        for sec in sorted(sectors):
            sec_deals = [d for d in deals if d.sector == sec]
            sec_wos = [w for w in work_orders if w.sector == sec]

            deals_count = len(sec_deals)
            pipe_val = sum(d.masked_deal_value or 0.0 for d in sec_deals if d.deal_stage not in ("Won", "Lost"))
            weighted_pipe = sum(
                (d.masked_deal_value or 0.0) * (d.closure_probability if d.closure_probability is not None else 0.5)
                for d in sec_deals if d.deal_stage not in ("Won", "Lost")
            )
            won_count = sum(1 for d in sec_deals if d.deal_stage == "Won")
            closed_count = won_count + sum(1 for d in sec_deals if d.deal_stage == "Lost")
            conv_rate = (won_count / closed_count * 100) if closed_count > 0 else 0.0

            contracted = sum(w.amount_excl_gst or 0.0 for w in sec_wos)
            billed = sum(w.billed_value_excl_gst or 0.0 for w in sec_wos)
            collected = sum(w.collected_amount_incl_gst or 0.0 for w in sec_wos)
            ar = sum(w.amount_receivable or 0.0 for w in sec_wos)

            results.append(
                SectorKPIs(
                    sector_name=sec,
                    deals_count=deals_count,
                    pipeline_value=round(pipe_val, 2),
                    weighted_pipeline_value=round(weighted_pipe, 2),
                    won_deals=won_count,
                    work_orders_count=len(sec_wos),
                    total_contracted=round(contracted, 2),
                    total_billed=round(billed, 2),
                    total_collected=round(collected, 2),
                    total_ar_outstanding=round(ar, 2),
                    conversion_rate_pct=round(conv_rate, 1),
                )
            )

        # Sort by total contracted descending
        results.sort(key=lambda x: (x.total_contracted, x.pipeline_value), reverse=True)
        return results

    @staticmethod
    def compute_operational_kpis(work_orders: list[WorkOrderRecord]) -> OperationalKPIs:
        """Compute operational execution and billing progression metrics."""
        exec_map: dict[str, int] = {}
        bill_map: dict[str, int] = {}

        qty_po = sum(w.quantity_po or 0.0 for w in work_orders)
        qty_billed = sum(w.quantity_billed or 0.0 for w in work_orders)
        qty_balance = sum(w.quantity_balance or 0.0 for w in work_orders)

        for w in work_orders:
            st = w.execution_status or "Unspecified"
            exec_map[st] = exec_map.get(st, 0) + 1

            bst = w.billing_status or "Unspecified"
            bill_map[bst] = bill_map.get(bst, 0) + 1

        notes: list[str] = []
        if bill_map.get("Update Required", 0) > 0:
            notes.append(f"{bill_map['Update Required']} work orders require billing status updates from ops/finance.")
        if qty_balance > 0:
            notes.append(f"Unfulfilled quantity balance across active POs stands at {qty_balance:,.0f} units.")

        return OperationalKPIs(
            total_work_orders=len(work_orders),
            execution_status_breakdown=exec_map,
            billing_status_breakdown=bill_map,
            total_quantity_po=round(qty_po, 1),
            total_quantity_billed=round(qty_billed, 1),
            total_quantity_balance=round(qty_balance, 1),
            turnaround_notes=notes,
        )
