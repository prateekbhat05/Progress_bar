# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import Optional, List, Dict

# PRODUCT CRUD

def get_product_by_sku(db: Session, sku: str) -> Optional[models.Product]:
    if not sku:
        return None
    return db.query(models.Product).filter(func.lower(models.Product.sku) == sku.lower()).first()

def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    db_obj = models.Product(
        sku=product.sku,
        name=product.name,
        description=product.description,
        price=product.price,
        active=product.active if product.active is not None else True
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_product(db: Session, db_obj: models.Product, updates: schemas.ProductUpdate) -> models.Product:
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def create_or_update_by_sku(db: Session, row: Dict) -> models.Product:
    """
    Accepts a dict-like row from CSV. Tries to find SKU (case-insensitive).
    Updates existing product or creates a new one.
    """
    # Try common header names
    sku = row.get("sku") or row.get("SKU") or row.get("Sku")
    if not sku:
        raise ValueError("SKU required")

    name = row.get("name") or row.get("Name") or None
    description = row.get("description") or row.get("Description") or None
    price = row.get("price") or row.get("Price") or None
    # optional active field in CSV (if present)
    active_raw = row.get("active") or row.get("Active") or None
    active = None
    if active_raw is not None:
        if str(active_raw).strip().lower() in ("0", "false", "no", "n"):
            active = False
        else:
            active = True

    existing = get_product_by_sku(db, sku)
    if existing:
        if name is not None:
            existing.name = name
        if description is not None:
            existing.description = description
        if price is not None:
            existing.price = price
        if active is not None:
            existing.active = active
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new = models.Product(
            sku=sku,
            name=name,
            description=description,
            price=price,
            active=active if active is not None else True
        )
        db.add(new)
        db.commit()
        db.refresh(new)
        return new

def list_products(db: Session, skip: int = 0, limit: int = 50, filters: dict = None) -> List[models.Product]:
    q = db.query(models.Product)
    if filters:
        if "sku" in filters and filters["sku"]:
            q = q.filter(func.lower(models.Product.sku).like(f"%{filters['sku'].lower()}%"))
        if "name" in filters and filters["name"]:
            q = q.filter(models.Product.name.ilike(f"%{filters['name']}%"))
        if "active" in filters and filters["active"] is not None:
            q = q.filter(models.Product.active == filters["active"])
    return q.order_by(models.Product.id.desc()).offset(skip).limit(limit).all()

def delete_product(db: Session, product: models.Product):
    db.delete(product)
    db.commit()

def bulk_delete_all(db: Session):
    db.query(models.Product).delete()
    db.commit()

# WEBHOOK CRUD (DB-backed)
def create_webhook(db: Session, url: str, event: str, enabled: bool = True):
    w = models.Webhook(url=url, event=event, enabled=enabled)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w

def list_webhooks(db: Session):
    return db.query(models.Webhook).order_by(models.Webhook.id).all()

def get_webhook(db: Session, webhook_id: int):
    return db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()

def delete_webhook(db: Session, webhook_id: int):
    w = get_webhook(db, webhook_id)
    if w:
        db.delete(w)
        db.commit()
