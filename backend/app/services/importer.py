"""Invoice import from CSV (Excel "Save as CSV" or a Tally export mapped to these columns).

Required columns: invoice_number, buyer_name, amount, invoice_date
Optional columns: buyer_email, acceptance_date, credit_days, due_date, paid_amount
"""
import csv
import io
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Buyer, Invoice
from .interest import statutory_due_date

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y")
REQUIRED = {"invoice_number", "buyer_name", "amount", "invoice_date"}


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date '{value}'")


def parse_amount(value: str) -> float:
    return float(value.replace("₹", "").replace(",", "").strip())


def import_csv(db: Session, content: bytes) -> dict:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower() for h in (reader.fieldnames or [])}
    missing = REQUIRED - headers
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    created, updated, errors = 0, 0, []
    for line_no, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        try:
            invoice_date = parse_date(row["invoice_date"])
            acceptance = parse_date(row["acceptance_date"]) if row.get("acceptance_date") else invoice_date
            credit_days = int(row["credit_days"]) if row.get("credit_days") else None
            if row.get("due_date"):
                due = parse_date(row["due_date"])
            elif credit_days is not None:
                due = acceptance + timedelta(days=credit_days)
            else:
                due = statutory_due_date(acceptance, None)

            buyer = db.scalar(select(Buyer).where(Buyer.name == row["buyer_name"]))
            if buyer is None:
                buyer = Buyer(name=row["buyer_name"], email=row.get("buyer_email") or None)
                db.add(buyer)
                db.flush()
            elif row.get("buyer_email"):
                buyer.email = row["buyer_email"]

            inv = db.scalar(select(Invoice).where(Invoice.invoice_number == row["invoice_number"]))
            fields = dict(
                buyer_id=buyer.id,
                amount=parse_amount(row["amount"]),
                invoice_date=invoice_date,
                acceptance_date=acceptance,
                agreed_credit_days=credit_days,
                due_date=due,
                paid_amount=parse_amount(row["paid_amount"]) if row.get("paid_amount") else 0.0,
            )
            if inv is None:
                db.add(Invoice(invoice_number=row["invoice_number"], **fields))
                created += 1
            else:
                for k, v in fields.items():
                    setattr(inv, k, v)
                updated += 1
        except (ValueError, KeyError) as e:
            errors.append({"line": line_no, "error": str(e)})

    db.commit()
    return {"created": created, "updated": updated, "errors": errors}
