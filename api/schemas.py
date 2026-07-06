# api/schemas.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class TransactionResponse(BaseModel):
    """
    Pydantic model for the transaction API response.
    Matches the format expected by extract_load.py script.
    """
    id: str = Field(..., description="Entry number from the CSV (EntryNo column)")
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    amount: float = Field(..., description="Transaction amount (Debit - Credit)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "29.1",
                "date": "2018-01-22",
                "amount": -2394.0
            }
        }


# Refined schema models
class DimAccountResponse(BaseModel):
    """Pydantic model for the dim_account refined table."""
    account_id: int = Field(..., description="Primary key for the account")
    Report: str = Field(..., description="Financial statement classification (e.g., Balance Sheet, Income Statement)")
    Class: str = Field(..., description="Broad category of account (e.g., Assets, Liabilities, Equity, Revenue, Expenses)")
    SubClass: Optional[str] = Field(None, description="Sub-classification within the class")
    SubClass2: Optional[str] = Field(None, description="Further sub-classification")
    account_name: str = Field(..., description="Name of the account")
    sub_account_name: Optional[str] = Field(None, description="Sub-account name (if applicable)")

    class Config:
        json_schema_extra = {
            "example": {
                "account_id": 1010,
                "Report": "Balance Sheet",
                "Class": "Assets",
                "SubClass": "Current Assets",
                "SubClass2": "Cash",
                "account_name": "Cash - USD",
                "sub_account_name": "Petty Cash"
            }
        }


class DimDateResponse(BaseModel):
    """Pydantic model for the dim_date refined table."""
    date_id: int = Field(..., description="Date as primary key (YYYYMMDD format)")
    year: int = Field(..., description="Year component of the date")
    month: int = Field(..., description="Month component of the date (1-12)")
    day: int = Field(..., description="Day component of the date (1-31)")
    month_year: str = Field(..., description="Month and year in text format (e.g., 'Jan 2023')")
    is_weekend: bool = Field(..., description="Flag indicating if the date is a weekend (Saturday or Sunday)")

    class Config:
        json_schema_extra = {
            "example": {
                "date_id": 20230115,
                "year": 2023,
                "month": 1,
                "day": 15,
                "month_year": "Jan 2023",
                "is_weekend": False
            }
        }


class FactGLTransactionsResponse(BaseModel):
    """Pydantic model for the fact_gl_transactions refined table."""
    transaction_id: str = Field(..., description="Primary key for the transaction")
    transaction_date: str = Field(..., description="Date of the transaction (YYYY-MM-DD)")
    account_id: int = Field(..., description="Foreign key to the account dimension")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    description: Optional[str] = Field(None, description="Transaction description")
    created_at: datetime = Field(..., description="Timestamp when the record was created")
    account_fk: int = Field(..., description="Foreign key to account dimension (redundant for clarity)")
    date_fk: int = Field(..., description="Foreign key to date dimension (redundant for clarity)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN001",
                "transaction_date": "2023-01-15",
                "account_id": 1010,
                "amount": 1500.00,
                "currency": "USD",
                "description": "Office supplies purchase",
                "created_at": "2023-01-15T10:30:00Z",
                "account_fk": 1010,
                "date_fk": 20230115
            }
        }


# Marts schema models
class NormalizeResponse(BaseModel):
    """Pydantic model for the normalize marts table."""
    entry_no: str = Field(..., description="Transaction entry number")
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    territory_key: Optional[int] = Field(None, description="Territory key")
    account_id: int = Field(..., description="Account identifier")
    details: Optional[str] = Field(None, description="Transaction details")
    debit: float = Field(..., description="Debit amount")
    credit: float = Field(..., description="Credit amount")
    amount: float = Field(..., description="Normalized amount (Debit - Credit or Credit - Debit based on account type)")

    class Config:
        json_schema_extra = {
            "example": {
                "entry_no": "TXN001",
                "date": "2023-01-15",
                "territory_key": 1,
                "account_id": 1010,
                "details": "Office supplies purchase",
                "debit": 1500.00,
                "credit": 0.00,
                "amount": 1500.00
            }
        }


class FinancialStatementsResponse(BaseModel):
    """Pydantic model for the financial_statements marts table."""
    statement_date: str = Field(..., description="Date of the financial statement (YYYY-MM-DD)")
    statement_type: str = Field(..., description="Type of financial statement (e.g., Balance Sheet)")
    account_class: str = Field(..., description="Account class (Assets, Liabilities, Equity)")
    balance: float = Field(..., description="Account balance")

    class Config:
        json_schema_extra = {
            "example": {
                "statement_date": "2023-01-31",
                "statement_type": "Balance Sheet",
                "account_class": "Assets",
                "balance": 150000.00
            }
        }


class AccountBalancesResponse(BaseModel):
    """Pydantic model for the account_balances marts table."""
    statement_date: str = Field(..., description="Date of the account balance (YYYY-MM-DD)")
    account_id: int = Field(..., description="Account identifier")
    account_name: str = Field(..., description="Name of the account")
    balance: float = Field(..., description="Account balance")

    class Config:
        json_schema_extra = {
            "example": {
                "statement_date": "2023-01-31",
                "account_id": 1010,
                "account_name": "Cash - USD",
                "balance": 50000.00
            }
        }


class IncomeStatementResponse(BaseModel):
    """Pydantic model for the income_statement_by_month marts table."""
    month: str = Field(..., description="Reporting month (YYYY-MM-DD)")
    line_type: str = Field(..., description="Income statement line type (Revenue, Operating Expense, Interest Expense)")
    account_class: str = Field(..., description="Account class from chart of accounts")
    amount: float = Field(..., description="Net amount for this classification in this month")
    revenue: float = Field(..., description="Revenue amount (0 for expense rows)")
    expenses: float = Field(..., description="Expense amount (0 for revenue rows)")

    class Config:
        json_schema_extra = {
            "example": {
                "month": "2024-01-01",
                "line_type": "Revenue",
                "account_class": "Non-operating",
                "amount": 12500.00,
                "revenue": 12500.00,
                "expenses": 0.00
            }
        }


class TrialBalanceResponse(BaseModel):
    """Pydantic model for the trial_balance_by_month marts table."""
    month: str = Field(..., description="Reporting month (YYYY-MM-DD)")
    account_id: int = Field(..., description="Account identifier")
    account_name: str = Field(..., description="Name of the account")
    account_class: str = Field(..., description="Account classification (Assets, Liabilities, Equity, Revenue, Expenses)")
    total_debit: float = Field(..., description="Sum of debits for this account in this month")
    total_credit: float = Field(..., description="Sum of credits for this account in this month")
    net_amount: float = Field(..., description="total_debit - total_credit")

    class Config:
        json_schema_extra = {
            "example": {
                "month": "2024-01-01",
                "account_id": 1010,
                "account_name": "Cash - USD",
                "account_class": "Assets",
                "total_debit": 50000.00,
                "total_credit": 12000.00,
                "net_amount": 38000.00
            }
        }