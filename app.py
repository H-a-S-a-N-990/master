from flask import Flask, request, jsonify
import sqlite3
import datetime
import schedule
import threading

app = Flask(__name__)
PORT = 24457
OFFLINE_THRESHOLD_MINUTES = 1

# Function to create a new database connection
def get_db_connection():
    conn = sqlite3.connect('masterlist.db')
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

# Create the servers table if it doesn't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            port INTEGER,
            last_seen DATETIME,
            is_official INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def update_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM servers')
    rows = cursor.fetchall()
    for row in rows:
        new_id = row[0] + 1
        cursor.execute('UPDATE servers SET id = ? WHERE id = ?', (new_id, row[0]))
    conn.commit()
    conn.close()
    print("All updates completed")

# Schedule the update_id function to run every 30 seconds
schedule.every(30).seconds.do(update_id)

@app.route('/announce.php', methods=['POST'])
def announce():
    ip = request.remote_addr
    port = request.form['port']
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_official = 1 if ip in ['127.0.0.1', '127.0.0.2'] else 0

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servers WHERE ip = ? AND port = ?', (ip, port))
    row = cursor.fetchone()
    
    if row:
        cursor.execute('UPDATE servers SET last_seen = ? WHERE ip = ? AND port = ?', (current_time, ip, port))
        conn.commit()
        print('Server updated successfully:', ip, port)
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.execute('INSERT INTO servers (ip, port, last_seen, is_official) VALUES (?, ?, ?, ?)', (ip, port, current_time, is_official))
        conn.commit()
        print('Server registered successfully:', ip, port)
        conn.close()
        return jsonify({'success': True})

@app.route('/official', methods=['GET'])
def get_official_servers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ip, port FROM servers WHERE is_official = 1')
    rows = cursor.fetchall()
    official_servers = [{'ip': row['ip'], 'port': row['port']} for row in rows]
    conn.close()
    return jsonify({'success': True, 'servers': official_servers})

@app.route('/servers', methods=['GET'])
def get_servers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ip, port, is_official FROM servers')
    rows = cursor.fetchall()
    servers = [{'ip': row['ip'], 'port': row['port'], 'is_official': row['is_official'] == 1} for row in rows]
    conn.close()
    return jsonify({'success': True, 'servers': servers})

def remove_offline_servers():
    offline_threshold = datetime.datetime.now() - datetime.timedelta(minutes=OFFLINE_THRESHOLD_MINUTES)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM servers WHERE last_seen < ?', (offline_threshold.strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    conn.close()
    print('Offline servers removed successfully.')

schedule.every(OFFLINE_THRESHOLD_MINUTES).minutes.do(remove_offline_servers)

if __name__ == '__main__':
    # Start a thread to run the scheduled tasks
    def run_schedule():
        while True:
                schedule.run_pending()
                time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT)
