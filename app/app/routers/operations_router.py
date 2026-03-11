"""
CallCoach CRM - Operations Router (v2.1)
Complete clinic operations: inventory management, patient records,
operational dashboard, AI-powered insights, and clinic analytics.
Invoicing is handled by legal_finance_router.py.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func, case, and_

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    InventoryItem,
    PatientRecord,
    PatientProcedureHistory,
    Invoice,
)
from app.services.operations_ai_coach import (
    analyze_inventory_health,
    analyze_patient_insights,
    generate_operations_report,
    ask_operations_coach,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/operations", tags=["operations"])


# =============================================================================
# 1. OPERATIONS DASHBOARD
# =============================================================================

@router.get("/dashboard")
async def operations_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Comprehensive operations overview with key metrics."""
    clinic_id = current_user.clinic_id

    # --- Inventory Stats ---
    total_items = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id
    ).scalar() or 0

    low_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock <= InventoryItem.min_stock_level,
        InventoryItem.current_stock > 0
    ).scalar() or 0

    out_of_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock == 0
    ).scalar() or 0

    inventory_value = db.query(
        func.sum(InventoryItem.current_stock * InventoryItem.unit_price)
    ).filter(InventoryItem.clinic_id == clinic_id).scalar() or 0

    # --- Patient Stats ---
    total_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_patients_30d = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.created_at >= thirty_days_ago
    ).scalar() or 0

    active_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.last_visit_at >= thirty_days_ago
    ).scalar() or 0

    total_patient_revenue = db.query(
        func.sum(PatientRecord.total_spent)
    ).filter(PatientRecord.clinic_id == clinic_id).scalar() or 0

    avg_revenue_per_patient = (
        float(total_patient_revenue) / total_patients if total_patients > 0 else 0
    )

    # --- Invoice Stats (read-only summary) ---
    total_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.clinic_id == clinic_id
    ).scalar() or 0

    pending_invoice_amount = db.query(func.sum(Invoice.total)).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status.in_(["draft", "sent", "overdue"])
    ).scalar() or 0

    collected_revenue = db.query(func.sum(Invoice.total)).filter(
        Invoice.clinic_id == clinic_id,
        Invoice.status == "paid"
    ).scalar() or 0

    # --- Procedure Stats ---
    total_procedures = db.query(func.count(PatientProcedureHistory.id)).filter(
        PatientProcedureHistory.clinic_id == clinic_id
    ).scalar() or 0

    procedures_30d = db.query(func.count(PatientProcedureHistory.id)).filter(
        PatientProcedureHistory.clinic_id == clinic_id,
        PatientProcedureHistory.procedure_date >= thirty_days_ago
    ).scalar() or 0

    return {
        "inventory": {
            "total_items": total_items,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "total_value": float(inventory_value)
        },
        "patients": {
            "total": total_patients,
            "new_last_30_days": new_patients_30d,
            "active_last_30_days": active_patients,
            "total_revenue": float(total_patient_revenue),
            "avg_revenue_per_patient": round(avg_revenue_per_patient, 2)
        },
        "invoicing": {
            "total_invoices": total_invoices,
            "pending_amount": float(pending_invoice_amount),
            "collected_revenue": float(collected_revenue)
        },
        "procedures": {
            "total_all_time": total_procedures,
            "last_30_days": procedures_30d
        }
    }


# =============================================================================
# 2. INVENTORY MANAGEMENT
# =============================================================================

@router.get("/inventory")
async def list_inventory(
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    low_stock_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List inventory items with filters."""
    query = db.query(InventoryItem).filter(
        InventoryItem.clinic_id == current_user.clinic_id
    )

    if category:
        query = query.filter(InventoryItem.category == category)
    if status:
        query = query.filter(InventoryItem.status == status)
    if search:
        query = query.filter(
            (InventoryItem.name.ilike(f"%{search}%")) |
            (InventoryItem.sku.ilike(f"%{search}%")) |
            (InventoryItem.supplier.ilike(f"%{search}%"))
        )
    if low_stock_only:
        query = query.filter(
            InventoryItem.current_stock <= InventoryItem.min_stock_level
        )

    total = query.count()
    items = query.order_by(
        InventoryItem.current_stock.asc()
    ).offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "sku": item.sku,
                "current_stock": item.current_stock,
                "min_stock_level": item.min_stock_level,
                "unit_price": item.unit_price,
                "supplier": item.supplier,
                "status": item.status,
                "last_restocked_at": item.last_restocked_at.isoformat() if item.last_restocked_at else None,
                "stock_value": item.current_stock * (item.unit_price or 0),
                "needs_restock": item.current_stock <= item.min_stock_level,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total
    }


@router.post("/inventory")
async def add_inventory_item(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new inventory item."""
    if "name" not in data or "category" not in data:
        raise HTTPException(status_code=400, detail="name and category are required")

    item = InventoryItem(
        clinic_id=current_user.clinic_id,
        name=data["name"],
        category=data["category"],
        sku=data.get("sku"),
        current_stock=data.get("current_stock", 0),
        min_stock_level=data.get("min_stock_level", 0),
        unit_price=data.get("unit_price", 0),
        supplier=data.get("supplier"),
        status=_compute_stock_status(
            data.get("current_stock", 0),
            data.get("min_stock_level", 0)
        )
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {"status": "created", "item_id": item.id}


@router.get("/inventory/{item_id}")
async def get_inventory_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get inventory item detail."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "sku": item.sku,
        "current_stock": item.current_stock,
        "min_stock_level": item.min_stock_level,
        "unit_price": item.unit_price,
        "supplier": item.supplier,
        "status": item.status,
        "last_restocked_at": item.last_restocked_at.isoformat() if item.last_restocked_at else None,
        "stock_value": item.current_stock * (item.unit_price or 0),
        "needs_restock": item.current_stock <= item.min_stock_level,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.put("/inventory/{item_id}")
async def update_inventory_item(
    item_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update inventory item details and stock."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    allowed_fields = [
        "name", "category", "sku", "current_stock", "min_stock_level",
        "unit_price", "supplier"
    ]
    for field in allowed_fields:
        if field in data:
            setattr(item, field, data[field])

    # Auto-update status based on stock levels
    item.status = _compute_stock_status(item.current_stock, item.min_stock_level)

    db.commit()
    db.refresh(item)

    return {"status": "updated", "item_id": item.id}


@router.post("/inventory/{item_id}/restock")
async def restock_item(
    item_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restock an inventory item by adding quantity."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    quantity_added = data.get("quantity", 0)
    if quantity_added <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")

    item.current_stock += quantity_added
    item.last_restocked_at = datetime.utcnow()
    item.status = _compute_stock_status(item.current_stock, item.min_stock_level)

    db.commit()
    db.refresh(item)

    return {
        "status": "restocked",
        "item_id": item.id,
        "quantity_added": quantity_added,
        "new_stock": item.current_stock
    }


@router.post("/inventory/{item_id}/consume")
async def consume_item(
    item_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reduce stock when item is used."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    quantity_used = data.get("quantity", 0)
    if quantity_used <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    if quantity_used > item.current_stock:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    item.current_stock -= quantity_used
    item.status = _compute_stock_status(item.current_stock, item.min_stock_level)

    db.commit()
    db.refresh(item)

    return {
        "status": "consumed",
        "item_id": item.id,
        "quantity_used": quantity_used,
        "remaining_stock": item.current_stock
    }


@router.delete("/inventory/{item_id}")
async def delete_inventory_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an inventory item."""
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.clinic_id == current_user.clinic_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    return {"status": "deleted", "item_id": item_id}


@router.get("/inventory/alerts/low-stock")
async def low_stock_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get items that need restocking."""
    items = db.query(InventoryItem).filter(
        InventoryItem.clinic_id == current_user.clinic_id,
        InventoryItem.current_stock <= InventoryItem.min_stock_level
    ).order_by(
        InventoryItem.current_stock.asc()
    ).all()

    return {
        "alerts": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_stock": item.current_stock,
                "min_stock_level": item.min_stock_level,
                "deficit": item.min_stock_level - item.current_stock,
                "supplier": item.supplier,
                "unit_price": item.unit_price,
                "estimated_restock_cost": (item.min_stock_level - item.current_stock) * (item.unit_price or 0)
            }
            for item in items
        ],
        "total_alerts": len(items)
    }


# =============================================================================
# 3. PATIENT RECORDS
# =============================================================================

@router.get("/patients")
async def list_patients(
    search: Optional[str] = None,
    gender: Optional[str] = None,
    min_spent: Optional[float] = None,
    sort_by: Optional[str] = "created_at",
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List patient records with filters."""
    query = db.query(PatientRecord).filter(
        PatientRecord.clinic_id == current_user.clinic_id
    )

    if search:
        query = query.filter(
            (PatientRecord.name.ilike(f"%{search}%")) |
            (PatientRecord.email.ilike(f"%{search}%")) |
            (PatientRecord.phone.ilike(f"%{search}%"))
        )
    if gender:
        query = query.filter(PatientRecord.gender == gender)
    if min_spent is not None:
        query = query.filter(PatientRecord.total_spent >= min_spent)

    # Sort
    sort_options = {
        "created_at": PatientRecord.created_at.desc(),
        "name": PatientRecord.name.asc(),
        "total_spent": PatientRecord.total_spent.desc(),
        "last_visit": PatientRecord.last_visit_at.desc(),
        "visits": PatientRecord.visits_count.desc(),
    }
    order = sort_options.get(sort_by, PatientRecord.created_at.desc())

    total = query.count()
    patients = query.order_by(order).offset(skip).limit(limit).all()

    return {
        "patients": [
            {
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "email": p.email,
                "gender": p.gender,
                "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
                "total_spent": p.total_spent,
                "visits_count": p.visits_count,
                "last_visit_at": p.last_visit_at.isoformat() if p.last_visit_at else None,
                "lead_id": p.lead_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in patients
        ],
        "total": total
    }


@router.post("/patients")
async def create_patient_record(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new patient record."""
    if "name" not in data:
        raise HTTPException(status_code=400, detail="name is required")

    patient = PatientRecord(
        clinic_id=current_user.clinic_id,
        lead_id=data.get("lead_id"),
        name=data["name"],
        phone=data.get("phone"),
        email=data.get("email"),
        date_of_birth=data.get("date_of_birth"),
        gender=data.get("gender"),
        blood_group=data.get("blood_group"),
        allergies=data.get("allergies", []),
        medical_history=data.get("medical_history", {}),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return {"status": "created", "patient_id": patient.id}


@router.get("/patients/{patient_id}")
async def get_patient_detail(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full patient record with procedure history."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Procedure history
    procedures = db.query(PatientProcedureHistory).filter(
        PatientProcedureHistory.patient_id == patient_id
    ).order_by(
        PatientProcedureHistory.procedure_date.desc()
    ).all()

    # Invoices for this patient
    invoices = db.query(Invoice).filter(
        Invoice.clinic_id == current_user.clinic_id,
        Invoice.patient_name == patient.name
    ).order_by(Invoice.created_at.desc()).limit(20).all()

    return {
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "phone": patient.phone,
            "email": patient.email,
            "gender": patient.gender,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "medical_history": patient.medical_history,
            "procedures_done": patient.procedures_done,
            "consent_forms": patient.consent_forms,
            "total_spent": patient.total_spent,
            "visits_count": patient.visits_count,
            "last_visit_at": patient.last_visit_at.isoformat() if patient.last_visit_at else None,
            "lead_id": patient.lead_id,
            "created_at": patient.created_at.isoformat() if patient.created_at else None,
            "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
        },
        "procedure_history": [
            {
                "id": proc.id,
                "procedure_name": proc.procedure_name,
                "procedure_date": proc.procedure_date.isoformat() if proc.procedure_date else None,
                "doctor_name": proc.doctor_name,
                "notes": proc.notes,
                "cost": proc.cost,
                "outcome": proc.outcome,
                "before_photos": proc.before_photos,
                "after_photos": proc.after_photos,
            }
            for proc in procedures
        ],
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "total": inv.total,
                "status": inv.status,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
            }
            for inv in invoices
        ],
        "total_procedures": len(procedures)
    }


@router.put("/patients/{patient_id}")
async def update_patient_record(
    patient_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update patient record."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    allowed_fields = [
        "name", "phone", "email", "date_of_birth", "gender",
        "blood_group", "allergies", "medical_history",
        "procedures_done", "consent_forms", "lead_id"
    ]
    for field in allowed_fields:
        if field in data:
            setattr(patient, field, data[field])

    db.commit()
    db.refresh(patient)

    return {"status": "updated", "patient_id": patient.id}


@router.post("/patients/{patient_id}/visit")
async def record_patient_visit(
    patient_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a patient visit and optionally add a procedure."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update visit stats
    patient.visits_count = (patient.visits_count or 0) + 1
    patient.last_visit_at = datetime.utcnow()

    # Add procedure if provided
    procedure_id = None
    if data.get("procedure_name"):
        cost = data.get("cost", 0)
        proc = PatientProcedureHistory(
            patient_id=patient_id,
            clinic_id=current_user.clinic_id,
            procedure_name=data["procedure_name"],
            procedure_date=data.get("procedure_date", datetime.utcnow()),
            doctor_name=data.get("doctor_name"),
            notes=data.get("notes"),
            cost=cost,
            outcome=data.get("outcome"),
            before_photos=data.get("before_photos", []),
            after_photos=data.get("after_photos", []),
        )
        db.add(proc)
        db.flush()
        procedure_id = proc.id

        # Update total spent
        patient.total_spent = (patient.total_spent or 0) + cost

        # Append to procedures_done list
        existing = patient.procedures_done or []
        existing.append({
            "procedure": data["procedure_name"],
            "date": str(datetime.utcnow().date()),
            "doctor": data.get("doctor_name"),
            "cost": cost,
        })
        patient.procedures_done = existing

    if data.get("amount_paid"):
        patient.total_spent = (patient.total_spent or 0) + data["amount_paid"]

    db.commit()
    db.refresh(patient)

    result = {
        "status": "visit_recorded",
        "patient_id": patient.id,
        "visits_count": patient.visits_count,
        "total_spent": patient.total_spent,
    }
    if procedure_id:
        result["procedure_id"] = procedure_id

    return result


@router.delete("/patients/{patient_id}")
async def delete_patient_record(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a patient record."""
    patient = db.query(PatientRecord).filter(
        PatientRecord.id == patient_id,
        PatientRecord.clinic_id == current_user.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.delete(patient)
    db.commit()

    return {"status": "deleted", "patient_id": patient_id}


# =============================================================================
# 4. PROCEDURE HISTORY
# =============================================================================

@router.get("/procedures")
async def list_procedures(
    patient_id: Optional[str] = None,
    procedure_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all procedure records with filters."""
    query = db.query(PatientProcedureHistory).filter(
        PatientProcedureHistory.clinic_id == current_user.clinic_id
    )

    if patient_id:
        query = query.filter(PatientProcedureHistory.patient_id == patient_id)
    if procedure_name:
        query = query.filter(
            PatientProcedureHistory.procedure_name.ilike(f"%{procedure_name}%")
        )
    if doctor_name:
        query = query.filter(
            PatientProcedureHistory.doctor_name.ilike(f"%{doctor_name}%")
        )

    total = query.count()
    procedures = query.order_by(
        PatientProcedureHistory.procedure_date.desc()
    ).offset(skip).limit(limit).all()

    return {
        "procedures": [
            {
                "id": proc.id,
                "patient_id": proc.patient_id,
                "procedure_name": proc.procedure_name,
                "procedure_date": proc.procedure_date.isoformat() if proc.procedure_date else None,
                "doctor_name": proc.doctor_name,
                "notes": proc.notes,
                "cost": proc.cost,
                "outcome": proc.outcome,
                "before_photos": proc.before_photos,
                "after_photos": proc.after_photos,
                "created_at": proc.created_at.isoformat() if proc.created_at else None,
            }
            for proc in procedures
        ],
        "total": total
    }


@router.get("/procedures/analytics")
async def procedure_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Procedure popularity and revenue analytics."""
    clinic_id = current_user.clinic_id

    # Most popular procedures
    popular = db.query(
        PatientProcedureHistory.procedure_name,
        func.count(PatientProcedureHistory.id).label("count"),
        func.sum(PatientProcedureHistory.cost).label("total_revenue"),
        func.avg(PatientProcedureHistory.cost).label("avg_cost")
    ).filter(
        PatientProcedureHistory.clinic_id == clinic_id
    ).group_by(
        PatientProcedureHistory.procedure_name
    ).order_by(
        func.count(PatientProcedureHistory.id).desc()
    ).limit(20).all()

    # Top doctors by procedure count
    top_doctors = db.query(
        PatientProcedureHistory.doctor_name,
        func.count(PatientProcedureHistory.id).label("count"),
        func.sum(PatientProcedureHistory.cost).label("total_revenue")
    ).filter(
        PatientProcedureHistory.clinic_id == clinic_id,
        PatientProcedureHistory.doctor_name.isnot(None)
    ).group_by(
        PatientProcedureHistory.doctor_name
    ).order_by(
        func.count(PatientProcedureHistory.id).desc()
    ).limit(10).all()

    return {
        "popular_procedures": [
            {
                "procedure_name": p.procedure_name,
                "count": p.count,
                "total_revenue": float(p.total_revenue or 0),
                "avg_cost": round(float(p.avg_cost or 0), 2)
            }
            for p in popular
        ],
        "top_doctors": [
            {
                "doctor_name": d.doctor_name,
                "procedures_done": d.count,
                "total_revenue": float(d.total_revenue or 0)
            }
            for d in top_doctors
        ]
    }


# =============================================================================
# 5. AI OPERATIONS COACH
# =============================================================================

@router.post("/ai/inventory-analysis")
async def ai_inventory_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI-powered inventory health analysis."""
    items = db.query(InventoryItem).filter(
        InventoryItem.clinic_id == current_user.clinic_id
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="No inventory items found")

    inventory_data = [
        {
            "name": item.name,
            "category": item.category,
            "current_stock": item.current_stock,
            "min_stock_level": item.min_stock_level,
            "unit_price": item.unit_price,
            "supplier": item.supplier,
            "status": item.status,
            "last_restocked": item.last_restocked_at.isoformat() if item.last_restocked_at else None,
        }
        for item in items
    ]

    analysis = await analyze_inventory_health(
        inventory_data=inventory_data,
        additional_context=f"Total items: {len(items)}"
    )

    return {"analysis": analysis}


@router.post("/ai/patient-insights")
async def ai_patient_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI-powered patient base analysis and growth insights."""
    clinic_id = current_user.clinic_id

    patients = db.query(PatientRecord).filter(
        PatientRecord.clinic_id == clinic_id
    ).order_by(PatientRecord.total_spent.desc()).limit(100).all()

    if not patients:
        raise HTTPException(status_code=404, detail="No patient records found")

    patient_data = [
        {
            "name_initial": p.name[:1] + "***" if p.name else "Unknown",
            "gender": p.gender,
            "total_spent": p.total_spent,
            "visits_count": p.visits_count,
            "last_visit": p.last_visit_at.isoformat() if p.last_visit_at else None,
            "procedures_count": len(p.procedures_done) if p.procedures_done else 0,
            "created": p.created_at.isoformat() if p.created_at else None,
        }
        for p in patients
    ]

    # Procedure stats
    procedure_stats_raw = db.query(
        PatientProcedureHistory.procedure_name,
        func.count(PatientProcedureHistory.id).label("count"),
        func.sum(PatientProcedureHistory.cost).label("revenue")
    ).filter(
        PatientProcedureHistory.clinic_id == clinic_id
    ).group_by(
        PatientProcedureHistory.procedure_name
    ).all()

    procedure_stats = {
        row.procedure_name: {
            "count": row.count,
            "revenue": float(row.revenue or 0)
        }
        for row in procedure_stats_raw
    }

    analysis = await analyze_patient_insights(
        patient_data=patient_data,
        procedure_stats=procedure_stats
    )

    return {"analysis": analysis}


@router.post("/ai/operations-report")
async def ai_operations_report(
    data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered comprehensive operations report."""
    clinic_id = current_user.clinic_id
    data = data or {}
    period = data.get("period", "this_month")

    # Build dashboard data
    total_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    total_revenue = db.query(func.sum(PatientRecord.total_spent)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    total_items = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id
    ).scalar() or 0

    low_stock_count = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock <= InventoryItem.min_stock_level
    ).scalar() or 0

    total_procedures = db.query(func.count(PatientProcedureHistory.id)).filter(
        PatientProcedureHistory.clinic_id == clinic_id
    ).scalar() or 0

    dashboard_data = {
        "total_patients": total_patients,
        "total_revenue": float(total_revenue),
        "total_inventory_items": total_items,
        "low_stock_items": low_stock_count,
        "total_procedures": total_procedures,
    }

    report = await generate_operations_report(
        dashboard_data=dashboard_data,
        period=period
    )

    return {"report": report}


@router.post("/ai/coach")
async def operations_coach_qa(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask the operations AI coach any question."""
    question = data.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    # Build context from clinic data
    clinic_id = current_user.clinic_id
    total_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    total_inventory = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id
    ).scalar() or 0

    context = {
        "total_patients": total_patients,
        "total_inventory_items": total_inventory,
        "user_role": "clinic_operations",
        **(data.get("context", {}))
    }

    response = await ask_operations_coach(question=question, context=context)

    return {"response": response}


# =============================================================================
# 6. PATIENT ANALYTICS
# =============================================================================

@router.get("/analytics/patients")
async def patient_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient analytics: segments, revenue distribution, retention."""
    clinic_id = current_user.clinic_id

    # Gender distribution
    gender_dist = db.query(
        PatientRecord.gender,
        func.count(PatientRecord.id).label("count")
    ).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.gender.isnot(None)
    ).group_by(PatientRecord.gender).all()

    # Revenue segments
    total_patients = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id
    ).scalar() or 0

    high_value = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.total_spent >= 50000
    ).scalar() or 0

    medium_value = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.total_spent >= 10000,
        PatientRecord.total_spent < 50000
    ).scalar() or 0

    low_value = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.total_spent < 10000
    ).scalar() or 0

    # Visit frequency
    frequent = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.visits_count >= 5
    ).scalar() or 0

    regular = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.visits_count >= 2,
        PatientRecord.visits_count < 5
    ).scalar() or 0

    one_time = db.query(func.count(PatientRecord.id)).filter(
        PatientRecord.clinic_id == clinic_id,
        PatientRecord.visits_count <= 1
    ).scalar() or 0

    # Top spenders
    top_spenders = db.query(PatientRecord).filter(
        PatientRecord.clinic_id == clinic_id
    ).order_by(
        PatientRecord.total_spent.desc()
    ).limit(10).all()

    return {
        "total_patients": total_patients,
        "gender_distribution": [
            {"gender": g.gender or "unknown", "count": g.count}
            for g in gender_dist
        ],
        "revenue_segments": {
            "high_value_50k_plus": high_value,
            "medium_value_10k_50k": medium_value,
            "low_value_under_10k": low_value
        },
        "visit_frequency": {
            "frequent_5_plus": frequent,
            "regular_2_4": regular,
            "one_time": one_time
        },
        "top_spenders": [
            {
                "name": p.name,
                "total_spent": p.total_spent,
                "visits_count": p.visits_count,
                "last_visit": p.last_visit_at.isoformat() if p.last_visit_at else None
            }
            for p in top_spenders
        ]
    }


@router.get("/analytics/inventory")
async def inventory_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inventory analytics: category breakdown, value distribution, stock health."""
    clinic_id = current_user.clinic_id

    # Category breakdown
    category_stats = db.query(
        InventoryItem.category,
        func.count(InventoryItem.id).label("count"),
        func.sum(InventoryItem.current_stock * InventoryItem.unit_price).label("value")
    ).filter(
        InventoryItem.clinic_id == clinic_id
    ).group_by(InventoryItem.category).all()

    # Stock health
    in_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock > InventoryItem.min_stock_level
    ).scalar() or 0

    low_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock <= InventoryItem.min_stock_level,
        InventoryItem.current_stock > 0
    ).scalar() or 0

    out_of_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.clinic_id == clinic_id,
        InventoryItem.current_stock == 0
    ).scalar() or 0

    total_value = db.query(
        func.sum(InventoryItem.current_stock * InventoryItem.unit_price)
    ).filter(InventoryItem.clinic_id == clinic_id).scalar() or 0

    return {
        "category_breakdown": [
            {
                "category": cs.category,
                "item_count": cs.count,
                "total_value": float(cs.value or 0)
            }
            for cs in category_stats
        ],
        "stock_health": {
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock
        },
        "total_inventory_value": float(total_value)
    }


# =============================================================================
# HELPERS
# =============================================================================

def _compute_stock_status(current_stock: int, min_stock_level: int) -> str:
    """Compute stock status from levels."""
    if current_stock == 0:
        return "out_of_stock"
    elif current_stock <= min_stock_level:
        return "low_stock"
    else:
        return "in_stock"
