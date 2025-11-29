# app/main.py
import os
import uuid
import csv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from . import models, schemas, crud, utils
from .database import engine, SessionLocal
from .database import Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Importer (SQLite version)")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Upload CSV and process synchronously (but chunked)
@app.post("/upload", status_code=202)
async def upload_csv(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Save uploaded file to a temp location
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.csv")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create a task id for progress tracking
    task_id = utils.create_task_id()
    utils.set_progress(task_id, 0.0, "started", "File uploaded, starting import")

    # Process CSV in the same request but in chunks to avoid blowing memory
    # NOTE: For very large files this may still be slow — but fine for testing.
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            reader = csv.DictReader(fh)
            # Count total if possible (cheap for smaller files)
            total = 0
            # We try to compute total lines; if file is huge this may be slow, but fine for testing.
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as count_f:
                    total = sum(1 for _ in count_f) - 1
            except Exception:
                total = 0

            batch = []
            batch_size = 1000  # tuneable
            processed = 0
            utils.set_progress(task_id, 1.0, "parsing", "Parsing CSV and preparing batches")
            for row in reader:
                batch.append(row)
                if len(batch) >= batch_size:
                    # process batch in a DB session
                    db = SessionLocal()
                    try:
                        for r in batch:
                            try:
                                crud.create_or_update_by_sku(db, r)
                            except Exception:
                                # skip invalid rows
                                continue
                        db.close()
                    finally:
                        if db:
                            db.close()
                    processed += len(batch)
                    batch = []
                    progress = (processed / total * 100) if total else 0.0
                    utils.set_progress(task_id, progress, "importing", f"Processed {processed} rows")
            # last batch
            if batch:
                db = SessionLocal()
                try:
                    for r in batch:
                        try:
                            crud.create_or_update_by_sku(db, r)
                        except Exception:
                            continue
                finally:
                    db.close()
                processed += len(batch)
                progress = (processed / total * 100) if total else 100.0
                utils.set_progress(task_id, progress, "importing", f"Processed {processed} rows")

        utils.set_progress(task_id, 100.0, "completed", f"Import complete: {processed} rows")
    except Exception as e:
        utils.set_progress(task_id, 0.0, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return {"task_id": task_id, "message": "Import completed (synchronous run)"}


# Progress endpoint
@app.get("/progress/{task_id}", response_model=schemas.ProgressOut)
def get_progress(task_id: str):
    data = utils.get_progress(task_id)
    # Ensure fields expected by the frontend
    return JSONResponse(content={
        "task_id": data.get("task_id"),
        "status": data.get("status"),
        "progress": float(data.get("progress", 0.0)),
        "message": data.get("message", "")
    })


# PRODUCT endpoints
@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(skip: int = 0, limit: int = 50,
                  sku: Optional[str] = None, name: Optional[str] = None,
                  active: Optional[bool] = None,
                  db: Session = Depends(get_db)):
    filters = {}
    if sku:
        filters["sku"] = sku
    if name:
        filters["name"] = name
    if active is not None:
        filters["active"] = active
    res = crud.list_products(db, skip=skip, limit=limit, filters=filters)
    return res

@app.post("/products", response_model=schemas.ProductOut)
def create_product(prod: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = crud.get_product_by_sku(db, prod.sku)
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists.")
    p = crud.create_product(db, prod)
    return p

@app.put("/products/{sku}", response_model=schemas.ProductOut)
def update_product(sku: str, updates: schemas.ProductUpdate, db: Session = Depends(get_db)):
    existing = crud.get_product_by_sku(db, sku)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    p = crud.update_product(db, existing, updates)
    return p

@app.delete("/products/{sku}", status_code=204)
def delete_product(sku: str, db: Session = Depends(get_db)):
    existing = crud.get_product_by_sku(db, sku)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.delete_product(db, existing)
    return JSONResponse(status_code=204, content={"detail": "deleted"})

@app.delete("/products", status_code=200)
def delete_all_products(confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="You must pass ?confirm=true to delete all products.")
    crud.bulk_delete_all(db)
    return {"detail": "All products deleted"}


# WEBHOOK endpoints
@app.post("/webhooks", response_model=schemas.WebhookOut)
def add_webhook(payload: schemas.WebhookCreate, db: Session = Depends(get_db)):
    w = crud.create_webhook(db, payload.url, payload.event, payload.enabled)
    return w

@app.get("/webhooks", response_model=List[schemas.WebhookOut])
def get_webhooks(db: Session = Depends(get_db)):
    return crud.list_webhooks(db)

@app.delete("/webhooks/{webhook_id}", status_code=204)
def remove_webhook(webhook_id: int, db: Session = Depends(get_db)):
    w = crud.get_webhook(db, webhook_id)
    if not w:
        raise HTTPException(status_code=404, detail="Webhook not found")
    crud.delete_webhook(db, webhook_id)
    return JSONResponse(status_code=204, content={"detail": "deleted"})

@app.post("/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    w = crud.get_webhook(db, webhook_id)
    if not w:
        raise HTTPException(status_code=404, detail="Webhook not found")
    payload = {"event": w.event, "sample": {"message": "test"}}
    import requests
    try:
        resp = requests.post(w.url, json=payload, timeout=10)
        return {"status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
