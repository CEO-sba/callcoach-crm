"""
CallCoach CRM - Operations Router
Clinic operations including billing, inventory, and patient records.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    Invoice,
    InventoryItem,
    PatientRecord,
    PatientProcedureHistory
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/operations", tags=["operations"])


# ===== INVOICING =====

@router.post("/invoices")
async def create_invoice(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new invoice.
    Expected data: {
        "patient_id": "patient_id",
        "description": "Invoice description",
        "amount": 1000.00,
        "invoice_date": "2024-03-15",
        "due_date": "2024-04-15",
        "items": [{"name": "service", "amount": 500}]
    }
    """
    required_fields = ["patient_id", "amount"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    invoice = Invoice(
        clinic_id=current_user.clinic_id,
        patient_id=data["patient_id"],
        description=data.get("description", ""),
        amount=data["amount"],
        invoice_date=data.get("invoice_date", datetime.utcnow().date()),
        due_date=data.get("due_date"),
        items=data.get("items", []),
        status="draft"
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "status": "created",
        "invoice_id": invoice.id,
        "invoice": invoice
    }


@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    patient_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List invoices with optional filters."""
    query = db.query(Invoice).filter(
        Invoice.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(Invoice.status == status)
    if patient_id:
        query = query.filter(Invoice.patient_id == patient_id)

    invoices = query.order_by(
        Invoice.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "invoices": invoices,
        "total": query.count()
    }


@router.put("/invoices/{invoice_id}")
async def update_invoice_status(
    invoice_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update invoice status (draft, sent, paid, overdue)."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.clinic_id == current_user.clinic_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if "status" in data:
        invoice.status = data["status"]

    invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)

    return {
        "status": "updated",
        "invoice_id": invoice.id,
        "invoice": invoice
    }


# ===== INVENTORY =====

@router.get("/inventory")
async def list_inventory(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List inventory items."""
    items = db.query(InventoryItem).filter(
        InventoryItem.clinic_id == current_user.clinic_id
    ).order_by(
        InventoryItem.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "items": items,
        "total": db.query(InventoryItem).filter(
            InventoryItem.clinic_id == current_user.clinic_id
        ).count()
    }


@router.post("/inventory")
async def add_inventory_item(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an inventory item.
    Expected data: {
        "name": "Item Name",
        "category": "Supplies",
        "quantity": 100,
        "reorder_level": 20,
        "unit_cost": 10.00,
        "supplier": "Supplier Name"
    }
    """
    required_fields = ["name", "quantity"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    item = InventoryItem(
        clinic_id=current_user.clinic_id,
        name=data["name"],
        category=data.get("category", ""),
        quantity=data["quantity"],
        reorder_level=data.get("reorder_level"),
        unit_cost=data.get("unit_cost"),
        supplier=data.get("supplier")
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "status": "created",
        "item_id": item.id,
        "item": item
    }


@router.put("/inventory/{item_id}")
async def update_stock(
    item_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update inventory item stock quantity."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "quantity" in data:
        item.quantity = data["quantity"]

    update_data = data
    for field, value in update_data.items():
        if hasattr(item, field) and field != "id":
            setattr(item, field, value)

    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return {
        "status": "updated",
        "item_id": item.id,
        "item": item
    }


# ===== PATIENT RECORDS =====

@router.get("/patients")
async def list_patients(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List patient records with optional search."""
    query = db.query(PatientRecord).filter(
        PatientRecord.clinic_id == current_user.clinic_id
    )

    if search:
        query = query.filter(
            (PatientRecord.name.ilike(f"%{search}%")) |
            (PatientRecord.email.ilike(f"%{search}%")) |
            (PatientRecord.phone.ilike(f"%{search}%"))
        )

    patients = query.order_by(
        PatientRecord.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "patients": patients,
        "total": query.count()
    }


@router.post("/patients")
async def create_patient_record(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a patient record.
    Expected data: {
        "name": "Patient Name",
        "email": "email@example.com",
        "phone": "phone_number",
        "date_of_birth": "1990-01-01",
        "address": "Address",
        "medical_history": "Medical history notes"
    }
    """
    required_fields = ["name", "email"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    patient = PatientRecord(
        clinic_id=current_user.clinic_id,
        name=data["name"],
        email=data["email"],
        phone=data.get("phone"),
        date_of_birth=data.get("date_of_birth"),
        address=data.get("address"),
        medical_history=data.get("medical_history")
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return {
        "status": "created",
        "patient_id": patient.id,
        "patient": patient
    }


@router.put("/patients/{patient_id}")
async def update_patient_record(
    patient_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update patient record details."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(patient, field):
            setattr(patient, field, value)

    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)

    return {
        "status": "updated",
        "patient_id": patient.id,
        "patient": patient
    }


@router.get("/patients/{patient_id}/history")
async def get_patient_history(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patient's procedure history."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = db.query(PatientProcedureHistory).filter(
        PatientProcedureHistory.patient_id == patient_id
    ).order_by(
        PatientProcedureHistory.procedure_date.desc()
    ).all()

    return {
        "patient_id": patient_id,
        "patient": patient,
        "procedures": history,
        "total_procedures": len(history)
    }


# ===== OPERATIONS DASHBOARD =====

@router.get("/dashboard")
async def operations_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get operations overview stats."""
    clinic_id = current_user.clinic_id

    # Invoice stats
    total_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.clinic_id == clinic_id
    ).scalar() or 0

    paid_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status == "paid"
    ).scalar() or 0

    pending_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status.in_(["draft", "sent"])
    ).scalar() or 0

    # Total revenue
    total_revenue = db.query(func.sum(Invoice.amount)).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status == "paid"
    ).scalar() or 0

    # Inventory stats
    total_items = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id
    ).scalar() or 0

    low_stock_items = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.quantity <= InventoryItem.reorder_level
    ).scalar() or 0

    # Patient stats
    total_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    return {
        "invoicing": {
            "total_invoices": total_invoices,
            "paid": paid_invoices,
            "pending": pending_invoices,
            "total_revenue": float(total_revenue)
        },
        "inventory": {
            "total_items": total_items,
            "low_stock_items": low_stock_items
        },
        "patients": {
            "total_patients": total_patients
        }
    }
