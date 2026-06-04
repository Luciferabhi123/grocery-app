
from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import razorpay

app = Flask(__name__)
app.secret_key = "secret123"

razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_SECRET"))

# ================= DATABASE =================

def connect_db():
    return sqlite3.connect("database.db")

def create_tables():

    con = connect_db()
    cur = con.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE,
            password TEXT
        )
    """)

    # PRODUCTS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    image TEXT DEFAULT ''
)
    """)

    # ORDERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            product TEXT,
            quantity INTEGER,
            total INTEGER,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()

create_tables()


# ================= API =================

# REGISTER
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    try:
        con = connect_db()
        cur = con.cursor()
        cur.execute("INSERT INTO users (name, phone, password) VALUES (?, ?, ?)",
                    (data["name"], data["phone"], generate_password_hash(data["password"])))
        con.commit()
        con.close()
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error", "message": "User exists"})


# LOGIN
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json

    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE phone=?", (data["phone"],))
    user = cur.fetchone()
    con.close()

    if user and check_password_hash(user[3], data["password"]):
        return jsonify({"status": "success", "name": user[1]})
    return jsonify({"status": "error"})


# PRODUCTS
@app.route("/api/products")
def api_products():
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM products")
    data = cur.fetchall()
    con.close()

    return jsonify([
        {"id": p[0], "name": p[1], "price": p[2]} for p in data
    ])


# PLACE ORDER (IMPORTANT FIX WITH STATUS)
@app.route("/api/place_order", methods=["POST"])
def api_place_order():
    data = request.json
    con = connect_db()
    cur = con.cursor()

    for item in data["cart"]:
        cur.execute("""
            INSERT INTO orders (user, product, quantity, total, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["user"],
            item["name"],
            item["qty"],
            item["price"] * item["qty"],
            "Pending"
        ))

    con.commit()
    con.close()

    return jsonify({"status": "order placed"})


# GET ORDERS (WITH STATUS)
@app.route("/api/orders")
def api_orders():
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    data = cur.fetchall()
    con.close()

    return jsonify([
        {
            "id": o[0],
            "user": o[1],
            "product": o[2],
            "qty": o[3],
            "total": o[4],
            "status": o[5]
        }
        for o in data
    ])


# UPDATE STATUS (ADMIN)
@app.route("/update_status/<int:id>/<status>")
def update_status(id, status):
    con = connect_db()
    cur = con.cursor()
    cur.execute("UPDATE orders SET status=? WHERE id=?", (status, id))
    con.commit()
    con.close()

    return redirect("/admin/dashboard")


# PAYMENT
@app.route("/create_payment", methods=["POST"])
def create_payment():
    amount = int(request.form["amount"]) * 100

    payment = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return {"id": payment["id"]}


# ================= WEB ROUTES =================

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
