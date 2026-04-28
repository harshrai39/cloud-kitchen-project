from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import hashlib

app = Flask(__name__)
CORS(app) # Fixes the "not responding" issue

db_config = {
    'host': 'bflsc3v2zuem9cpblkk9-mysql.services.clever-cloud.com',
    'user': 'ukqysulb87iuj4pg',
    'password': 'D6mG9S057Z5o0LaNV42J', 
    'database': 'bflsc3v2zuem9cpblkk9',
    'port': 3306,
    'connection_timeout': 10
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def setup():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INT AUTO_INCREMENT PRIMARY KEY, fullname VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(255), role ENUM('customer', 'admin') DEFAULT 'customer')")
        cursor.execute("CREATE TABLE IF NOT EXISTS menu_items (item_id INT AUTO_INCREMENT PRIMARY KEY, item_name VARCHAR(100), price DECIMAL(10,2))")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100),
                total_amount DECIMAL(10,2),
                payment_method VARCHAR(50),
                order_status VARCHAR(50) DEFAULT 'Preparing',
                delivery_address TEXT,
                delivery_rider VARCHAR(100) DEFAULT 'Assigning...'
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS order_items (id INT AUTO_INCREMENT PRIMARY KEY, order_id INT, item_id INT, FOREIGN KEY (order_id) REFERENCES orders(order_id), FOREIGN KEY (item_id) REFERENCES menu_items(item_id))")
        conn.commit()
        return jsonify({"message": "CKMS Backend Ready!"})
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if conn: conn.close() # Fixes the "Max Connections" error

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    pw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)", (data['fullname'], data['email'], pw))
        conn.commit()
        return jsonify({"message": "Success"}), 201
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    pw = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (data['email'], pw))
        user = cursor.fetchone()
        if user: return jsonify({"fullname": user['fullname'], "role": user['role']})
        return jsonify({"error": "Failed"}), 401
    finally:
        conn.close()

@app.route('/menu', methods=['GET'])
def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM menu_items")
        return jsonify(cursor.fetchall())
    finally:
        conn.close()

@app.route('/add_menu_item', methods=['POST'])
def add_menu_item():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO menu_items (item_name, price) VALUES (%s, %s)", (data['item_name'], data['price']))
        conn.commit()
        return jsonify({"message": "Added"})
    finally:
        conn.close()

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO orders (customer_name, total_amount, payment_method, delivery_address) VALUES (%s, %s, %s, %s)", 
                       (data['customer_name'], data['total_price'], data['payment_method'], data['address']))
        oid = cursor.lastrowid
        for iid in data['items']:
            cursor.execute("INSERT INTO order_items (order_id, item_id) VALUES (%s, %s)", (oid, iid))
        conn.commit()
        return jsonify({"message": "Success", "order_id": oid})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/active_orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT o.*, GROUP_CONCAT(m.item_name SEPARATOR ', ') as food_items 
            FROM orders o 
            JOIN order_items oi ON o.order_id = oi.order_id 
            JOIN menu_items m ON oi.item_id = m.item_id 
            GROUP BY o.order_id 
            ORDER BY o.order_id DESC
        """)
        return jsonify(cursor.fetchall())
    finally:
        conn.close()

@app.route('/update_order', methods=['POST'])
def update_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE orders SET order_status = %s, delivery_rider = %s WHERE order_id = %s", 
                       (data['status'], data['rider'], data['order_id']))
        conn.commit()
        return jsonify({"message": "Updated"})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)