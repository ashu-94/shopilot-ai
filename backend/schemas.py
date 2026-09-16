from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(StrictModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class LineItem(StrictModel):
    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=100)


class CartInput(StrictModel):
    items: list[LineItem] = Field(max_length=40)


class ProcurementDetails(StrictModel):
    organization: str = Field(min_length=2, max_length=160)
    cost_center: str = Field(min_length=2, max_length=80)
    delivery_address: str = Field(min_length=12, max_length=500)
    billing_address: str = Field(min_length=12, max_length=500)
    contact_email: str = Field(min_length=5, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    requested_delivery_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    payment_terms: Literal["prepaid_mock", "net_30_mock"] = "prepaid_mock"
    reference: str = Field(default="", max_length=100)


class MissionInput(StrictModel):
    query: str = Field(min_length=8, max_length=3000)
    mode: Literal["shopping", "procurement", "support"] = "shopping"
    procurement: ProcurementDetails | None = None
    budget: int | None = Field(default=None, ge=1000, le=100000000)


class CheckoutInput(StrictModel):
    address: str = Field(min_length=12, max_length=500)
    simulate_failure: bool = False


class DecisionInput(StrictModel):
    decision: Literal["approve", "reject", "request_info"]
    feedback: str = Field(default="", max_length=1000)


class ReturnInput(StrictModel):
    items: list[LineItem] | None = Field(default=None, min_length=1, max_length=40)
    order_id: str = Field(max_length=64)
    reason: str = Field(min_length=10, max_length=1500)
    resolution: Literal["refund", "replacement"] = "refund"


class ReplayInput(StrictModel):
    reason: str = Field(min_length=10, max_length=500)
