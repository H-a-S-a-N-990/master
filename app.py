from flask import Flask, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)
PORT = 24457
OFFLINE_THRESHOLD_MINUTES = 1

# Create a SQLite database connection
conn = sqlite3.connect('masterlist.db')
cursor = conn.cursor()

# Create the servers table if it doesn't exist
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

def update_id():
    cursor.execute('SELECT id FROM servers')
    rows = cursor.fetchall()
    for row in rows:
        new_id = row[0] + 1
        cursor.execute('UPDATE servers SET id = ? WHERE id = ?', (new_id, row[0]))
    conn.commit()
    print("All updates completed")

# Schedule the update_id function to run every 30 seconds
import schedule
import time
schedule.every(30).seconds.do(update_id)

@app.route('/announce.php', methods=['POST'])
def announce():
    ip = request.remote_addr
    port = request.form['port']
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_official = 0
    if ip in ['127.0.0.1', '127.0.0.2']:
        is_official = 1

    cursor.execute('SELECT * FROM servers WHERE ip = ? AND port = ?', (ip, port))
    row = cursor.fetchone()
    if row:
        cursor.execute('UPDATE servers SET last_seen = ? WHERE ip = ? AND port = ?', (current_time, ip, port))
        conn.commit()
        print('Server updated successfully:', ip, port)
        return jsonify({'success': True})
    else:
        cursor.execute('INSERT INTO servers (ip, port, last_seen, is_official) VALUES (?, ?, ?, ?)', (ip, port, current_time, is_official))
        conn.commit()
        print('Server registered successfully:', ip, port)
        return jsonify({'success': True})

@app.route('/official', methods=['GET'])
def get_official_servers():
    cursor.execute('SELECT ip, port FROM servers WHERE is_official = 1')
    rows = cursor.fetchall()
    official_servers = [{'ip': row[0], 'port': row[1]} for row in rows]
    return jsonify({'success': True, 'servers': official_servers})

@app.route('/servers', methods=['GET'])
def get_servers():
    cursor.execute('SELECT ip, port, is_official FROM servers')
    rows = cursor.fetchall()
    servers = [{'ip': row[0], 'port': row[1], 'is_official': row[2] == 1} for row in rows]
    return jsonify({'success': True, 'servers': servers})

def remove_offline_servers():
    offline_threshold = datetime.datetime.now() - datetime.timedelta(minutes=OFFLINE_THRESHOLD_MINUTES)
    cursor.execute('DELETE FROM servers WHERE last_seen < ?', (offline_threshold.strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    print('Offline servers removed successfully.')

schedule.every(OFFLINE_THRESHOLD_MINUTES).minutes.do(remove_offline_servers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
