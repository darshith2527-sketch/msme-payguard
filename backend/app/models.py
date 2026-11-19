from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="buyer")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"))
    amount: Mapped[float] = mapped_column(Float)
    invoice_date: Mapped[date] = mapped_column(Date)
    # Date the buyer accepted the goods (MSMED Act counts from here).
    acceptance_date: Mapped[date] = mapped_column(Date)
    # Credit period agreed in writing; None = no agreement (15-day rule applies).
    agreed_credit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date] = mapped_column(Date)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Dispute tracking (from buyer responses)
    dispute_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dispute_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    buyer: Mapped[Buyer] = relationship(back_populates="invoices")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="invoice")

    @property
    def outstanding(self) -> float:
        return round(max(self.amount - (self.paid_amount or 0.0), 0.0), 2)


class Reminder(Base):
    """A drafted reminder. PayGuard drafts; the supplier decides whether to send."""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    level: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    invoice: Mapped[Invoice] = relationship(back_populates="reminders")
