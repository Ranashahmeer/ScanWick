import uuid
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, Date, ForeignKey, Numeric, String, Text, Uuid, Integer
from sqlalchemy import Enum as SAEnum

from app.models.auth import Base


class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"


class TransactionMode(str, Enum):
    bank_transfer = "bank_transfer"
    pos = "pos"
    cash_withdrawal = "cash_withdrawal"
    mobile_money = "mobile_money"
    direct_debit = "direct_debit"
    standing_order = "standing_order"
    bank_charge = "bank_charge"


class TransactionCategory(str, Enum):
    income = "income"
    operational_expense = "operational_expense"
    personal = "personal"
    debt_service = "debt_service"
    interbank_transfer = "interbank_transfer"
    tax = "tax"
    unknown = "unknown"


class BankTransactionDataSource(str, Enum):
    gtbank_pdf = "gtbank_pdf"
    access_csv = "access_csv"
    zenith_pdf = "zenith_pdf"
    opay_csv = "opay_csv"
    generic_csv = "generic_csv"
    generic_pdf = "generic_pdf"
    mono_api = "mono_api"


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id = Column(Uuid, ForeignKey("accounts.id"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    payee_normalized = Column(String, nullable=True)
    amount = Column(Integer, nullable=False)
    original_currency = Column(String(3), nullable=False)
    base_currency_amount = Column(Integer, nullable=True)
    exchange_rate = Column(Numeric(10, 6), nullable=True)
    type = Column(SAEnum(TransactionType, validate_strings=True), nullable=False)
    mode = Column(SAEnum(TransactionMode, validate_strings=True), nullable=True)
    category = Column(
        SAEnum(TransactionCategory, validate_strings=True), nullable=True, default=TransactionCategory.unknown
    )
    is_recurring = Column(Boolean, nullable=False, default=False)
    is_own_account_transfer = Column(Boolean, nullable=False, default=False)
    is_anomalous = Column(Boolean, nullable=False, default=False)
    fraud_flags = Column(JSON, nullable=True, default=list)
    balance_after = Column(Integer, nullable=True)
    data_source = Column(SAEnum(BankTransactionDataSource, validate_strings=True), nullable=False)
