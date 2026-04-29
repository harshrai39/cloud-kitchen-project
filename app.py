from flask import Flask, request, jsonify
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

# --- DATABASE SETUP & FORCE DATA INJECTION ---
def setup_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Create Tables (Ensures ACID structure)
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INT AUTO_INCREMENT PRIMARY KEY, fullname VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(255), role ENUM('customer', 'admin', 'chef') DEFAULT 'customer')")
        cursor.execute("CREATE TABLE IF NOT EXISTS menu_items (item_id INT AUTO_INCREMENT PRIMARY KEY, item_name VARCHAR(100), price DECIMAL(10,2))")
        cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY, 
            customer_name VARCHAR(100), 
            total_amount DECIMAL(10,2), 
            payment_method VARCHAR(50), 
            order_status VARCHAR(50) DEFAULT 'Preparing', 
            delivery_address TEXT, 
            delivery_rider VARCHAR(100) DEFAULT 'Assigning...')""")
        
        # 2. Force Inject Menu Items
        cursor.execute("INSERT IGNORE INTO menu_items (item_id, item_name, price) VALUES (1, 'Paneer Tikka', 250.00), (2, 'Veg Biryani', 180.00), (3, 'Cold Coffee', 90.00)")

        # 3. Force Inject Sample Orders (This removes the 0s from Admin Dashboard)
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] < 2:
            sample_data = [
                ('Harsh Vardhan Rai', 340.00, 'UPI', 'SRM University, KTR'),
                ('Demo Student', 180.00, 'COD', 'Lucknow Center')
            ]
            cursor.executemany("INSERT INTO orders (customer_name, total_amount, payment_method, delivery_address) VALUES (%s, %s, %s, %s)", sample_data)

        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception as e:
        print(f"DB Error: {e}"); return False

@app.route('/')
def home():
    setup_database() # Runs the setup and data injection
    return jsonify({"status": "Online", "message": "CKMS Backend Ready"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    hpw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (data['email'], hpw))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return jsonify(user) if user else (jsonify({"error": "Auth Failed"}), 401)

@app.route('/active_orders', methods=['GET'])
def get_orders():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
    orders = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(orders)

@app.route('/menu', methods=['GET'])
def get_menu():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu_items")
    m = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(m)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)