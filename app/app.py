import os
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "appdb")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_PORT = os.environ.get("DB_PORT", "5432")

@app.route("/health")
def health():
    return jsonify(status="ok"), 200

@app.route("/db-health")
def db_health():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER,
            password=DB_PASSWORD, port=DB_PORT, connect_timeout=3
        )
        conn.close()
        return jsonify(status="db connected"), 200
    except Exception as e:
        return jsonify(status="db connection failed", error=str(e)), 500

@app.route("/")
def index():
    return jsonify(message="8Byte DevOps Assignment App"), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
