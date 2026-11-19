const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Invoice = {
  id: number;
  invoice_number: string;
  buyer_name: string;
  buyer_email: string | null;
  amount: number;
  paid_amount: number;
  outstanding: number;
  invoice_date: string;
  due_date: string;
  status: "upcoming" | "due_soon" | "overdue" | "disputed" | "paid";
  days_overdue: number;
  interest: number;
  dispute_category: string | null;
  suggested_level: string;
  reminders_sent: number;
};

export type BuyerSummary = {
  buyer: string;
  outstanding: number;
  overdue_amount: number;
  overdue_invoices: number;
  max_days_overdue: number;
  interest: number;
  disputes: number;
  priority_score: number;
};

export type Dashboard = {
  as_of: string;
  total_receivables: number;
  overdue_amount: number;
  overdue_invoices: number;
  open_disputes: number;
  due_soon_amount: number;
  accrued_interest: number;
  buyers: BuyerSummary[];
};

export type Reminder = { id: number; level: string; subject: string; body: string; to: string | null };

export type DisputeResult = {
  category: string;
  is_dispute: boolean;
  matched_keywords: string[];
  suggested_actions: string[];
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json();
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  dashboard: () => req<Dashboard>("/api/dashboard"),
  invoices: () => req<Invoice[]>("/api/invoices"),
  seedDemo: () => req("/api/demo/seed", { method: "POST" }),
  importCsv: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ created: number; updated: number; errors: unknown[] }>("/api/invoices/import", {
      method: "POST",
      body: fd,
    });
  },
  draftReminder: (id: number) => req<Reminder>(`/api/invoices/${id}/reminders`, json({})),
  buyerResponse: (id: number, message: string) =>
    req<DisputeResult>(`/api/invoices/${id}/buyer-response`, json({ message })),
};

export const inr = (n: number) =>
  "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
