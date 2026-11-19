"""Due-date clocks: classify each invoice as upcoming / due_soon / overdue."""
from datetime import date

PAID = "paid"
DISPUTED = "disputed"
OVERDUE = "overdue"
DUE_SOON = "due_soon"
UPCOMING = "upcoming"


def payment_status(
    due_date: date,
    as_of: date,
    outstanding: float,
    due_soon_days: int = 7,
    disputed: bool = False,
) -> str:
    if outstanding <= 0:
        return PAID
    if disputed:
        return DISPUTED
    days_left = (due_date - as_of).days
    if days_left < 0:
        return OVERDUE
    if days_left <= due_soon_days:
        return DUE_SOON
    return UPCOMING


def days_overdue(due_date: date, as_of: date) -> int:
    return max((as_of - due_date).days, 0)
