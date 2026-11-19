# MSME PayGuard

**AI-powered receivables intelligence and dispute prevention for India's MSMEs**

> *Every invoice tracked. Every payment protected.*

Built for the **GAVS Hackathon**.

---

## The problem

Raju runs a small fabrication unit. Three buyers owe him ₹8.4 lakh, and he still has to pay wages, buy raw material and cover the electricity bill. Delayed payments are one of the biggest cash-flow problems for Micro, Small and Medium Enterprises in India.

Tools already exist for parts of this problem:

| Existing solution | What it covers |
|---|---|
| **MSME Samadhaan** | Formal delayed-payment complaints to the Facilitation Council |
| **MSME ODR Portal** | Online negotiation, mediation and dispute resolution |
| **Zoho Books / Tally** | Accounting, invoicing and payment reminders |
| **TReDS** | Invoice financing |

**The gap is between delivering the invoice and reaching a formal dispute.** Suppliers often don't know *why* a payment is stuck, which buyer to chase first, or whether their paperwork would hold up. They also worry that pushing too hard will cost them a customer.

## Our solution

PayGuard is built for the supplier. It doesn't replace accounting software or government portals. It helps the supplier act early and with the right tone, so fewer delays turn into formal disputes.

| Module | What it does | Status |
|---|---|---|
| Invoice import | CSV, Excel or Tally export → invoices with due dates | ✅ MVP |
| Due-date clocks | Upcoming / due soon / overdue / disputed / paid | ✅ MVP |
| Receivables intelligence | Ranks buyers by money stuck × days delayed ("who to chase first") | ✅ MVP |
| MSMED interest calculator | s.15 due-date rules (45-day cap, 15-day default) and s.16 compound interest at 3× RBI bank rate | ✅ MVP |
| Relationship-safe escalation | Friendly → follow-up → formal → escalation, picked from status and history | ✅ MVP |
| AI letter polishing | Optional LLM improves the tone; facts always come from the rules engine | ✅ MVP |
| Dispute detection | Classifies buyer replies (PO mismatch, goods not received, quality, missing docs…) and suggests next steps | ✅ MVP (rule-based) |
| Digital evidence locker | Invoice, PO, delivery challan, e-way bill and chats in one folder per invoice | 🔜 Planned |
| OCR invoice upload | Read invoice photos/PDFs with Tesseract or Google Vision | 🔜 Planned |
| Email / WhatsApp reminders | Send drafts to buyers; buyer clicks "paid / processing / disputed" | 🔜 Planned |
| Legal-readiness report | Pre-filled summary and document pack for MSME Samadhaan | 🔜 Planned |
| Buyer reliability score | Payment behaviour across suppliers (opt-in, privacy-safe) | 🧪 Stretch |

## Architecture

```
┌──────────────┐     REST      ┌──────────────────────────────┐     ┌────────────┐
│  Next.js UI  │ ───────────▶ │  FastAPI backend               │ ──▶ │ PostgreSQL │
│  (frontend/) │              │  ├─ importer   (CSV → invoices)│     │ (or SQLite)│
└──────────────┘              │  ├─ status     (due clocks)    │     └────────────┘
                              │  ├─ interest   (MSMED s.15/16) │
                              │  ├─ disputes   (why unpaid?)   │     ┌────────────┐
                              │  └─ reminders  (tone + letter) │ ──▶ │  LLM API   │
                              └──────────────────────────────┘     │ (optional) │
                                                                    └────────────┘
```

**Stack:** Next.js, React, TypeScript · Python FastAPI · SQLAlchemy · PostgreSQL · any OpenAI-compatible LLM

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs. The backend uses SQLite by default, so you don't need a database to start.

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 and click **Load demo data**.

### Using Postgres (optional)

```bash
docker compose up -d db
# then in backend/.env:
DATABASE_URL=postgresql+psycopg://payguard:payguard@localhost:5432/payguard
```

### Run tests

```bash
cd backend && pytest
```

## CSV format

| Column | Required | Example |
|---|---|---|
| `invoice_number` | ✅ | INV-1001 |
| `buyer_name` | ✅ | Shakti Auto Components |
| `amount` | ✅ | 300000 or ₹3,00,000 |
| `invoice_date` | ✅ | 2026-09-10 or 10/09/2026 |
| `buyer_email` | | accounts@buyer.com |
| `acceptance_date` | | date the buyer accepted the goods (defaults to invoice date) |
| `credit_days` | | agreed credit period (blank = no written agreement) |
| `due_date` | | overrides the calculated due date |
| `paid_amount` | | amount already received |

See [`sample_data/invoices.csv`](sample_data/invoices.csv).

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/invoices/import` | Upload a CSV |
| POST | `/api/demo/seed` | Load demo invoices |
| GET | `/api/dashboard` | Totals plus buyers ranked by priority |
| GET | `/api/invoices` | All invoices with status, days overdue and interest |
| GET | `/api/invoices/{id}/interest` | Detailed MSMED interest breakdown |
| POST | `/api/invoices/{id}/reminders` | Draft a reminder (tone suggested automatically) |
| POST | `/api/invoices/{id}/buyer-response` | Classify the buyer's reply and flag disputes |
| POST | `/api/invoices/{id}/payment` | Record a payment |

All `GET` endpoints accept `?as_of=YYYY-MM-DD`, so demo numbers stay the same on any date.

## 3-minute demo script

1. **Hook:** "Raju's fabrication unit is owed lakhs by three buyers. He can't pay his workers."
2. **Import:** upload the CSV. The dashboard shows red overdue clocks.
3. **Who to chase first:** the buyer with the most money stuck for the longest is at the top.
4. **Interest:** show what the buyer legally owes under the MSMED Act.
5. **Right tone:** draft a letter. PayGuard picks "formal" rather than an aggressive notice, because Raju depends on this buyer.
6. **Dispute:** paste the buyer's reply ("amount doesn't match our PO"). PayGuard flags a PO mismatch and lists the documents to send.
7. **Close:** "We work in the gap before a dispute becomes a legal case, alongside Samadhaan and Zoho rather than in place of them."

## Legal disclaimer

PayGuard is a hackathon prototype. Interest calculations follow a simplified reading of Sections 15–16 of the MSMED Act, 2006, and use a configurable RBI bank rate (`RBI_BANK_RATE` in `.env`; check the current rate on rbi.org.in). The Act's protections apply only to eligible (Udyam-registered micro and small) suppliers. Have a Chartered Accountant review all legal logic before anyone relies on it. PayGuard drafts letters and prepares information; it doesn't send legal notices or file complaints on its own.

## Team

| Name | Role |
|---|---|
| _add name_ | _frontend / backend / AI / pitch_ |

## License

[MIT](LICENSE)
