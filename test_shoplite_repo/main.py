from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="ShopLite API", debug=True)

class OrderUpdate(BaseModel):
    shipping_address: str

def get_current_user():
    return {"user_id": 1, "role": "buyer"}

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: int, user = Depends(get_current_user)):
    return {"order_id": order_id, "user_id": user["user_id"], "status": "active"}

@app.patch("/api/v1/orders/{order_id}")
def update_order(order_id: int, data: OrderUpdate):
    return {"order_id": order_id, "status": "updated", "new_address": data.shipping_address}
