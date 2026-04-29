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

# --- DATABASE SETUP & DEFAULT DATA ---
def setup_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create Tables
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INT AUTO_INCREMENT PRIMARY KEY, fullname VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(255), role ENUM('customer', 'admin', 'chef') DEFAULT 'customer')")
        cursor.execute("CREATE TABLE IF NOT EXISTS menu_items (item_id INT AUTO_INCREMENT PRIMARY KEY, item_name VARCHAR(100), price DECIMAL(10,2))")
        cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY, 
            customer_name VARCHAR(100), 
            total_amount DECIMAL(10,2), 
            payment_method ENUM('UPI', 'Card', 'COD'), 
            order_status ENUM('Preparing', 'Out for Delivery', 'Delivered') DEFAULT 'Preparing', 
            delivery_address TEXT, 
            delivery_rider VARCHAR(100) DEFAULT 'Assigning...')""")
        
        # Insert Default Menu if empty
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        if cursor.fetchone()[0] == 0:
            menu = [('Paneer Tikka', 240.00), ('Veg Burger', 120.00), ('Hakubaku Noodles', 180.00)]
            cursor.executemany("INSERT INTO menu_items (item_name, price) VALUES (%s, %s)", menu)

        # Insert Default Orders for Admin Dashboard Visibility
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] == 0:
            sample_orders = [
                ('Harsh Vardhan Rai', 360.00, 'UPI', 'SRM University, KTR'),
                ('Test Student', 120.00, 'COD', 'Lucknow, UP')
            ]
            cursor.executemany("INSERT INTO orders (customer_name, total_amount, payment_method, delivery_address) VALUES (%s, %s, %s, %s)", sample_orders)

        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception as e:
        print(f"DB Error: {e}"); return False

@app.route('/')
def home():
    setup_database()
    return jsonify({"status": "Online", "message": "CKMS Backend Ready"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    hpw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (data['email'], hpw))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return jsonify(user) if user else (jsonify({"error": "Failed"}), 401)

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