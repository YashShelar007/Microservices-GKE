# user-service/app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/users", methods=["GET"])
def get_users():
    # Dummy data
    return jsonify({"users": ["alice", "bob", "carol"]})

if __name__ == "__main__":
    # Listen on 0.0.0.0 to be reachable inside container
    app.run(host="0.0.0.0", port=8080)
