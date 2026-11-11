"""New tables only. The existing users table and its rows are never recreated."""
import sqlalchemy as sa
from app.core.models import Base
from app.features.support.models import FAQ, SupportTicket, SupportReply

metadata = Base.metadata
Events = sa.Table("events", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("title", sa.Text, nullable=False), sa.Column("description", sa.Text),
    sa.Column("date_time", sa.Text), sa.Column("price", sa.Text),
    sa.Column("bank_link", sa.Text), sa.Column("card_number", sa.Text),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("is_free", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("total_tickets", sa.Integer, nullable=False),
    sa.Column("success_message", sa.Text), sa.Column("is_fixed_price", sa.Boolean, server_default=sa.true()),
    sa.Column("location", sa.Text), sa.Column("photo_id", sa.Text),
    sa.Column("venue_type", sa.String(50), nullable=False),
    sa.Column("requires_confirmation", sa.Boolean, server_default=sa.false()),
    sa.Column("available_seats_list", sa.Text),
    sa.Column("has_promo", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("promocodes", sa.Text), sa.Column("promo_discount", sa.Numeric(12,2), nullable=False, server_default="0"),
    sa.Column("generates_qr_ticket", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.CheckConstraint("total_tickets >= 0", name="ck_event_capacity"),
    sa.CheckConstraint("promo_discount >= 0", name="ck_event_discount"))
Orders = sa.Table("orders", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.telegram_id", ondelete="RESTRICT"), nullable=False, index=True),
    sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, index=True),
    sa.Column("ticket_count", sa.Integer, nullable=False),
    sa.Column("file_id", sa.Text), sa.Column("file_type", sa.Text),
    sa.Column("proof_file_id", sa.Text), sa.Column("proof_file_type", sa.Text),
    sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
    sa.Column("is_ticket_given", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("paid_amount", sa.Numeric(12,2), nullable=False, server_default="0"),
    sa.Column("required_amount", sa.Numeric(12,2), nullable=False, server_default="0"),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("promocode", sa.String(50)), sa.Column("friends", sa.Text),
    sa.CheckConstraint("ticket_count >= 0", name="ck_order_quantity"),
    sa.CheckConstraint("paid_amount >= 0 AND required_amount >= 0", name="ck_order_amounts"))
SeatTickets = sa.Table("seat_tickets", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("row_num", sa.String(30), nullable=False), sa.Column("seat_num", sa.String(30), nullable=False),
    sa.Column("file_id", sa.Text, nullable=False), sa.Column("file_type", sa.Text, nullable=False),
    sa.UniqueConstraint("event_id", "row_num", "seat_num", name="unique_seat_per_event"))
OrderSeats = sa.Table("order_seats", metadata,
    sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id", ondelete="RESTRICT"), primary_key=True),
    sa.Column("seat_key", sa.String(100), primary_key=True),
    sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True))
ProcessedTransactions = sa.Table("processed_transactions", metadata,
    sa.Column("tx_id", sa.String(255), primary_key=True),
    sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="RESTRICT")),
    sa.Column("amount", sa.Numeric(12,2)),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
Blacklist = sa.Table("blacklist", metadata, sa.Column("username", sa.String(255), primary_key=True))
NEW_TABLE_NAMES = ("events", "orders", "seat_tickets", "order_seats", "processed_transactions", "blacklist", "faq", "support_tickets", "support_replies")
