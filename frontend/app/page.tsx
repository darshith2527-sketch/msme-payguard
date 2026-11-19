"use client";

import { useCallback, useEffect, useState } from "react";
import { api, inr, type Dashboard, type DisputeResult, type Invoice, type Reminder } from "@/lib/api";

const STATUS_LABEL: Record<Invoice["status"], string> = {
  upcoming: "Upcoming",
  due_soon: "Due soon",
  overdue: "Overdue",
  disputed: "Disputed",
  paid: "Paid",
};

export default function Home() {
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [letter, setLetter] = useState<Reminder | null>(null);
  const [dispute, setDispute] = useState<{ inv: Invoice; result?: DisputeResult } | null>(null);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [d, i] = await Promise.all([api.dashboard(), api.invoices()]);
      setDash(d);
      setInvoices(i);
      setError(null);
    } catch (e) {
      setError(`Can't reach the API. Is the backend running? (${(e as Error).message})`);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = (fn: () => Promise<unknown>) => async () => {
    try {
      await fn();
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <main>
      <header>
        <div>
          <h1>MSME PayGuard</h1>
          <p className="muted">Every invoice tracked. Every payment protected.</p>
        </div>
        <div className="actions">
          <label className="btn">
            Import CSV
            <input
              type="file"
              accept=".csv"
              hidden
              onChange={(e) => e.target.files?.[0] && run(() => api.importCsv(e.target.files![0]))()}
            />
          </label>
          <button className="btn secondary" onClick={run(api.seedDemo)}>
            Load demo data
          </button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      {dash && (
        <section className="cards">
          <Card label="Total receivables" value={inr(dash.total_receivables)} />
          <Card label="Overdue" value={inr(dash.overdue_amount)} sub={`${dash.overdue_invoices} invoices`} tone="red" />
          <Card label="Open disputes" value={String(dash.open_disputes)} tone="amber" />
          <Card label="Due in 7 days" value={inr(dash.due_soon_amount)} />
          <Card label="MSMED interest accrued" value={inr(dash.accrued_interest)} sub="indicative" />
        </section>
      )}

      {dash && dash.buyers.length > 0 && (
        <section>
          <h2>Who to chase first</h2>
          <table>
            <thead>
              <tr>
                <th>Buyer</th><th>Outstanding</th><th>Overdue</th><th>Longest delay</th><th>Disputes</th>
              </tr>
            </thead>
            <tbody>
              {dash.buyers.map((b) => (
                <tr key={b.buyer}>
                  <td>{b.buyer}</td>
                  <td>{inr(b.outstanding)}</td>
                  <td>{inr(b.overdue_amount)}</td>
                  <td>{b.max_days_overdue ? `${b.max_days_overdue} days` : "—"}</td>
                  <td>{b.disputes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section>
        <h2>Invoices</h2>
        {invoices.length === 0 ? (
          <p className="muted">No invoices yet. Import a CSV or load the demo data.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Invoice</th><th>Buyer</th><th>Outstanding</th><th>Due</th><th>Status</th><th>Interest</th><th />
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.invoice_number}</td>
                  <td>{inv.buyer_name}</td>
                  <td>{inr(inv.outstanding)}</td>
                  <td>{inv.due_date}</td>
                  <td>
                    <span className={`chip ${inv.status}`}>
                      {STATUS_LABEL[inv.status]}
                      {inv.status === "overdue" && ` · ${inv.days_overdue}d`}
                    </span>
                  </td>
                  <td>{inv.interest ? inr(inv.interest) : "—"}</td>
                  <td className="row-actions">
                    {inv.status !== "paid" && (
                      <>
                        <button onClick={run(async () => setLetter(await api.draftReminder(inv.id)))}>
                          Draft {inv.suggested_level.replace("_", " ")}
                        </button>
                        <button onClick={() => { setDispute({ inv }); setMessage(""); }}>
                          Buyer replied
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {letter && (
        <Modal onClose={() => setLetter(null)} title={letter.subject}>
          <p className="muted">To: {letter.to ?? "buyer email not set"} · tone: {letter.level}</p>
          <pre>{letter.body}</pre>
          <button className="btn" onClick={() => navigator.clipboard.writeText(letter.body)}>
            Copy letter
          </button>
        </Modal>
      )}

      {dispute && (
        <Modal onClose={() => setDispute(null)} title={`Buyer response – ${dispute.inv.invoice_number}`}>
          <textarea
            placeholder="Paste what the buyer said, e.g. “Amount doesn't match our PO”"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button
            className="btn"
            disabled={!message}
            onClick={run(async () => setDispute({ ...dispute, result: await api.buyerResponse(dispute.inv.id, message) }))}
          >
            Analyse
          </button>
          {dispute.result && (
            <div className="result">
              <p>
                <strong>{dispute.result.category.replaceAll("_", " ")}</strong>
                {dispute.result.is_dispute ? " — flagged as dispute" : " — not a dispute"}
              </p>
              <ul>
                {dispute.result.suggested_actions.map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          )}
        </Modal>
      )}

      <footer className="muted">
        Interest figures are indicative (MSMED Act s.15–16) and must be verified by a CA.
      </footer>
    </main>
  );
}

function Card({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "red" | "amber" }) {
  return (
    <div className={`card ${tone ?? ""}`}>
      <span className="muted">{label}</span>
      <strong>{value}</strong>
      {sub && <span className="muted small">{sub}</span>}
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}
