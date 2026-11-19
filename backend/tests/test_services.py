from datetime import date

from app.services.disputes import classify_buyer_response
from app.services.interest import msmed_interest, statutory_due_date
from app.services.reminders import inr, suggest_level
from app.services.status import payment_status


def test_due_date_no_agreement_is_15_days():
    assert statutory_due_date(date(2026, 1, 1), None) == date(2026, 1, 16)


def test_agreed_credit_capped_at_45_days():
    assert statutory_due_date(date(2026, 1, 1), 90) == date(2026, 2, 15)


def test_no_interest_before_due_date():
    r = msmed_interest(100000, date(2026, 1, 1), 30, date(2026, 1, 20), 6.0)
    assert r.days_overdue == 0 and r.interest == 0


def test_interest_compounds_monthly_at_3x_bank_rate():
    # Bank rate 6% -> 18% p.a. -> 1.5% per month. 60 days overdue = 2 full months.
    r = msmed_interest(100000, date(2026, 1, 1), 15, date(2026, 3, 17), 6.0)
    assert r.days_overdue == 60
    assert r.annual_rate_pct == 18.0
    assert r.interest == round(100000 * 1.015**2 - 100000, 2)  # 3022.50


def test_payment_status():
    today = date(2026, 11, 19)
    assert payment_status(date(2026, 11, 1), today, 1000) == "overdue"
    assert payment_status(date(2026, 11, 22), today, 1000) == "due_soon"
    assert payment_status(date(2026, 12, 30), today, 1000) == "upcoming"
    assert payment_status(date(2026, 11, 1), today, 0) == "paid"
    assert payment_status(date(2026, 11, 1), today, 1000, disputed=True) == "disputed"


def test_dispute_detection():
    r = classify_buyer_response("Goods were damaged, 20 units rejected by QC")
    assert r.category == "quality_issue" and r.is_dispute
    r = classify_buyer_response("We will pay next week, approval pending")
    assert r.category == "needs_time" and not r.is_dispute


def test_relationship_safe_escalation():
    assert suggest_level("due_soon", 0, 0) == "friendly"
    assert suggest_level("overdue", 5, 0) == "follow_up"
    assert suggest_level("overdue", 30, 1) == "formal"
    assert suggest_level("overdue", 60, 2) == "escalation"
    assert suggest_level("disputed", 60, 2) == "clarification"


def test_indian_number_format():
    assert inr(840000) == "₹8,40,000.00"
    assert inr(999) == "₹999.00"
