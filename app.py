import os
import sqlite3
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
DB_FILE = "cloud_security.db"
UPLOAD_FOLDER = "static"
API_SECRET = os.environ.get("API_SECRET", "super_secret_office_key_2026") 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Persons (name TEXT PRIMARY KEY, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Logs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, event_type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def require_auth(req):
    return req.headers.get("Authorization") == f"Bearer {API_SECRET}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT id, name, event_type, timestamp FROM Logs ORDER BY id DESC LIMIT 6")
    recent_logs = [{"id": r[0], "name": r[1], "event_type": r[2], "timestamp": r[3]} for r in c.fetchall()]
    
    c.execute("SELECT COUNT(*) FROM Logs")
    total_entries = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM Logs WHERE event_type = 'ENTRY' OR event_type = 'APPROVED_BY_ADMIN'")
    auth_entries = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM Logs WHERE event_type = 'REJECTED_BY_ADMIN' OR event_type = 'TIMEOUT_DENIED'")
    rejections = c.fetchone()[0]
    
    latest_entry = recent_logs[0] if recent_logs else {"name": "None", "timestamp": "-"}
    conn.close()
    
    return jsonify({
        "total_entries": total_entries,
        "auth_entries": auth_entries,
        "rejections": rejections,
        "latest_entry": latest_entry,
        "recent_logs": recent_logs
    })

@app.route('/api/log_event', methods=['POST'])
def log_event():
    if not require_auth(request): return jsonify({"error": "Unauthorized"}), 401
    
    # Accept standard form data (so images can be attached)
    name = request.form.get("name", "Unknown")
    event_type = request.form.get("event_type", "EVENT")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO Logs (name, event_type) VALUES (?, ?)", (name, event_type))
    log_id = c.lastrowid
    conn.commit()
    conn.close()

    # Save the attached photo named strictly by its database ID
    if 'photo' in request.files:
        photo = request.files['photo']
        photo.save(os.path.join(UPLOAD_FOLDER, f"{log_id}.jpg"))

    return jsonify({"status": "success"})

@app.route('/api/sync_persons', methods=['POST'])
def sync_persons():
    if not require_auth(request): return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for p in data.get("persons", []):
        c.execute("INSERT OR REPLACE INTO Persons (name, role) VALUES (?, ?)", (p["name"], p["role"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))