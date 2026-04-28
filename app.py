from flask import Flask, render_template, request, jsonify
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

# --- DATABASE SETUP (Runs automatically) ---
def setup_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create Users table for login/signup
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                fullname VARCHAR(100),
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('customer', 'admin', 'chef') DEFAULT 'customer'
            )
        """)
        # Add Management columns to Orders
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN total_amount DECIMAL(10,2) DEFAULT 0.00")
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_status ENUM('Unpaid', 'Paid') DEFAULT 'Unpaid'")
            cursor.execute("ALTER TABLE orders ADD COLUMN delivery_address TEXT")
        except:
            pass # Columns already exist
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Setup Error: {e}")
        return False

@app.route('/')
def home():
    setup_database()
    return jsonify({"message": "Cloud Kitchen System: Online & Database Ready"})

# --- AUTHENTICATION ROUTES ---

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    # Hashing password for security
    hashed_pw = hashlib.sha256(data['password'].encode()).hexdigest()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)",
                       (data['fullname'], data['email'], hashed_pw))
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        return jsonify({"error": "Email already exists or database error"}), 400
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
        return jsonify({"message": "Login successful!", "role": user['role'], "fullname": user['fullname']})
    return jsonify({"error": "Invalid email or password"}), 401

# --- CORE FUNCTIONALITY ---

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
        # Insert main order
        cursor.execute("INSERT INTO orders (customer_name, total_amount, payment_status, delivery_address) VALUES (%s, %s, 'Paid', %s)", 
                       (data['customer_name'], data['total_price'], data['address']))
        order_id = cursor.lastrowid
        # Insert items
        for item_id in data['items']:
            cursor.execute("INSERT INTO order_items (order_id, item_id) VALUES (%s, %s)", (order_id, item_id))
        conn.commit()
        return jsonify({"message": "Order placed!", "order_id": order_id}), 201
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
        SELECT o.order_id, o.customer_name, o.payment_status, o.total_amount, GROUP_CONCAT(m.item_name SEPARATOR ', ') as food_items
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN menu_items m ON oi.item_id = m.item_id
        GROUP BY o.order_id
    """
    cursor.execute(query)
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(orders)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)