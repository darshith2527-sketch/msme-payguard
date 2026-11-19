import os

os.environ["DATABASE_URL"] = "sqlite:///./test_payguard.db"
if os.path.exists("test_payguard.db"):
    os.remove("test_payguard.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
AS_OF = "2026-11-19"


def test_demo_flow():
    seeded = client.post("/api/demo/seed").json()
    assert seeded["created"] == 6 and not seeded["errors"]

    invoices = client.get(f"/api/invoices?as_of={AS_OF}").json()
    by_no = {i["invoice_number"]: i for i in invoices}
    assert by_no["INV-1001"]["status"] == "overdue"
    assert by_no["INV-1005"]["status"] == "upcoming"
    assert by_no["INV-1006"]["status"] == "paid"
    assert by_no["INV-1003"]["outstanding"] == 150000

    dash = client.get(f"/api/dashboard?as_of={AS_OF}").json()
    assert dash["overdue_invoices"] == 4
    assert dash["buyers"][0]["buyer"] == "Shakti Auto Components"

    inv_id = by_no["INV-1001"]["id"]
    interest = client.get(f"/api/invoices/{inv_id}/interest?as_of={AS_OF}").json()
    assert interest["days_overdue"] == 38 and interest["interest"] > 0

    letter = client.post(f"/api/invoices/{inv_id}/reminders?as_of={AS_OF}",
                         json={"use_llm": False}).json()
    assert letter["level"] == "formal" and "₹3,00,000.00" in letter["body"]

    resp = client.post(f"/api/invoices/{inv_id}/buyer-response",
                       json={"message": "Invoice amount doesn't match our PO rate"}).json()
    assert resp["is_dispute"]
    assert client.get(f"/api/invoices/{inv_id}?as_of={AS_OF}").json()["status"] == "disputed"
