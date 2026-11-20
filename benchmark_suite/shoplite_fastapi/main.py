from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="ShopLite API")

class OrderCreate(BaseModel):
    shipping_address: str

def get_current_user():
    return {"user_id": 1, "role": "buyer"}

def require_admin():
    return {"user_id": 99, "role": "admin"}

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: int, user = Depends(get_current_user)):
    return {"order_id": order_id}

@app.patch("/api/v1/orders/{order_id}")
def update_order(order_id: int):
    return {"order_id": order_id}

@app.post("/api/v1/orders")
def create_order(data: OrderCreate, user = Depends(get_current_user)):
    return {"status": "created"}

@app.get("/api/v1/admin/dashboard")
def admin_dashboard(admin = Depends(require_admin)):
    return {"stats": 42}

@app.post("/api/v1/auth/login")
def login():
    return {"token": "xyz"}
