"""
CallCoach CRM - Legal & Finance Router (v2.1 - Full Integration)
Legal documents, invoices, financial records, and AI financial analysis.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    ClinicDocument,
    FinanceRecord,
    Invoice,
)
# Alias for backward compat
LegalDocument = ClinicDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["legal", "finance"])


# ============================================================================
# 1. LEGAL DOCUMENTS
# ============================================================================

@router.get("/legal/documents")
async def list_legal_documents(
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List legal documents with filters."""
    query = db.query(ClinicDocument).filter(
        ClinicDocument.clinic_id == current_user.clinic_id
    )

    if document_type:
        query = query.filter(ClinicDocument.document_type == document_type)
    if status:
        query = query.filter(ClinicDocument.status == status)
    if search:
        query = query.filter(ClinicDocument.title.ilike(f"%{search}%"))

    total = query.count()
    documents = query.order_by(desc(ClinicDocument.created_at)).offset(skip).limit(limit).all()

    results = []
    for d in documents:
        results.append({
            "id": d.id,
            "title": d.title,
            "document_type": d.document_type,
            "file_url": d.file_url,
            "status": d.status,
            "valid_until": str(d.valid_until) if d.valid_until else None,
            "is_expired": d.valid_until < datetime.utcnow() if d.valid_until else False,
            "created_at": str(d.created_at) if d.created_at else None,
            "updated_at": str(d.updated_at) if d.updated_at else None,
        })

    return {"documents": results, "total": total}


@router.post("/legal/documents")
async def create_document(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a legal document record."""
    if "title" not in data or "document_type" not in data:
        raise HTTPException(status_code=400, detail="title and document_type required")

    valid_types = ["contract", "agreement", "nda", "consent_form", "policy", "license"]
    if data["document_type"] not in valid_types:
        raise HTTPException(status_code=400, detail=f"document_type must be one of: {valid_types}")

    document = ClinicDocument(
        clinic_id=current_user.clinic_id,
        title=data["title"],
        document_type=data["document_type"],
        file_url=data.get("file_url", ""),
        status=data.get("status", "draft"),
        valid_until=data.get("valid_until"),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {"status": "created", "document_id": document.id}


@router.put("/legal/documents/{document_id}")
async def update_document(
    document_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a legal document."""
    document = db.query(ClinicDocument).filter(
        ClinicDocument.id == document_id,
        ClinicDocument.clinic_id == current_user.clinic_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    allowed = ["title", "document_type", "file_url", "status", "valid_until"]
    for field, value in data.items():
        if field in allowed:
            setattr(document, field, value)

    db.commit()
    return {"status": "updated", "document_id": document.id}


@router.delete("/legal/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a legal document."""
    document = db.query(ClinicDocument).filter(
        ClinicDocument.id == document_id,
        ClinicDocument.clinic_id == current_user.clinic_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()
    return {"status": "deleted"}


@router.get("/legal/expiring")
async def get_expiring_documents(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get documents expiring within N days."""
    cutoff = datetime.utcnow() + timedelta(days=days)
    now = datetime.utcnow()

    documents = db.query(ClinicDocument).filter(
        ClinicDocument.clinic_id == current_user.clinic_id,
        ClinicDocument.valid_until != None,
        ClinicDocument.valid_until <= cutoff,
        ClinicDocument.status != "archived",
    ).order_by(ClinicDocument.valid_until.asc()).all()

    results = []
    for d in documents:
        days_left = (d.valid_until - now).days if d.valid_until else 0
        results.append({
            "id": d.id,
            "title": d.title,
            "document_type": d.document_type,
            "valid_until": str(d.valid_until),
            "days_remaining": max(days_left, 0),
            "is_expired": days_left < 0,
        })

    return {"expiring_documents": results, "total": len(results)}


# ============================================================================
# 2. INVOICES
# ============================================================================

@router.get("/finance/invoices")
async def list_invoices(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List invoices with filters."""
    query = db.query(Invoice).filter(Invoice.clinic_id == current_user.clinic_id)

    if status:
        query = query.filter(Invoice.status == status)
    if lead_id:
        query = query.filter(Invoice.lead_id == lead_id)
    if search:
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Invoice.patient_name.ilike(f"%{search}%"),
            )
        )
    if date_from:
        query = query.filter(Invoice.created_at >= date_from)
    if date_to:
        query = query.filter(Invoice.created_at <= date_to)

    total = query.count()
    invoices = query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()

    results = []
    for inv in invoices:
        results.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "patient_name": inv.patient_name,
            "patient_phone": inv.patient_phone,
            "items": inv.items or [],
            "subtotal": inv.subtotal,
            "tax_percent": inv.tax_percent,
            "tax_amount": inv.tax_amount,
            "discount_percent": inv.discount_percent,
            "discount_amount": inv.discount_amount,
            "total": inv.total,
            "status": inv.status,
            "due_date": str(inv.due_date) if inv.due_date else None,
            "paid_at": str(inv.paid_at) if inv.paid_at else None,
            "payment_method": inv.payment_method,
            "notes": inv.notes,
            "created_at": str(inv.created_at) if inv.created_at else None,
        })

    return {"invoices": results, "total": total}


@router.post("/finance/invoices")
async def create_invoice(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create an invoice.
    Required: invoice_number, patient_name, items
    Items format: [{"description": "...", "quantity": 1, "unit_price": 100.00}]
    """
    if "invoice_number" not in data or "patient_name" not in data:
        raise HTTPException(status_code=400, detail="invoice_number and patient_name required")

    items = data.get("items", [])

    # Calculate totals
    subtotal = sum(
        item.get("quantity", 1) * item.get("unit_price", 0) for item in items
    )
    tax_percent = data.get("tax_percent", 0)
    tax_amount = subtotal * (tax_percent / 100)
    discount_percent = data.get("discount_percent", 0)
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal + tax_amount - discount_amount

    # Add total to each item
    for item in items:
        item["total"] = item.get("quantity", 1) * item.get("unit_price", 0)

    invoice = Invoice(
        clinic_id=current_user.clinic_id,
        lead_id=data.get("lead_id"),
        invoice_number=data["invoice_number"],
        patient_name=data["patient_name"],
        patient_phone=data.get("patient_phone"),
        items=items,
        subtotal=round(subtotal, 2),
        tax_percent=tax_percent,
        tax_amount=round(tax_amount, 2),
        discount_percent=discount_percent,
        discount_amount=round(discount_amount, 2),
        total=round(total, 2),
        status=data.get("status", "draft"),
        due_date=data.get("due_date"),
        notes=data.get("notes"),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {"status": "created", "invoice_id": invoice.id, "total": invoice.total}


@router.get("/finance/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full invoice details."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.clinic_id == current_user.clinic_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "lead_id": invoice.lead_id,
            "patient_name": invoice.patient_name,
            "patient_phone": invoice.patient_phone,
            "items": invoice.items or [],
            "subtotal": invoice.subtotal,
            "tax_percent": invoice.tax_percent,
            "tax_amount": invoice.tax_amount,
            "discount_percent": invoice.discount_percent,
            "discount_amount": invoice.discount_amount,
            "total": invoice.total,
            "status": invoice.status,
            "due_date": str(invoice.due_date) if invoice.due_date else None,
            "paid_at": str(invoice.paid_at) if invoice.paid_at else None,
            "payment_method": invoice.payment_method,
            "notes": invoice.notes,
            "created_at": str(invoice.created_at) if invoice.created_at else None,
        }
    }


@router.put("/finance/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an invoice."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.clinic_id == current_user.clinic_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    allowed = [
        "patient_name", "patient_phone", "items", "status",
        "due_date", "notes", "tax_percent", "discount_percent", "payment_method",
    ]
    for field, value in data.items():
        if field in allowed:
            setattr(invoice, field, value)

    # Recalculate if items changed
    if "items" in data or "tax_percent" in data or "discount_percent" in data:
        items = invoice.items or []
        subtotal = sum(item.get("quantity", 1) * item.get("unit_price", 0) for item in items)
        tax_amount = subtotal * (invoice.tax_percent / 100)
        discount_amount = subtotal * (invoice.discount_percent / 100)
        invoice.subtotal = round(subtotal, 2)
        invoice.tax_amount = round(tax_amount, 2)
        invoice.discount_amount = round(discount_amount, 2)
        invoice.total = round(subtotal + tax_amount - discount_amount, 2)

    db.commit()
    return {"status": "updated", "invoice_id": invoice.id, "total": invoice.total}


@router.put("/finance/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark an invoice as paid."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.clinic_id == current_user.clinic_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    data = data or {}
    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()
    invoice.payment_method = data.get("payment_method", invoice.payment_method)

    # Auto-create finance record for the income
    record = FinanceRecord(
        clinic_id=current_user.clinic_id,
        record_type="income",
        category="treatment_fee",
        amount=invoice.total,
        description=f"Invoice {invoice.invoice_number} - {invoice.patient_name}",
        date=datetime.utcnow(),
        payment_method=invoice.payment_method,
        reference_number=invoice.invoice_number,
    )
    db.add(record)
    db.commit()

    return {"status": "paid", "invoice_id": invoice.id, "paid_at": str(invoice.paid_at)}


# ============================================================================
# 3. FINANCE RECORDS
# ============================================================================

@router.get("/finance/records")
async def list_finance_records(
    record_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_method: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List finance records with filters."""
    query = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == current_user.clinic_id
    )

    if record_type:
        query = query.filter(FinanceRecord.record_type == record_type)
    if category:
        query = query.filter(FinanceRecord.category == category)
    if payment_method:
        query = query.filter(FinanceRecord.payment_method == payment_method)
    if start_date:
        try:
            query = query.filter(FinanceRecord.date >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            query = query.filter(FinanceRecord.date <= datetime.fromisoformat(end_date))
        except ValueError:
            pass

    total = query.count()
    records = query.order_by(desc(FinanceRecord.date)).offset(skip).limit(limit).all()

    results = []
    for r in records:
        results.append({
            "id": r.id,
            "record_type": r.record_type,
            "category": r.category,
            "amount": r.amount,
            "description": r.description,
            "date": str(r.date) if r.date else None,
            "payment_method": r.payment_method,
            "reference_number": r.reference_number,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"records": results, "total": total}


@router.post("/finance/records")
async def create_finance_record(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a finance record (income or expense)."""
    required = ["record_type", "category", "amount"]
    for f in required:
        if f not in data:
            raise HTTPException(status_code=400, detail=f"Missing: {f}")

    if data["record_type"] not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="record_type must be income or expense")

    record = FinanceRecord(
        clinic_id=current_user.clinic_id,
        record_type=data["record_type"],
        category=data["category"],
        amount=data["amount"],
        description=data.get("description", ""),
        date=data.get("date", datetime.utcnow()),
        payment_method=data.get("payment_method"),
        reference_number=data.get("reference_number"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"status": "created", "record_id": record.id}


@router.delete("/finance/records/{record_id}")
async def delete_finance_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a finance record."""
    record = db.query(FinanceRecord).filter(
        FinanceRecord.id == record_id,
        FinanceRecord.clinic_id == current_user.clinic_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()
    return {"status": "deleted"}


# ============================================================================
# 4. FINANCIAL DASHBOARD & SUMMARY
# ============================================================================

@router.get("/finance/dashboard")
async def finance_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Comprehensive finance dashboard."""
    clinic_id = current_user.clinic_id
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Current period records
    current_records = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id,
        FinanceRecord.date >= thirty_days_ago
    ).all()

    current_income = sum(r.amount for r in current_records if r.record_type == "income")
    current_expenses = sum(r.amount for r in current_records if r.record_type == "expense")

    # Previous period for comparison
    sixty_days_ago = now - timedelta(days=60)
    prev_records = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id,
        FinanceRecord.date >= sixty_days_ago,
        FinanceRecord.date < thirty_days_ago
    ).all()

    prev_income = sum(r.amount for r in prev_records if r.record_type == "income")
    prev_expenses = sum(r.amount for r in prev_records if r.record_type == "expense")

    # YTD
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    ytd_records = db.query(FinanceRecord).filter(
        FinanceRecord.clinic_id == clinic_id,
        FinanceRecord.date >= year_start
    ).all()

    ytd_income = sum(r.amount for r in ytd_records if r.record_type == "income")
    ytd_expenses = sum(r.amount for r in ytd_records if r.record_type == "expense")

    # Category breakdowns
    expense_cats = {}
    income_cats = {}
    for r in current_records:
        target = income_cats if r.record_type == "income" else expense_cats
        target[r.category] = target.get(r.category, 0) + r.amount

    # Invoice stats
    total_invoices = db.query(func.count(Invoice.id)).filter(Invoice.clinic_id == clinic_id).scalar() or 0
    unpaid_invoices = db.query(Invoice).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status.in_(["sent", "overdue"])
    ).all()
    outstanding_amount = sum(inv.total for inv in unpaid_invoices)
    overdue_count = sum(1 for inv in unpaid_invoices if inv.status == "overdue")

    # Income growth
    income_growth = 0
    if prev_income > 0:
        income_growth = round((current_income - prev_income) / prev_income * 100, 1)

    return {
        "current_period": {
            "period": "Last 30 days",
            "income": round(current_income, 2),
            "expenses": round(current_expenses, 2),
            "profit": round(current_income - current_expenses, 2),
            "profit_margin": round((current_income - current_expenses) / current_income * 100, 1) if current_income > 0 else 0,
        },
        "previous_period": {
            "income": round(prev_income, 2),
            "expenses": round(prev_expenses, 2),
            "profit": round(prev_income - prev_expenses, 2),
        },
        "income_growth_percent": income_growth,
        "year_to_date": {
            "income": round(ytd_income, 2),
            "expenses": round(ytd_expenses, 2),
            "profit": round(ytd_income - ytd_expenses, 2),
        },
        "invoices": {
            "total": total_invoices,
            "outstanding_amount": round(outstanding_amount, 2),
            "overdue_count": overdue_count,
        },
        "top_expense_categories": sorted(expense_cats.items(), key=lambda x: x[1], reverse=True)[:5],
        "top_income_categories": sorted(income_cats.items(), key=lambda x: x[1], reverse=True)[:5],
    }


@router.get("/finance/summary")
async def get_financial_summary(
    period: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get financial summary by period (monthly, quarterly, yearly, all)."""
    clinic_id = current_user.clinic_id

    days_map = {"monthly": 30, "quarterly": 90, "yearly": 365, "all": None}
    days_back = days_map.get(period, 30)

    query = db.query(FinanceRecord).filter(FinanceRecord.clinic_id == clinic_id)
    if days_back:
        start = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(FinanceRecord.date >= start)

    records = query.all()

    income = sum(r.amount for r in records if r.record_type == "income")
    expenses = sum(r.amount for r in records if r.record_type == "expense")

    income_by_cat = {}
    expense_by_cat = {}
    for r in records:
        target = income_by_cat if r.record_type == "income" else expense_by_cat
        target[r.category] = target.get(r.category, 0) + r.amount

    return {
        "period": period or "monthly",
        "summary": {
            "total_income": round(income, 2),
            "total_expenses": round(expenses, 2),
            "net_profit": round(income - expenses, 2),
        },
        "by_category": {"income": income_by_cat, "expenses": expense_by_cat},
        "record_count": len(records),
    }


# ============================================================================
# 5. LEGAL DASHBOARD
# ============================================================================

@router.get("/legal/dashboard")
async def legal_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legal documents overview dashboard."""
    clinic_id = current_user.clinic_id
    now = datetime.utcnow()

    total = db.query(func.count(ClinicDocument.id)).filter(
        ClinicDocument.clinic_id == clinic_id
    ).scalar() or 0

    by_type = {}
    types = ["contract", "agreement", "nda", "consent_form", "policy", "license"]
    for t in types:
        count = db.query(func.count(ClinicDocument.id)).filter(
            ClinicDocument.clinic_id == clinic_id,
            ClinicDocument.document_type == t
        ).scalar() or 0
        by_type[t] = count

    by_status = {}
    statuses = ["draft", "active", "expired", "archived"]
    for s in statuses:
        count = db.query(func.count(ClinicDocument.id)).filter(
            ClinicDocument.clinic_id == clinic_id,
            ClinicDocument.status == s
        ).scalar() or 0
        by_status[s] = count

    # Expiring in 30 days
    expiring_soon = db.query(func.count(ClinicDocument.id)).filter(
        ClinicDocument.clinic_id == clinic_id,
        ClinicDocument.valid_until != None,
        ClinicDocument.valid_until <= now + timedelta(days=30),
        ClinicDocument.valid_until > now,
        ClinicDocument.status != "archived",
    ).scalar() or 0

    # Already expired
    expired = db.query(func.count(ClinicDocument.id)).filter(
        ClinicDocument.clinic_id == clinic_id,
        ClinicDocument.valid_until != None,
        ClinicDocument.valid_until < now,
        ClinicDocument.status == "active",
    ).scalar() or 0

    return {
        "total_documents": total,
        "by_type": by_type,
        "by_status": by_status,
        "expiring_in_30_days": expiring_soon,
        "expired_but_active": expired,
    }
