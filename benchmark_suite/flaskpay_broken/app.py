from flask import Flask
app = Flask(__name__)

class Payment(object):
    table = "payments"
    customer_id = 123
    amount = 50.0

@app.route("/api/v1/payments/<payment_id>")
def get_payment(payment_id):
    return payment_id

@app.route("/api/v1/payments/refund", methods=["POST"])
def refund_payment():
    return "ok"

@app.route("/api/v1/experimental/draft")
def broken_draft(param: int
    return param
