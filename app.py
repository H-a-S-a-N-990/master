from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///masterlist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

OFFLINE_THRESHOLD_MINUTES = 1

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False)
    port = db.Column(db.Integer, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_official = db.Column(db.Boolean, default=False)

# Create the database and the table if they do not exist
with app.app_context():
    db.create_all()

@app.route('/announce.php', methods=['POST'])
def announce():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    port = request.form.get('port')
    current_time = datetime.utcnow()
    is_official = 1 if ip in ['127.0.0.1', '127.0.0.2'] else 0

    # Check if the server already exists in the database
    server = Server.query.filter_by(ip=ip, port=port).first()

    if server:
        # If the server exists, update the last_seen timestamp
        server.last_seen = current_time
        db.session.commit()
        print(f'Server updated successfully: {ip}:{port}')
        return '', 200
    else:
        # If the server doesn't exist, insert a new record
        new_server = Server(ip=ip, port=port, last_seen=current_time, is_official=is_official)
        db.session.add(new_server)
        db.session.commit()
        print(f'Server registered successfully: {ip}:{port}')
        return '', 200

@app.route('/official', methods=['GET'])
def official_servers():
    servers = Server.query.filter_by(is_official=True).all()
    official_servers = [{'ip': server.ip, 'port': server.port} for server in servers]
    return jsonify({'success': True, 'servers': official_servers})

@app.route('/servers', methods=['GET'])
def all_servers():
    servers = Server.query.all()
    all_servers = [{'ip': server.ip, 'port': server.port, 'is_official': server.is_official} for server in servers]
    return jsonify({'success': True, 'servers': all_servers})

def remove_offline_servers():
    offline_threshold = datetime.utcnow() - timedelta(minutes=OFFLINE_THRESHOLD_MINUTES)
    db.session.query(Server).filter(Server.last_seen < offline_threshold).delete()
    db.session.commit()
    print('Offline servers removed successfully.')

# Schedule the removal of offline servers
import threading
import time

def schedule_removal():
    while True:
        time.sleep(OFFLINE_THRESHOLD_MINUTES * 60)
        remove_offline_servers()

# Start the scheduled task in a separate thread
threading.Thread(target=schedule_removal, daemon=True).start()

if __name__ == '__main__':
    app.run(port=24457)
