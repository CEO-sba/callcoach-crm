"""
CallCoach CRM - Legal & Finance Router
Legal document management and financial records tracking.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    LegalDocument,
    FinanceRecord
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["legal", "finance"])


# ===== LEGAL DOCUMENTS =====

@router.get("/legal/documents")
async def list_legal_documents(
    document_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List clinic legal documents."""
    query = db.query(LegalDocument).filter(
        LegalDocument.clinic_id == current_user.clinic_id
    )

    if document_type:
        query = query.filter(LegalDocument.document_type == document_type)
    if search:
        query = query.filter(
            (LegalDocument.title.ilike(f"%{search}%")) |
            (LegalDocument.description.ilike(f"%{search}%"))
        )

    documents = query.order_by(
        LegalDocument.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "documents": documents,
        "total": query.count()
    }


@router.post("/legal/documents")
async def upload_legal_document(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload or create a legal document.
    Expected data: {
        "title": "Document Title",
        "document_type": "contract|policy|compliance|other",
        "description": "Description",
        "file_url": "URL to document file",
        "expiration_date": "2025-03-15"
    }
    """
    required_fields = ["title", "document_type"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    document = LegalDocument(
        clinic_id=current_user.clinic_id,
        title=data["title"],
        document_type=data["document_type"],
        description=data.get("description", ""),
        file_url=data.get("file_url", ""),
        expiration_date=data.get("expiration_date"),
        status="active"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "status": "created",
        "document_id": document.id,
        "document": document
    }


@router.put("/legal/documents/{document_id}")
async def update_legal_document(
    document_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update legal document details."""
    document = db.query(LegalDocument).filter(
        LegalDocument.id == document_id,
        LegalDocument.clinic_id == current_user.clinic_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(document, field):
            setattr(document, field, value)

    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)

    return {
        "status": "updated",
        "document_id": document.id,
        "document": document
    }


# ===== FINANCE RECORDS =====

@router.get("/finance/records")
async def list_finance_records(
    record_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List finance records with optional filters by type, category, and date range."""
    query = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == current_user.clinic_id
    )

    if record_type:
        query = query.filter(FinanceRecord.record_type == record_type)
    if category:
        query = query.filter(FinanceRecord.category == category)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(FinanceRecord.date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(FinanceRecord.date <= end)
        except ValueError:
            pass

    records = query.order_by(
        FinanceRecord.date.desc()
    ).offset(skip).limit(limit).all()

    return {
        "records": records,
        "total": query.count()
    }


@router.post("/finance/records")
async def create_finance_record(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a finance record (income or expense).
    Expected data: {
        "record_type": "income|expense",
        "category": "Category Name",
        "amount": 1000.00,
        "description": "Description",
        "date": "2024-03-15",
        "notes": "Optional notes"
    }
    """
    required_fields = ["record_type", "category", "amount"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    if data["record_type"] not in ["income", "expense"]:
        raise HTTPException(
            status_code=400,
            detail="record_type must be 'income' or 'expense'"
        )

    record = FinanceRecord(
        clinic_id=current_user.clinic_id,
        record_type=data["record_type"],
        category=data["category"],
        amount=data["amount"],
        description=data.get("description", ""),
        date=data.get("date", datetime.utcnow().date()),
        notes=data.get("notes")
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "created",
        "record_id": record.id,
        "record": record
    }


@router.get("/finance/summary")
async def get_financial_summary(
    period: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get financial summary (revenue, expenses, profit by period).
    Query param: period (monthly|quarterly|yearly|all)
    """
    clinic_id = current_user.clinic_id

    # Default to last 30 days
    if period == "quarterly":
        days_back = 90
    elif period == "yearly":
        days_back = 365
    elif period == "all":
        days_back = None
    else:  # default monthly
        days_back = 30

    query = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id
    )

    if days_back:
        start_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(FinanceRecord.date >= start_date)

    all_records = query.all()

    # Calculate totals
    total_income = sum(r.amount for r in all_records if r.record_type == "income")
    total_expenses = sum(r.amount for r in all_records if r.record_type == "expense")
    net_profit = total_income - total_expenses

    # Category breakdown
    income_by_category = {}
    expense_by_category = {}

    for record in all_records:
        if record.record_type == "income":
            if record.category not in income_by_category:
                income_by_category[record.category] = 0
            income_by_category[record.category] += record.amount
        else:
            if record.category not in expense_by_category:
                expense_by_category[record.category] = 0
            expense_by_category[record.category] += record.amount

    period_label = period or "monthly"
    if period == "all":
        period_label = "all_time"

    return {
        "period": period_label,
        "summary": {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2)
        },
        "by_category": {
            "income": income_by_category,
            "expenses": expense_by_category
        },
        "record_count": len(all_records)
    }


@router.get("/finance/dashboard")
async def finance_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get finance dashboard overview."""
    clinic_id = current_user.clinic_id

    # Get last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    records = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id,
        FinanceRecord.date >= thirty_days_ago
    ).all()

    # Calculate metrics
    total_income = sum(r.amount for r in records if r.record_type == "income")
    total_expenses = sum(r.amount for r in records if r.record_type == "expense")
    net_profit = total_income - total_expenses

    # Get year-to-date comparison
    year_start = datetime.utcnow().replace(month=1, day=1).date()
    ytd_records = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id,
        FinanceRecord.date >= year_start
    ).all()

    ytd_income = sum(r.amount for r in ytd_records if r.record_type == "income")
    ytd_expenses = sum(r.amount for r in ytd_records if r.record_type == "expense")
    ytd_profit = ytd_income - ytd_expenses

    # Top categories
    expense_categories = {}
    for record in records:
        if record.record_type == "expense":
            if record.category not in expense_categories:
                expense_categories[record.category] = 0
            expense_categories[record.category] += record.amount

    top_expenses = sorted(
        expense_categories.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {
        "current_period": {
            "period": "Last 30 days",
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2)
        },
        "year_to_date": {
            "total_income": round(ytd_income, 2),
            "total_expenses": round(ytd_expenses, 2),
            "net_profit": round(ytd_profit, 2)
        },
        "top_expenses": [
            {
                "category": cat,
                "amount": round(amount, 2)
            }
            for cat, amount in top_expenses
        ],
        "record_count": len(records)
    }
