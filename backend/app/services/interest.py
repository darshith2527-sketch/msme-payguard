"""Delayed-payment interest under the MSMED Act, 2006 (Sections 15 & 16).

- s.15: the buyer must pay by the agreed date, and the agreed period can't
  exceed 45 days from acceptance. With no written agreement, 15 days.
- s.16: on late payment, compound interest with monthly rests at three times
  the bank rate notified by the RBI.

DISCLAIMER: simplified for a hackathon prototype. Eligibility (Udyam
registration, micro/small category, supplier vs. trader, etc.) and edge cases
must be reviewed by a Chartered Accountant before relying on these numbers.
"""
from dataclasses import asdict, dataclass
from datetime import date, timedelta

MAX_AGREED_DAYS = 45
DEFAULT_DAYS_NO_AGREEMENT = 15
DAYS_PER_MONTH = 30  # simplification for the monthly rest


def statutory_due_date(acceptance_date: date, agreed_credit_days: int | None) -> date:
    """Latest date the buyer may pay under s.15."""
    if agreed_credit_days is None:
        days = DEFAULT_DAYS_NO_AGREEMENT
    else:
        days = min(max(agreed_credit_days, 0), MAX_AGREED_DAYS)
    return acceptance_date + timedelta(days=days)


@dataclass
class InterestBreakdown:
    principal: float
    statutory_due_date: date
    as_of: date
    days_overdue: int
    bank_rate_pct: float
    annual_rate_pct: float
    full_months: int
    extra_days: int
    interest: float
    total_due: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["statutory_due_date"] = self.statutory_due_date.isoformat()
        d["as_of"] = self.as_of.isoformat()
        return d


def msmed_interest(
    principal: float,
    acceptance_date: date,
    agreed_credit_days: int | None,
    as_of: date,
    bank_rate_pct: float,
) -> InterestBreakdown:
    due = statutory_due_date(acceptance_date, agreed_credit_days)
    days_overdue = max((as_of - due).days, 0)

    annual_rate = 3 * bank_rate_pct
    monthly_rate = annual_rate / 100 / 12

    full_months, extra_days = divmod(days_overdue, DAYS_PER_MONTH)
    amount = principal * (1 + monthly_rate) ** full_months
    # Partial month: simple interest on the compounded amount.
    amount *= 1 + monthly_rate * extra_days / DAYS_PER_MONTH

    interest = round(amount - principal, 2) if days_overdue else 0.0
    return InterestBreakdown(
        principal=round(principal, 2),
        statutory_due_date=due,
        as_of=as_of,
        days_overdue=days_overdue,
        bank_rate_pct=bank_rate_pct,
        annual_rate_pct=annual_rate,
        full_months=full_months,
        extra_days=extra_days,
        interest=interest,
        total_due=round(principal + interest, 2),
    )
