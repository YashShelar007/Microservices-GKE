# order-service/app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/orders", methods=["GET"])
def get_orders():
    # Dummy data
    return jsonify({"orders": [{"id": 1, "item": "widget"}, {"id": 2, "item": "gadget"}]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
