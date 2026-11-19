from datetime import date

from pydantic import BaseModel, Field


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    buyer_name: str
    buyer_email: str | None
    amount: float
    paid_amount: float
    outstanding: float
    invoice_date: date
    due_date: date
    status: str
    days_overdue: int
    interest: float
    dispute_category: str | None
    suggested_level: str
    reminders_sent: int


class ReminderRequest(BaseModel):
    level: str | None = Field(None, description="Leave empty to let PayGuard suggest the tone")
    supplier_name: str = "Raju Fabrication Works"
    use_llm: bool = True


class ReminderOut(BaseModel):
    id: int
    level: str
    subject: str
    body: str
    to: str | None


class BuyerResponseIn(BaseModel):
    message: str


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)
    paid_date: date | None = None
