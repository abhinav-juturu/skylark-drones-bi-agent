"""
Pydantic data models for Monday.com business records and data quality reports.
"""

from datetime import date
from typing import Optional, Any
from pydantic import BaseModel, Field


class DealRecord(BaseModel):
    """Normalized schema for a Sales Deal item."""
    id: str
    name: str = Field(description="Deal Name")
    owner_code: Optional[str] = None
    client_code: Optional[str] = None
    deal_status: Optional[str] = None
    close_date_actual: Optional[date] = None
    closure_probability: Optional[float] = Field(default=None, description="Probability between 0.0 and 1.0")
    masked_deal_value: Optional[float] = Field(default=0.0, description="Deal value in currency units")
    tentative_close_date: Optional[date] = None
    deal_stage: Optional[str] = None
    product_deal: Optional[str] = None
    sector: Optional[str] = Field(default="Other", description="Normalized business sector")
    created_date: Optional[date] = None
    raw_columns: dict[str, Any] = Field(default_factory=dict)


class WorkOrderRecord(BaseModel):
    """Normalized schema for an Execution Work Order item."""
    id: str
    name: str = Field(description="Work Order Deal Name / Masked Name")
    customer_code: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, description="PO/Deal serial reference, e.g. SDPLDEAL-002")
    nature_of_work: Optional[str] = None
    last_executed_month: Optional[str] = None
    execution_status: Optional[str] = None
    data_delivery_date: Optional[date] = None
    po_date: Optional[date] = None
    document_type: Optional[str] = None
    probable_start_date: Optional[date] = None
    probable_end_date: Optional[date] = None
    bd_kam_code: Optional[str] = None
    sector: Optional[str] = Field(default="Other", description="Normalized business sector")
    type_of_work: Optional[str] = None
    software_platform_included: Optional[str] = None
    last_invoice_date: Optional[date] = None
    latest_invoice_no: Optional[str] = None
    
    # Financials (Masked)
    amount_excl_gst: Optional[float] = 0.0
    amount_incl_gst: Optional[float] = 0.0
    billed_value_excl_gst: Optional[float] = 0.0
    billed_value_incl_gst: Optional[float] = 0.0
    collected_amount_incl_gst: Optional[float] = 0.0
    amount_to_be_billed_excl_gst: Optional[float] = 0.0
    amount_to_be_billed_incl_gst: Optional[float] = 0.0
    amount_receivable: Optional[float] = 0.0
    
    ar_priority: Optional[str] = None
    quantity_ops: Optional[float] = 0.0
    quantity_po: Optional[float] = 0.0
    quantity_billed: Optional[float] = 0.0
    quantity_balance: Optional[float] = 0.0
    
    invoice_status: Optional[str] = None
    expected_billing_month: Optional[str] = None
    actual_billing_month: Optional[str] = None
    actual_collection_month: Optional[str] = None
    wo_status_billed: Optional[str] = None
    collection_status: Optional[str] = None
    collection_date: Optional[str] = None
    billing_status: Optional[str] = None
    
    raw_columns: dict[str, Any] = Field(default_factory=dict)


class UnifiedBusinessRecord(BaseModel):
    """Reconciled record combining Deals pipeline with Execution Work Orders."""
    deal_name: str
    client_code: Optional[str] = None
    sector: str = "Other"
    
    # Deals Pipeline Info
    deal_id: Optional[str] = None
    deal_stage: Optional[str] = None
    deal_status: Optional[str] = None
    closure_probability: Optional[float] = None
    pipeline_value: float = 0.0
    weighted_pipeline_value: float = 0.0
    close_date: Optional[date] = None
    
    # Execution & Financial Info (from Work Orders)
    has_work_orders: bool = False
    work_order_ids: list[str] = Field(default_factory=list)
    serial_numbers: list[str] = Field(default_factory=list)
    total_order_value_excl_gst: float = 0.0
    total_order_value_incl_gst: float = 0.0
    total_billed_value_excl_gst: float = 0.0
    total_billed_value_incl_gst: float = 0.0
    total_collected_value: float = 0.0
    total_amount_receivable: float = 0.0
    total_unbilled_value: float = 0.0
    execution_statuses: list[str] = Field(default_factory=list)
    billing_statuses: list[str] = Field(default_factory=list)
    is_ar_risk: bool = False


class DataCaveat(BaseModel):
    """A specific data quality caveat or warning."""
    level: str = Field(description="INFO, WARNING, or CRITICAL")
    category: str = Field(description="MISSING_VALUE, FORMAT_INCONSISTENCY, RECONCILIATION_GAP")
    message: str
    impacted_records_count: int
    impacted_records_pct: float


class DataQualityReport(BaseModel):
    """Summary report of data health and caveats."""
    total_deals: int
    total_work_orders: int
    deals_with_missing_value: int
    deals_with_missing_dates: int
    work_orders_with_unbilled: int
    work_orders_with_overdue_ar: int
    unmatched_work_orders: int
    data_health_score: float = Field(description="Percentage score 0 to 100")
    caveats: list[DataCaveat] = Field(default_factory=list)
