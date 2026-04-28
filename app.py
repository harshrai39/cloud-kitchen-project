from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import hashlib

app = Flask(__name__)
CORS(app)

# --- CLOUD DATABASE CONFIGURATION ---
db_config = {
    'host': 'bflsc3v2zuem9cpblkk9-mysql.services.clever-cloud.com',
    'user': 'ukqysulb87iuj4pg',
    'password': 'D6mG9S057Z5o0LaNV42J', 
    'database': 'bflsc3v2zuem9cpblkk9',
    'port': 3306
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- SYSTEM INITIALIZATION (Creates Tables & Adds Food) ---
@app.route('/')
def setup():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Users Table (Identity Management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                fullname VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                password VARCHAR(255),
                role ENUM('customer', 'admin', 'chef') DEFAULT 'customer'
            )
        """)

        # 2. Menu Table (Inventory Management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                item_id INT AUTO_INCREMENT PRIMARY KEY,
                item_name VARCHAR(100),
                price DECIMAL(10,2)
            )
        """)

        # 3. Orders Table (Sales & Logistics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100),
                total_amount DECIMAL(10,2),
                payment_method VARCHAR(50),
                payment_status VARCHAR(50) DEFAULT 'Paid',
                order_status ENUM('Preparing', 'Out for Delivery', 'Delivered') DEFAULT 'Preparing',
                delivery_address TEXT,
                delivery_rider VARCHAR(100) DEFAULT 'Assigning...'
            )
        """)

        # 4. Order Mapping (Relational Data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                item_id INT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
            )
        """)

        # 5. AUTO-FILL MENU (If empty, add items so they show on UI)
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO menu_items (item_name, price) VALUES ('Classic Burger', 120), ('Veg Pizza', 250), ('French Fries', 80), ('Pasta Alfredo', 180)")
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "Success", "message": "CKMS Database Ready & Food Seeded!"})
    except Exception as e:
        return jsonify({"status": "Error", "error": str(e)})

# --- AUTHENTICATION MODULE ---

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    hashed_pw = hashlib.sha256(data['password'].encode()).hexdigest()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)", 
                       (data['fullname'], data['email'], hashed_pw))
        conn.commit()
        return jsonify({"message": "User registered"}), 201
    except:
        return jsonify({"error": "Email already exists"}), 400
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
    cursor.close()
    conn.close()
    if user:
        return jsonify({"fullname": user['fullname'], "role": user['role']})
    return jsonify({"error": "Invalid login"}), 401

# --- CORE BUSINESS LOGIC ---

@app.route('/menu', methods=['GET'])
def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu_items")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(items)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (customer_name, total_amount, payment_method, delivery_address) 
            VALUES (%s, %s, %s, %s)
        """, (data['customer_name'], data['total_price'], data['payment_method'], data['address']))
        
        order_id = cursor.lastrowid
        for item_id in data['items']:
            cursor.execute("INSERT INTO order_items (order_id, item_id) VALUES (%s, %s)", (order_id, item_id))
        
        conn.commit()
        return jsonify({"message": "Order Successful", "order_id": order_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/active_orders', methods=['GET'])
def get_active_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT o.*, GROUP_CONCAT(m.item_name SEPARATOR ', ') as food_items
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN menu_items m ON oi.item_id = m.item_id
        GROUP BY o.order_id
        ORDER BY o.order_id DESC
    """
    cursor.execute(query)
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(orders)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)