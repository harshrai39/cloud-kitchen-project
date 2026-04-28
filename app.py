from flask import Flask, render_template, request, jsonify
import mysql.connector
from flask_cors import CORS
import hashlib

app = Flask(__name__)
CORS(app)

# --- CLOUD DATABASE CONFIG ---
db_config = {
    'host': 'bflsc3v2zuem9cpblkk9-mysql.services.clever-cloud.com',
    'user': 'ukqysulb87iuj4pg',
    'password': 'D6mG9S057Z5o0LaNV42J', 
    'database': 'bflsc3v2zuem9cpblkk9',
    'port': 3306
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- AUTO SETUP (Fixes your phpMyAdmin issue) ---
def setup_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 1. Users Table
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INT AUTO_INCREMENT PRIMARY KEY, fullname VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(255), role ENUM('customer', 'admin', 'chef') DEFAULT 'customer')")
        # 2. Menu Table
        cursor.execute("CREATE TABLE IF NOT EXISTS menu_items (item_id INT AUTO_INCREMENT PRIMARY KEY, item_name VARCHAR(100), price DECIMAL(10,2))")
        # 3. Comprehensive Orders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100),
                total_amount DECIMAL(10,2),
                payment_method ENUM('UPI', 'Card', 'COD') DEFAULT 'UPI',
                payment_status ENUM('Unpaid', 'Paid') DEFAULT 'Unpaid',
                order_status ENUM('Preparing', 'Out for Delivery', 'Delivered') DEFAULT 'Preparing',
                delivery_address TEXT,
                delivery_rider VARCHAR(100) DEFAULT 'Assigning...'
            )
        """)
        # 4. Order Mapping
        cursor.execute("CREATE TABLE IF NOT EXISTS order_items (id INT AUTO_INCREMENT PRIMARY KEY, order_id INT, item_id INT, FOREIGN KEY (order_id) REFERENCES orders(order_id), FOREIGN KEY (item_id) REFERENCES menu_items(item_id))")
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False

@app.route('/')
def home():
    setup_database()
    return jsonify({"status": "Online", "system": "Cloud Kitchen Management System v2.0"})

# --- AUTHENTICATION ---
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    hashed_pw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)", (data['fullname'], data['email'], hashed_pw))
        conn.commit()
        return jsonify({"message": "User registered"}), 201
    except:
        return jsonify({"error": "Email exists"}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    hashed_pw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (data['email'], hashed_pw))
    user = cursor.fetchone()
    if user:
        return jsonify({"fullname": user['fullname'], "role": user['role']})
    return jsonify({"error": "Invalid login"}), 401

# --- ORDERING SYSTEM ---
@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (customer_name, total_amount, payment_method, payment_status, delivery_address) VALUES (%s, %s, %s, 'Paid', %s)", 
                   (data['customer_name'], data['total_price'], data['payment_method'], data['address']))
    oid = cursor.lastrowid
    for iid in data['items']:
        cursor.execute("INSERT INTO order_items (order_id, item_id) VALUES (%s, %s)", (oid, iid))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Success", "order_id": oid})

@app.route('/active_orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT o.*, GROUP_CONCAT(m.item_name SEPARATOR ', ') as food_items FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN menu_items m ON oi.item_id = m.item_id GROUP BY o.order_id ORDER BY o.order_id DESC")
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(orders)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)