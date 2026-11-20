import os
import sys
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

app = FastAPI(
    title="ShopLite Vulnerable E-Commerce API",
    version="1.0.0",
    description="Live benchmark sandbox for AegisTrace Multi-Agent security assessment."
)

orders_db: Dict[int, Dict[str, Any]] = {
    100: {"id": 100, "user_id": 1, "owner": "alice", "shipping_address": "12 Nile St, Alexandria", "status": "pending", "total": 149.99},
    200: {"id": 200, "user_id": 2, "owner": "bob", "shipping_address": "45 Pyramids Rd, Giza", "status": "shipped", "total": 89.50}
}

transfers_db: Dict[int, Dict[str, Any]] = {
    100: {"id": 100, "transfer_id": 100, "user_id": 1, "owner": "alice", "amount": 5000.0, "status": "pending", "recipient": "bob"},
    200: {"id": 200, "transfer_id": 200, "user_id": 2, "owner": "bob", "amount": 1200.0, "status": "completed", "recipient": "charlie"}
}

prescriptions_db: Dict[int, Dict[str, Any]] = {
    100: {"id": 100, "rx_id": 100, "user_id": 1, "patient": "alice", "medication": "Amoxicillin", "dosage": "250mg", "status": "active"},
    200: {"id": 200, "rx_id": 200, "user_id": 2, "patient": "bob", "medication": "Metformin", "dosage": "500mg", "status": "active"}
}

users_db: Dict[str, Dict[str, Any]] = {
    "buyer_a": {"user_id": 1, "username": "alice", "role": "customer"},
    "buyer_b": {"user_id": 2, "username": "bob", "role": "customer"},
    "admin": {"user_id": 99, "username": "admin", "role": "administrator"}
}

class OrderUpdate(BaseModel):
    shipping_address: Optional[str] = None
    status: Optional[str] = None

class TransferUpdate(BaseModel):
    status: Optional[str] = None
    amount: Optional[float] = None

class PrescriptionUpdate(BaseModel):
    dosage: Optional[str] = None
    status: Optional[str] = None

class OrderCreate(BaseModel):
    shipping_address: str
    items: Optional[list] = None

def get_current_user(
    x_testing_identity: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    ident = (x_testing_identity or "").lower()
    if "buyer_b" in ident or "auditor_2" in ident or "patient_b" in ident:
        return users_db.get("buyer_b", {"user_id": 2, "username": "bob", "role": "customer"})
    if "admin" in ident:
        return users_db.get("admin", {"user_id": 99, "username": "admin", "role": "administrator"})
    return users_db.get("buyer_a", {"user_id": 1, "username": "alice", "role": "customer"})

@app.get("/")
def root():
    return {
        "app": "ShopLite Vulnerable E-Commerce API",
        "version": "1.0.0",
        "status": "online",
        "vulnerability_hint": "BOLA / IDOR on PATCH /api/v1/orders/{order_id}",
        "endpoints": [
            "/api/v1/orders/{order_id}",
            "/api/v1/orders",
            "/api/v1/admin/dashboard",
            "/openapi.json"
        ]
    }

@app.get("/api/v1/orders")
def list_orders(current_user = Depends(get_current_user)):
    return list(orders_db.values())

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: int, current_user = Depends(get_current_user)):
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.patch("/api/v1/orders/{order_id}")
def update_order(order_id: int, payload: OrderUpdate, current_user = Depends(get_current_user)):
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.shipping_address:
        order["shipping_address"] = payload.shipping_address
    if payload.status:
        order["status"] = payload.status
    return {"id": order_id, "status": "updated", "order": order}

@app.post("/api/v1/orders")
def create_order(payload: OrderCreate, current_user = Depends(get_current_user)):
    new_id = max(orders_db.keys()) + 1
    new_order = {
        "id": new_id,
        "user_id": current_user["user_id"],
        "owner": current_user["username"],
        "shipping_address": payload.shipping_address,
        "status": "created"
    }
    orders_db[new_id] = new_order
    return new_order

@app.get("/api/v1/admin/dashboard")
def admin_dashboard(current_user = Depends(get_current_user)):
    if current_user.get("role") != "administrator":
        raise HTTPException(status_code=403, detail="Admin role required")
    return {"total_orders": len(orders_db), "system_status": "healthy"}

@app.get("/api/v1/transfers/{transfer_id}")
def get_transfer(transfer_id: int, current_user = Depends(get_current_user)):
    t = transfers_db.get(transfer_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return t

@app.patch("/api/v1/transfers/{transfer_id}")
def update_transfer(transfer_id: int, payload: TransferUpdate, current_user = Depends(get_current_user)):
    t = transfers_db.get(transfer_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if payload.status:
        t["status"] = payload.status
    if payload.amount:
        t["amount"] = payload.amount
    return {"id": transfer_id, "status": "updated", "transfer": t}

@app.get("/api/v1/prescriptions/{rx_id}")
def get_prescription(rx_id: int, current_user = Depends(get_current_user)):
    rx = prescriptions_db.get(rx_id)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return rx

@app.patch("/api/v1/prescriptions/{rx_id}")
def update_prescription(rx_id: int, payload: PrescriptionUpdate, current_user = Depends(get_current_user)):
    rx = prescriptions_db.get(rx_id)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if payload.dosage:
        rx["dosage"] = payload.dosage
    if payload.status:
        rx["status"] = payload.status
    return {"id": rx_id, "status": "updated", "prescription": rx}
