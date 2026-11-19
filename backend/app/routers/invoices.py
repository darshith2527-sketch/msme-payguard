from collections import defaultdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import config
from ..db import get_db
from ..models import Invoice, Reminder
from ..schemas import BuyerResponseIn, InvoiceOut, PaymentIn, ReminderOut, ReminderRequest
from ..services import disputes, importer, reminders, status
from ..services.interest import msmed_interest

router = APIRouter(prefix="/api")

SAMPLE_CSV = Path(__file__).resolve().parents[3] / "sample_data" / "invoices.csv"


def _today(as_of: date | None) -> date:
    return as_of or date.today()


def _interest(inv: Invoice, as_of: date):
    return msmed_interest(inv.outstanding, inv.acceptance_date, inv.agreed_credit_days,
                          as_of, config.RBI_BANK_RATE)


def _to_out(inv: Invoice, as_of: date) -> InvoiceOut:
    st = status.payment_status(inv.due_date, as_of, inv.outstanding, config.DUE_SOON_DAYS,
                               disputed=inv.dispute_category is not None)
    overdue = status.days_overdue(inv.due_date, as_of) if st != status.PAID else 0
    return InvoiceOut(
        id=inv.id,
        invoice_number=inv.invoice_number,
        buyer_name=inv.buyer.name,
        buyer_email=inv.buyer.email,
        amount=inv.amount,
        paid_amount=inv.paid_amount,
        outstanding=inv.outstanding,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        status=st,
        days_overdue=overdue,
        interest=_interest(inv, as_of).interest if st != status.PAID else 0.0,
        dispute_category=inv.dispute_category,
        suggested_level=reminders.suggest_level(st, overdue, len(inv.reminders)),
        reminders_sent=len(inv.reminders),
    )


def _get(db: Session, invoice_id: int) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Invoice not found")
    return inv


def _all(db: Session) -> list[Invoice]:
    q = select(Invoice).options(selectinload(Invoice.buyer), selectinload(Invoice.reminders))
    return list(db.scalars(q.order_by(Invoice.due_date)))


@router.post("/invoices/import")
async def import_invoices(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        return importer.import_csv(db, await file.read())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Load Raju's demo invoices from sample_data/invoices.csv."""
    return importer.import_csv(db, SAMPLE_CSV.read_bytes())


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(as_of: date | None = None, db: Session = Depends(get_db)):
    today = _today(as_of)
    return [_to_out(inv, today) for inv in _all(db)]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, as_of: date | None = None, db: Session = Depends(get_db)):
    return _to_out(_get(db, invoice_id), _today(as_of))


@router.get("/invoices/{invoice_id}/interest")
def get_interest(invoice_id: int, as_of: date | None = None, db: Session = Depends(get_db)):
    inv = _get(db, invoice_id)
    result = _interest(inv, _today(as_of)).to_dict()
    result["disclaimer"] = ("Indicative MSMED Act s.16 calculation. Eligibility and figures "
                            "must be verified by a Chartered Accountant.")
    return result


@router.post("/invoices/{invoice_id}/reminders", response_model=ReminderOut)
def draft_reminder(invoice_id: int, req: ReminderRequest, as_of: date | None = None,
                   db: Session = Depends(get_db)):
    inv = _get(db, invoice_id)
    out = _to_out(inv, _today(as_of))
    level = req.level or out.suggested_level
    if level not in reminders.LEVELS:
        raise HTTPException(400, f"level must be one of {reminders.LEVELS}")

    ctx = reminders.LetterContext(
        supplier_name=req.supplier_name, buyer_name=inv.buyer.name,
        invoice_number=inv.invoice_number, invoice_date=inv.invoice_date,
        due_date=inv.due_date, outstanding=inv.outstanding, days_overdue=out.days_overdue,
        interest=out.interest, dispute_category=inv.dispute_category,
    )
    subject, body = reminders.draft_letter(level, ctx)
    if req.use_llm:
        body = reminders.polish_with_llm(body)

    rem = Reminder(invoice_id=inv.id, level=level, subject=subject, body=body)
    db.add(rem)
    db.commit()
    return ReminderOut(id=rem.id, level=level, subject=subject, body=body, to=inv.buyer.email)


@router.post("/invoices/{invoice_id}/buyer-response")
def record_buyer_response(invoice_id: int, req: BuyerResponseIn, db: Session = Depends(get_db)):
    """Classify what the buyer said and flag disputes with next steps."""
    inv = _get(db, invoice_id)
    result = disputes.classify_buyer_response(req.message)
    inv.dispute_note = req.message
    inv.dispute_category = result.category if result.is_dispute else None
    db.commit()
    return result.__dict__


@router.post("/invoices/{invoice_id}/resolve-dispute")
def resolve_dispute(invoice_id: int, db: Session = Depends(get_db)):
    inv = _get(db, invoice_id)
    inv.dispute_category = None
    db.commit()
    return {"ok": True}


@router.post("/invoices/{invoice_id}/payment")
def record_payment(invoice_id: int, req: PaymentIn, db: Session = Depends(get_db)):
    inv = _get(db, invoice_id)
    inv.paid_amount = round((inv.paid_amount or 0) + req.amount, 2)
    inv.paid_date = req.paid_date or date.today()
    db.commit()
    return {"outstanding": inv.outstanding}


@router.get("/dashboard")
def dashboard(as_of: date | None = None, db: Session = Depends(get_db)):
    """Receivables intelligence: totals plus which buyers need attention first."""
    today = _today(as_of)
    rows = [_to_out(inv, today) for inv in _all(db)]
    open_rows = [r for r in rows if r.status != status.PAID]

    buyers: dict[str, dict] = defaultdict(lambda: {
        "outstanding": 0.0, "overdue_amount": 0.0, "overdue_invoices": 0,
        "max_days_overdue": 0, "interest": 0.0, "disputes": 0,
    })
    for r in open_rows:
        b = buyers[r.buyer_name]
        b["outstanding"] += r.outstanding
        b["interest"] += r.interest
        if r.status == status.OVERDUE:
            b["overdue_amount"] += r.outstanding
            b["overdue_invoices"] += 1
            b["max_days_overdue"] = max(b["max_days_overdue"], r.days_overdue)
        if r.status == status.DISPUTED:
            b["disputes"] += 1

    # Priority = money stuck x how long it has been stuck.
    ranked = sorted(
        ({"buyer": name, **{k: round(v, 2) for k, v in s.items()},
          "priority_score": round(s["overdue_amount"] * (1 + s["max_days_overdue"] / 30))}
         for name, s in buyers.items()),
        key=lambda x: x["priority_score"], reverse=True,
    )

    return {
        "as_of": today.isoformat(),
        "total_receivables": round(sum(r.outstanding for r in open_rows), 2),
        "overdue_amount": round(sum(r.outstanding for r in open_rows if r.status == status.OVERDUE), 2),
        "overdue_invoices": sum(1 for r in open_rows if r.status == status.OVERDUE),
        "open_disputes": sum(1 for r in open_rows if r.status == status.DISPUTED),
        "due_soon_amount": round(sum(r.outstanding for r in open_rows if r.status == status.DUE_SOON), 2),
        "accrued_interest": round(sum(r.interest for r in open_rows), 2),
        "buyers": ranked,
    }
