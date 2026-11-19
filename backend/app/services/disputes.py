"""Payment dispute detection: work out WHY a buyer hasn't paid.

v1 is rule-based (fast, explainable, no API key needed). Swap in an LLM
classifier later using the same categories.
"""
from dataclasses import dataclass

# Order matters for ties: more specific categories first.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "po_mismatch": ["purchase order", "po number", "po mismatch", " po ", "po#"],
    "goods_not_received": ["not received", "not delivered", "didn't receive", "did not receive",
                           "short supply", "short quantity", "nahi mila", "nahi aaya"],
    "quality_issue": ["quality", "defect", "damaged", "rejected", "faulty", "broken"],
    "missing_documents": ["e-way", "eway", "gst invoice", "delivery challan", "grn", "document",
                          "copy of", "signed", "proof"],
    "amount_mismatch": ["amount", "mismatch", "rate", "price", "doesn't match", "does not match",
                        "difference", "excess", "wrong total"],
    "needs_time": ["next week", "more time", "cash flow", "processing", "approval pending",
                   "will pay", "will release", "few days"],
}

SUGGESTED_ACTIONS: dict[str, list[str]] = {
    "po_mismatch": ["Attach the buyer's purchase order", "Reconcile line items against the PO",
                    "Share a corrected invoice or credit note if needed"],
    "goods_not_received": ["Attach signed delivery challan / LR copy", "Attach e-way bill",
                           "Ask buyer for their GRN (goods receipt note)"],
    "quality_issue": ["Request the buyer's inspection/rejection report",
                      "Propose replacement or partial credit for rejected units"],
    "missing_documents": ["Send the missing documents from the Evidence Locker",
                          "Confirm GST invoice and e-way bill details match"],
    "amount_mismatch": ["Reconcile invoice amount with PO rates and quantities",
                        "Share rate confirmation (email/quote) agreed with the buyer"],
    "needs_time": ["Ask for a committed payment date in writing",
                   "Track whether the promised date is met"],
    "unclear": ["Ask the buyer to specify the reason for the delay"],
}


@dataclass
class DisputeResult:
    category: str
    is_dispute: bool
    matched_keywords: list[str]
    suggested_actions: list[str]


def classify_buyer_response(message: str) -> DisputeResult:
    text = f" {message.lower()} "
    best, best_hits = "unclear", []
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = [k.strip() for k in keywords if k in text]
        if len(hits) > len(best_hits):
            best, best_hits = category, hits
    return DisputeResult(
        category=best,
        # "needs_time" is a payment promise, not a dispute about the invoice.
        is_dispute=best not in ("needs_time", "unclear"),
        matched_keywords=best_hits,
        suggested_actions=SUGGESTED_ACTIONS[best],
    )
