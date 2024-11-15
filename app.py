from flask import Flask, request, jsonify
import sqlite3
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = Flask(__name__)
PORT = 24457

# Ensure the database directory exists
os.makedirs(os.path.dirname('masterlist.db'), exist_ok=True)

# Database connection with error handling
def get_db_connection():
    try:
        conn = sqlite3.connect('masterlist.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

# Initialize database
def init_database():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS servers
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT,
                            port INTEGER,
                            last_seen DATETIME,
                            is_official INTEGER DEFAULT 0,
                            UNIQUE(ip, port))''')
            conn.commit()
            conn.close()
            print("Database initialized successfully")
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")

# Update IDs function
def update_ids():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            print("Updating IDs for the servers table")
            cursor.execute("SELECT id FROM servers")
            rows = cursor.fetchall()
            for index, row in enumerate(rows, start=1):
                cursor.execute("UPDATE servers SET id = ? WHERE id = ?", (index, row['id']))
                print(f"Row with id {row['id']} updated to id {index}")
            conn.commit()
            conn.close()
            print("All updates completed")
    except sqlite3.Error as e:
        print(f"Error updating IDs: {e}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(update_ids, 'interval', minutes=30)
scheduler.start()

# Initialize database on startup
init_database()

@app.route('/announce', methods=['POST'])
def announce_server():
    try:
        # Get IP address, considering potential proxy
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Validate port
        port = request.form.get('port')
        if not port or not port.isdigit():
            return jsonify({"error": "Invalid port"}), 400

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine if server is official
        is_official = 1 if ip in ['127.0.0.1', '127.0.0.2'] else 0

        # Database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()

        try:
            # Upsert operation (update or insert)
            cursor.execute('''
                INSERT INTO servers (ip, port, last_seen, is_official) 
                VALUES (?, ?, ?, ?) 
                ON CONFLICT(ip, port) DO UPDATE SET 
                last_seen = ?, is_official = ?
            ''', (ip, port, current_time, is_official, 
                  current_time, is_official))
            
            conn.commit()
            print(f"Server {'updated' if cursor.rowcount > 1 else 'registered'} successfully: {ip}, {port}")
            
            return jsonify({"message": "Server announcement processed"}), 200
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return jsonify({"error": "Database operation failed"}), 500
        
        finally:
            conn.close()

    except Exception as e:
        print(f"Unexpected error in announce_server: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/official', methods=['GET'])
def get_official_servers():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()
        cursor.execute("SELECT ip, port FROM servers WHERE is_official = 1")
        official_servers = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({"servers": official_servers}), 200
    
    except Exception as e:
        print(f"Error fetching official servers: {e}")
        return jsonify({"error": "Failed to retrieve servers"}), 500

@app.route('/servers', methods=['GET'])
def get_all_servers():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()
        cursor.execute("SELECT ip, port, last_seen FROM servers")
        all_servers = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({"servers": all_servers}), 200
    
    except Exception as e:
        print(f"Error fetching all servers: {e}")
        return jsonify({"error": "Failed to retrieve servers"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
