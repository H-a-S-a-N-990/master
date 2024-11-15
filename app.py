# my improved code
from flask import Flask, request, jsonify
import sqlite3
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
PORT = 24457
OFFLINE_THRESHOLD_MINUTES = 1

conn = sqlite3.connect('masterlist.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS servers
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                port INTEGER,
                last_seen DATETIME,
                is_official INTEGER DEFAULT 0)''')
conn.commit()

def update_ids():
    print("Updating IDs for the servers table")
    cursor.execute("SELECT id FROM servers")
    rows = cursor.fetchall()
    for index, row in enumerate(rows, start=1):
        cursor.execute("UPDATE servers SET id = ? WHERE id = ?", (index, row[0]))
        print(f"Row with id {row[0]} updated to id {index}")
    conn.commit()
    print("All updates completed")


scheduler = BackgroundScheduler()
scheduler.add_job(update_ids, 'interval', seconds=30)
scheduler.start()


@app.route('/announce', methods=['POST'])
def announce_server():
    ip = request.headers.get('X-Forwarded-For') or request.remote_addr
    port = request.form.get('port')
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_official = 1 if ip in ['127.0.0.1', '127.0.0.2'] else 0

    cursor.execute("SELECT * FROM servers WHERE ip = ? AND port = ?", (ip, port))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE servers SET last_seen = ? WHERE ip = ? AND port = ?", (current_time, ip, port))
        conn.commit()
        print(f"Server updated successfully: {ip}, {port}")
    else:
        cursor.execute("INSERT INTO servers (ip, port, last_seen, is_official) VALUES (?, ?, ?, ?)", (ip, port, current_time, is_official))
        conn.commit()
        print(f"Server registered successfully: {ip}, {port}")

    return jsonify({"message": "Server announcement processed"})


@app.route('/official', methods=['GET'])
def get_official_servers():
    cursor.execute("SELECT ip, port FROM servers WHERE is_official = 1")
    official_servers = cursor.fetchall()
    return jsonify({"servers": official_servers})


@app.route('/servers', methods=['GET'])
def get_all_servers():
    cursor.execute("SELECT ip, port, is_official FROM servers")
    servers = cursor.fetchall()
    return jsonify({"servers": servers})

if __name__ == '__main__':
    app.run(port=PORT, debug=True)
    
