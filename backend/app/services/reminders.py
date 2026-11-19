"""Relationship-safe escalation: pick the right tone and draft the letter.

Facts and figures always come from templates (the rules engine). An LLM, if
configured, may only polish the wording; it never changes amounts or dates.
PayGuard drafts; the supplier reviews and decides whether to send.
"""
from dataclasses import dataclass
from datetime import date

import httpx

from .. import config

LEVELS = ["friendly", "follow_up", "formal", "escalation", "clarification"]


def suggest_level(status: str, days_overdue: int, reminders_sent: int) -> str:
    if status == "disputed":
        return "clarification"
    if status in ("upcoming", "due_soon"):
        return "friendly"
    if days_overdue <= 15:
        return "follow_up"
    if days_overdue > 45 and reminders_sent >= 2:
        return "escalation"
    return "formal"


@dataclass
class LetterContext:
    supplier_name: str
    buyer_name: str
    invoice_number: str
    invoice_date: date
    due_date: date
    outstanding: float
    days_overdue: int
    interest: float
    dispute_category: str | None = None


def inr(amount: float) -> str:
    """Format a number the Indian way: 840000 -> ₹8,40,000.00"""
    whole, frac = f"{amount:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"₹{whole}.{frac}"


def draft_letter(level: str, c: LetterContext) -> tuple[str, str]:
    d = lambda x: x.strftime("%d %b %Y")  # noqa: E731
    ref = f"Invoice {c.invoice_number} dated {d(c.invoice_date)}"

    if level == "friendly":
        subject = f"Payment reminder – {ref}"
        body = (
            f"Dear {c.buyer_name} team,\n\n"
            f"This is a friendly reminder that payment of {inr(c.outstanding)} against {ref} "
            f"is due on {d(c.due_date)}.\n\n"
            "Please let us know if you need any document from our side to process it.\n\n"
            f"Thank you for your continued business.\n\nRegards,\n{c.supplier_name}"
        )
    elif level == "follow_up":
        subject = f"Follow-up: payment pending – {ref}"
        body = (
            f"Dear {c.buyer_name} team,\n\n"
            f"Our records show that {inr(c.outstanding)} against {ref}, due on {d(c.due_date)}, "
            f"is still pending ({c.days_overdue} days past due).\n\n"
            "Could you please share the expected payment date? If there is any issue with the "
            "invoice, let us know and we will resolve it quickly.\n\n"
            f"Regards,\n{c.supplier_name}"
        )
    elif level == "formal":
        subject = f"Outstanding payment – {ref}"
        body = (
            f"Dear {c.buyer_name} team,\n\n"
            f"Despite earlier reminders, payment of {inr(c.outstanding)} against {ref} remains "
            f"outstanding. The payment was due on {d(c.due_date)} and is now {c.days_overdue} "
            "days overdue.\n\n"
            "We request you to clear the amount within 7 days or confirm a payment date in "
            "writing.\n\n"
            "Please note that under Sections 15 and 16 of the MSMED Act, 2006, delayed payments "
            "to registered micro and small enterprises attract compound interest at three times "
            "the RBI bank rate.\n\n"
            f"Regards,\n{c.supplier_name}"
        )
    elif level == "escalation":
        subject = f"Notice of delayed payment under the MSMED Act, 2006 – {ref}"
        body = (
            f"Dear {c.buyer_name} team,\n\n"
            f"Payment of {inr(c.outstanding)} against {ref}, due on {d(c.due_date)}, remains "
            f"unpaid after {c.days_overdue} days despite repeated reminders.\n\n"
            "Under Section 16 of the MSMED Act, 2006, interest accrues on this amount at three "
            "times the RBI bank rate, compounded monthly. As of today, the interest is "
            f"{inr(c.interest)}, making the total due {inr(c.outstanding + c.interest)}.\n\n"
            "If the amount is not settled within 15 days, we may approach the Micro and Small "
            "Enterprises Facilitation Council through the MSME Samadhaan portal.\n\n"
            "We value our business relationship and would prefer to resolve this directly.\n\n"
            f"Regards,\n{c.supplier_name}"
        )
    elif level == "clarification":
        issue = (c.dispute_category or "an issue").replace("_", " ")
        subject = f"Resolving {issue} – {ref}"
        body = (
            f"Dear {c.buyer_name} team,\n\n"
            f"Thank you for letting us know about {issue} on {ref} ({inr(c.outstanding)}).\n\n"
            "We have attached the relevant documents. Please review them and confirm what else "
            "is needed so the payment can be processed.\n\n"
            f"Regards,\n{c.supplier_name}"
        )
    else:
        raise ValueError(f"Unknown level: {level}. Use one of {LEVELS}")
    return subject, body


def polish_with_llm(body: str) -> str:
    """Optionally improve tone with an LLM. Falls back to the template on any error."""
    if not config.LLM_API_KEY:
        return body
    try:
        resp = httpx.post(
            f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json={
                "model": config.LLM_MODEL,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": (
                        "You polish business letters from Indian small manufacturers. Keep the "
                        "tone professional and relationship-safe. Do NOT change any amount, date, "
                        "invoice number, name or legal reference. Return only the letter body."
                    )},
                    {"role": "user", "content": body},
                ],
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return body
