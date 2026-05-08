from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
import secrets
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin123')
KEYS_FILE = '/tmp/keys.json'
LOGS_FILE = '/tmp/logs.json'
HARDWARE_BANS_FILE = '/tmp/hardware_bans.json'

TIERS = {
    '1h': {'name': '1 Hour', 'hours': 1, 'price': 'Free'},
    '24h': {'name': '1 Day', 'hours': 24, 'price': '$2.99'},
    '7d': {'name': '1 Week', 'hours': 168, 'price': '$9.99'},
    '30d': {'name': '1 Month', 'hours': 720, 'price': '$24.99'},
    'lifetime': {'name': 'Lifetime', 'hours': 0, 'price': '$99.99'}
}

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except:
        pass
    return default

def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")

def load_keys(): return load_json(KEYS_FILE, {})
def save_keys(keys): save_json(KEYS_FILE, keys)
def load_logs(): return load_json(LOGS_FILE, [])
def save_logs(logs): save_json(LOGS_FILE, logs)
def load_hw_bans(): return load_json(HARDWARE_BANS_FILE, [])
def save_hw_bans(bans): save_json(HARDWARE_BANS_FILE, bans)

def add_log(action, details="", ip=None):
    logs = load_logs()
    logs.append({
        'id': secrets.token_hex(8),
        'timestamp': int(time.time()),
        'action': action,
        'details': details,
        'ip': ip or request.remote_addr or 'unknown',
        'user_agent': request.headers.get('User-Agent', 'Unknown')[:100]
    })
    save_logs(logs[-1000:])

def is_key_valid(key_data):
    if not key_data or key_data.get('banned') or key_data.get('hw_banned'):
        return False
    if key_data['expires'] != 9999999999 and int(time.time()) > key_data['expires']:
        return False
    return True

def get_key_status(key_data):
    now = int(time.time())
    if not key_data:
        return 'deleted'
    if key_data.get('hw_banned'):
        return 'hw_banned'
    if key_data.get('banned'):
        return 'banned'
    if key_data['expires'] != 9999999999 and key_data['expires'] < now:
        return 'expired'
    if key_data.get('device_id'):
        return 'active'
    return 'unused'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def format_time(ts):
    if ts == 9999999999:
        return "Lifetime"
    if not ts:
        return "Never"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

def time_ago(ts):
    if not ts:
        return "Never"
    diff = int(time.time()) - ts
    if diff < 60:
        return f"{diff}s ago"
    if diff < 3600:
        return f"{diff//60}m ago"
    if diff < 86400:
        return f"{diff//3600}h ago"
    return f"{diff//86400}d ago"

ADMIN_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FF Mod Pro - Admin Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF6B00; --primary-light: #FF8533; --primary-glow: rgba(255,107,0,0.3);
            --bg: #050505; --bg-card: #0c0c0c; --bg-elevated: #141414;
            --text: #ffffff; --text-secondary: #999999; --text-muted: #555555;
            --success: #00FF88; --danger: #ff4444; --warning: #FFB347; --border: #1a1a1a;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 50%, #FFB347 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif;
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 20px; overflow: hidden;
        }
        body::before {
            content: ''; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle at 30% 30%, rgba(255,107,0,0.08) 0%, transparent 50%),
                        radial-gradient(circle at 70% 70%, rgba(255,133,51,0.05) 0%, transparent 50%);
            animation: bgFloat 20s ease-in-out infinite; pointer-events: none;
        }
        @keyframes bgFloat {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33% { transform: translate(30px, -30px) rotate(1deg); }
            66% { transform: translate(-20px, 20px) rotate(-1deg); }
        }
        .login-container { width: 100%; max-width: 440px; position: relative; z-index: 1; }
        .login-header { text-align: center; margin-bottom: 48px; }
        .login-header .logo-icon {
            width: 72px; height: 72px; background: var(--gradient); border-radius: 20px;
            display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;
            font-size: 32px; box-shadow: 0 8px 32px rgba(255,107,0,0.3);
        }
        .login-header .logo {
            font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 900;
            background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; letter-spacing: 2px;
        }
        .login-header p { color: var(--text-secondary); font-size: 14px; letter-spacing: 1px; }
        .login-card {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 24px;
            padding: 48px; position: relative; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .login-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--gradient);
        }
        .form-group { margin-bottom: 28px; }
        .form-group label {
            display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary);
            margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1.5px;
        }
        .form-group input {
            width: 100%; background: var(--bg-elevated); border: 2px solid var(--border);
            color: var(--text); padding: 16px 18px; border-radius: 14px; font-size: 15px;
            outline: none; transition: all 0.3s; font-family: 'Inter', sans-serif;
        }
        .form-group input:focus { border-color: var(--primary); box-shadow: 0 0 0 4px var(--primary-glow); }
        .form-group input::placeholder { color: var(--text-muted); }
        .login-btn {
            width: 100%; background: var(--gradient); color: white; border: none;
            padding: 18px; border-radius: 14px; font-size: 16px; font-weight: 800;
            cursor: pointer; transition: all 0.3s; letter-spacing: 1px; text-transform: uppercase;
            margin-top: 8px; position: relative; overflow: hidden;
        }
        .login-btn::after {
            content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        .login-btn:hover::after { left: 100%; }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(255,107,0,0.3); }
        .error-message {
            background: rgba(255,68,68,0.1); border: 1px solid rgba(255,68,68,0.3);
            color: var(--danger); padding: 14px 18px; border-radius: 12px; font-size: 14px;
            margin-bottom: 24px; display: none; align-items: center; gap: 10px;
        }
        .error-message.show { display: flex; }
        .security-note {
            text-align: center; margin-top: 24px; font-size: 12px; color: var(--text-muted);
            display: flex; align-items: center; justify-content: center; gap: 6px;
        }
        .security-note .dot {
            width: 6px; height: 6px; background: var(--success); border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="logo-icon">&#128293;</div>
            <div class="logo">FF MOD PRO</div>
            <p>Developer Control Panel</p>
        </div>
        <div class="login-card">
            {% if error %}
            <div class="error-message show">
                <span>&#9888;&#65039;</span>
                <span>{{ error }}</span>
            </div>
            {% endif %}
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" placeholder="Enter username" required autofocus autocomplete="off">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter password" required>
                </div>
                <button type="submit" class="login-btn">&#128272; Secure Login</button>
            </form>
            <div class="security-note">
                <span class="dot"></span>
                <span>Secure SSL Connection Active</span>
            </div>
        </div>
    </div>
</body>
</html>"""

ADMIN_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FF Mod Pro - Developer Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #FF6B00; --primary-light: #FF8533; --primary-glow: rgba(255,107,0,0.2);
            --bg: #050505; --bg-sidebar: #080808; --bg-card: #0c0c0c; --bg-elevated: #141414; --bg-hover: #1c1c1c;
            --text: #ffffff; --text-secondary: #999999; --text-muted: #444444;
            --success: #00FF88; --danger: #ff4444; --warning: #FFB347; --info: #3399FF;
            --border: #1a1a1a; --border-light: #222222;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 50%, #FFB347 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #444; }
        .dashboard { display: flex; min-height: 100vh; }
        .sidebar {
            width: 280px; background: var(--bg-sidebar); border-right: 1px solid var(--border);
            padding: 0; position: fixed; height: 100vh; overflow-y: auto; z-index: 100;
            display: flex; flex-direction: column;
        }
        .sidebar-header { padding: 28px 24px 24px; border-bottom: 1px solid var(--border); }
        .sidebar-logo {
            font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 900;
            background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            display: flex; align-items: center; gap: 12px;
        }
        .sidebar-logo i { font-size: 26px; -webkit-text-fill-color: var(--primary); }
        .sidebar-subtitle { font-size: 11px; color: var(--text-muted); margin-top: 6px; letter-spacing: 2px; text-transform: uppercase; }
        .nav-menu { list-style: none; padding: 16px 12px; flex: 1; }
        .nav-item { margin-bottom: 4px; }
        .nav-link {
            display: flex; align-items: center; gap: 14px; padding: 13px 18px;
            color: var(--text-secondary); border-radius: 12px; font-size: 14px; font-weight: 600;
            cursor: pointer; border: none; background: none; width: 100%; text-align: left; transition: all 0.3s;
        }
        .nav-link:hover, .nav-link.active { background: var(--bg-elevated); color: var(--primary); }
        .nav-link i { width: 22px; text-align: center; font-size: 17px; }
        .nav-badge { margin-left: auto; background: var(--primary); color: white; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 50px; }
        .sidebar-footer { padding: 20px 24px; border-top: 1px solid var(--border); }
        .logout-btn { display: flex; align-items: center; gap: 10px; color: var(--danger); text-decoration: none; font-size: 14px; font-weight: 700; padding: 10px 14px; border-radius: 10px; transition: all 0.3s; }
        .logout-btn:hover { background: rgba(255,68,68,0.1); }
        .main-content { flex: 1; margin-left: 280px; padding: 28px 36px; min-height: 100vh; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 36px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
        .page-title { font-family: 'Orbitron', sans-serif; font-size: 26px; font-weight: 700; }
        .top-actions { display: flex; gap: 12px; align-items: center; }
        .refresh-btn, .export-btn {
            background: var(--bg-elevated); border: 1px solid var(--border-light); color: var(--text-secondary);
            padding: 10px 18px; border-radius: 12px; cursor: pointer; font-size: 13px; font-weight: 600;
            display: flex; align-items: center; gap: 8px; transition: all 0.3s;
        }
        .refresh-btn:hover, .export-btn:hover { border-color: var(--primary); color: var(--primary); }
        .live-indicator { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
        .live-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 32px; }
        .stat-card {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px;
            padding: 24px; position: relative; overflow: hidden; transition: all 0.3s;
        }
        .stat-card:hover { transform: translateY(-3px); border-color: var(--border-light); }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
        .stat-card.total::before { background: var(--gradient); }
        .stat-card.active::before { background: var(--success); }
        .stat-card.expired::before { background: var(--danger); }
        .stat-card.banned::before { background: var(--warning); }
        .stat-icon {
            width: 48px; height: 48px; border-radius: 14px;
            display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 16px;
        }
        .stat-card.total .stat-icon { background: rgba(255,107,0,0.12); color: var(--primary); }
        .stat-card.active .stat-icon { background: rgba(0,255,136,0.12); color: var(--success); }
        .stat-card.expired .stat-icon { background: rgba(255,68,68,0.12); color: var(--danger); }
        .stat-card.banned .stat-icon { background: rgba(255,179,71,0.12); color: var(--warning); }
        .stat-value { font-family: 'Orbitron', sans-serif; font-size: 34px; font-weight: 900; margin-bottom: 4px; }
        .stat-card.total .stat-value { color: var(--primary); }
        .stat-card.active .stat-value { color: var(--success); }
        .stat-card.expired .stat-value { color: var(--danger); }
        .stat-card.banned .stat-value { color: var(--warning); }
        .stat-label { font-size: 13px; color: var(--text-secondary); font-weight: 600; }
        .stat-change { font-size: 11px; margin-top: 8px; display: flex; align-items: center; gap: 4px; }
        .stat-change.up { color: var(--success); }
        .stat-change.down { color: var(--danger); }
        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px; overflow: hidden; margin-bottom: 24px; }
        .card-header { padding: 22px 28px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .card-title { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 12px; }
        .card-title i { color: var(--primary); font-size: 18px; }
        .card-body { padding: 24px 28px; }
        .generate-section { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; align-items: stretch; }
        .tier-select {
            background: var(--bg-elevated); border: 2px solid var(--border); color: var(--text);
            padding: 14px 18px; border-radius: 14px; font-size: 14px; min-width: 180px;
            outline: none; cursor: pointer; font-family: 'Inter', sans-serif; font-weight: 600; transition: all 0.3s;
        }
        .tier-select:focus { border-color: var(--primary); }
        .tier-select option { background: var(--bg-elevated); }
        .count-input {
            background: var(--bg-elevated); border: 2px solid var(--border); color: var(--text);
            padding: 14px 18px; border-radius: 14px; font-size: 14px; width: 90px;
            outline: none; font-family: 'Inter', sans-serif; font-weight: 600; text-align: center;
        }
        .count-input:focus { border-color: var(--primary); }
        .btn {
            padding: 14px 28px; border-radius: 14px; font-size: 14px; font-weight: 700;
            cursor: pointer; border: none; display: inline-flex; align-items: center; gap: 10px;
            transition: all 0.3s; font-family: 'Inter', sans-serif;
        }
        .btn-primary { background: var(--gradient); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(255,107,0,0.3); }
        .btn-danger { background: var(--danger); color: white; }
        .btn-danger:hover { background: #ff2222; transform: translateY(-2px); }
        .btn-sm { padding: 8px 16px; font-size: 12px; }
        .btn-secondary { background: var(--bg-elevated); color: var(--text); border: 1px solid var(--border-light); }
        .btn-secondary:hover { border-color: var(--primary); color: var(--primary); }
        .btn-warning { background: var(--warning); color: #000; }
        .btn-info { background: var(--info); color: white; }
        .generated-keys {
            background: var(--bg-elevated); border-radius: 16px; padding: 20px; margin-top: 20px;
            display: none; border: 1px solid var(--border);
        }
        .generated-keys.show { display: block; }
        .generated-keys h4 { font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; }
        .key-list { display: flex; flex-direction: column; gap: 8px; }
        .key-item {
            background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 10px;
            padding: 14px 18px; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 14px;
            color: var(--primary); display: flex; justify-content: space-between; align-items: center; transition: all 0.3s;
        }
        .key-item:hover { border-color: var(--primary); }
        .key-item button { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 16px; padding: 4px; transition: color 0.3s; }
        .key-item button:hover { color: var(--primary); }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th {
            text-align: left; padding: 14px 18px; font-size: 11px; font-weight: 700;
            color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid var(--border);
        }
        td { padding: 16px 18px; font-size: 13px; border-bottom: 1px solid var(--border); color: var(--text); }
        tr { transition: background 0.2s; }
        tr:hover td { background: var(--bg-hover); }
        .badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 5px 14px; border-radius: 50px; font-size: 11px; font-weight: 800;
        }
        .badge-success { background: rgba(0,255,136,0.1); color: var(--success); border: 1px solid rgba(0,255,136,0.2); }
        .badge-danger { background: rgba(255,68,68,0.1); color: var(--danger); border: 1px solid rgba(255,68,68,0.2); }
        .badge-warning { background: rgba(255,179,71,0.1); color: var(--warning); border: 1px solid rgba(255,179,71,0.2); }
        .badge-info { background: rgba(51,153,255,0.1); color: var(--info); border: 1px solid rgba(51,153,255,0.2); }
        .badge-muted { background: rgba(100,100,100,0.1); color: var(--text-secondary); border: 1px solid rgba(100,100,100,0.2); }
        .key-text {
            font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 12px; color: var(--primary);
            background: rgba(255,107,0,0.08); padding: 4px 10px; border-radius: 6px;
        }
        .device-text {
            font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; color: var(--text-secondary);
            max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .action-btns { display: flex; gap: 6px; }
        .action-btn {
            width: 32px; height: 32px; border-radius: 8px; border: none; cursor: pointer;
            display: flex; align-items: center; justify-content: center; font-size: 13px; transition: all 0.3s;
        }
        .action-btn.copy { background: rgba(51,153,255,0.1); color: var(--info); }
        .action-btn.ban { background: rgba(255,179,71,0.1); color: var(--warning); }
        .action-btn.delete { background: rgba(255,68,68,0.1); color: var(--danger); }
        .action-btn.extend { background: rgba(0,255,136,0.1); color: var(--success); }
        .action-btn.hw { background: rgba(255,107,0,0.1); color: var(--primary); }
        .action-btn:hover { transform: scale(1.15); }
        .log-item { display: flex; align-items: flex-start; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--border); }
        .log-item:last-child { border-bottom: none; }
        .log-time { font-size: 11px; color: var(--text-muted); min-width: 70px; font-family: 'JetBrains Mono', monospace; }
        .log-action {
            font-size: 10px; font-weight: 800; padding: 3px 10px; border-radius: 6px;
            min-width: 100px; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .log-action.success { background: rgba(0,255,136,0.1); color: var(--success); }
        .log-action.fail { background: rgba(255,68,68,0.1); color: var(--danger); }
        .log-action.warn { background: rgba(255,179,71,0.1); color: var(--warning); }
        .log-action.info { background: rgba(51,153,255,0.1); color: var(--info); }
        .log-details { font-size: 13px; color: var(--text-secondary); flex: 1; }
        .log-ip { font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
        .toast-container { position: fixed; top: 24px; right: 24px; z-index: 1000; display: flex; flex-direction: column; gap: 10px; }
        .toast {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
            padding: 18px 24px; display: flex; align-items: center; gap: 14px;
            box-shadow: 0 8px 40px rgba(0,0,0,0.5);
            animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); min-width: 320px; max-width: 450px;
        }
        @keyframes slideIn { from { transform: translateX(120%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .toast.success { border-left: 4px solid var(--success); }
        .toast.error { border-left: 4px solid var(--danger); }
        .toast.warning { border-left: 4px solid var(--warning); }
        .toast-icon { font-size: 22px; }
        .toast.success .toast-icon { color: var(--success); }
        .toast.error .toast-icon { color: var(--danger); }
        .toast.warning .toast-icon { color: var(--warning); }
        .toast-message { font-size: 14px; font-weight: 600; }
        .toast-desc { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
        .modal-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85); display: none; align-items: center; justify-content: center;
            z-index: 1000; backdrop-filter: blur(8px);
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 24px;
            padding: 36px; max-width: 440px; width: 90%; text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes modalIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .modal-icon { width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; margin: 0 auto 20px; }
        .modal-icon.danger { background: rgba(255,68,68,0.1); color: var(--danger); }
        .modal-icon.warning { background: rgba(255,179,71,0.1); color: var(--warning); }
        .modal h3 { font-size: 22px; margin-bottom: 10px; }
        .modal p { color: var(--text-secondary); font-size: 14px; margin-bottom: 28px; line-height: 1.6; }
        .modal-actions { display: flex; gap: 12px; justify-content: center; }
        .modal-actions .btn { flex: 1; justify-content: center; }
        #keySearch {
            background: var(--bg-elevated); border: 2px solid var(--border); color: var(--text);
            padding: 10px 16px; border-radius: 12px; font-size: 13px; outline: none;
            width: 240px; font-family: 'Inter', sans-serif; transition: all 0.3s;
        }
        #keySearch:focus { border-color: var(--primary); }
        #keySearch::placeholder { color: var(--text-muted); }
        .empty-state { text-align: center; padding: 48px; color: var(--text-muted); }
        .empty-state i { font-size: 56px; margin-bottom: 20px; opacity: 0.4; }
        .empty-state p { font-size: 15px; }
        .chart-container { height: 280px; margin: 20px 0; }
        .tier-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }
        .tier-card {
            background: var(--bg-elevated); border: 2px solid var(--border); border-radius: 14px;
            padding: 18px 14px; text-align: center; cursor: pointer; transition: all 0.3s;
        }
        .tier-card:hover { border-color: var(--primary); }
        .tier-card.selected { border-color: var(--primary); background: rgba(255,107,0,0.05); }
        .tier-card .tier-name { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
        .tier-card .tier-price { font-size: 18px; font-weight: 900; color: var(--primary); }
        .tier-card .tier-hours { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
        .menu-toggle {
            display: none; position: fixed; top: 20px; left: 20px; z-index: 200;
            background: var(--bg-card); border: 1px solid var(--border); color: var(--text);
            width: 44px; height: 44px; border-radius: 12px; cursor: pointer; font-size: 18px;
            align-items: center; justify-content: center;
        }
        @media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .tier-grid { grid-template-columns: repeat(3, 1fr); } }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); transition: transform 0.3s; }
            .sidebar.open { transform: translateX(0); }
            .main-content { margin-left: 0; padding: 20px; }
            .menu-toggle { display: flex; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .generate-section { flex-direction: column; }
            .tier-grid { grid-template-columns: repeat(2, 1fr); }
            .top-bar { flex-direction: column; gap: 16px; align-items: flex-start; }
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.5s ease forwards; }
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.3s ease; }
    </style>
</head>
<body>
    <button class="menu-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
    <div class="dashboard">
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-logo"><i class="fas fa-fire"></i><span>FF MOD PRO</span></div>
                <div class="sidebar-subtitle">Developer Control Panel v3.0</div>
            </div>
            <ul class="nav-menu">
                <li class="nav-item">
                    <button class="nav-link active" onclick="showTab('overview')">
                        <i class="fas fa-chart-pie"></i><span>Overview</span>
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('keys')">
                        <i class="fas fa-key"></i><span>Key Management</span>
                        <span class="nav-badge" id="navKeyCount">{{ total_keys }}</span>
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('hwbans')">
                        <i class="fas fa-shield-halved"></i><span>HW Bans</span>
                        <span class="nav-badge" id="navBanCount">{{ hw_ban_count }}</span>
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('logs')">
                        <i class="fas fa-clock-rotate-left"></i><span>System Logs</span>
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('analytics')">
                        <i class="fas fa-chart-line"></i><span>Analytics</span>
                    </button>
                </li>
            </ul>
            <div class="sidebar-footer">
                <a href="/admin/logout" class="logout-btn">
                    <i class="fas fa-arrow-right-from-bracket"></i><span>Logout</span>
                </a>
            </div>
        </aside>

        <main class="main-content">
            <div class="top-bar">
                <h1 class="page-title" id="pageTitle">Dashboard Overview</h1>
                <div class="top-actions">
                    <div class="live-indicator">
                        <span class="live-dot"></span>
                        <span>Live</span>
                    </div>
                    <button class="export-btn" onclick="exportKeys()">
                        <i class="fas fa-download"></i><span>Export</span>
                    </button>
                    <button class="refresh-btn" onclick="refreshData()">
                        <i class="fas fa-rotate"></i><span>Refresh</span>
                    </button>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card total fade-in">
                    <div class="stat-icon"><i class="fas fa-key"></i></div>
                    <div class="stat-value">{{ total_keys }}</div>
                    <div class="stat-label">Total Keys</div>
                    <div class="stat-change up"><i class="fas fa-arrow-up"></i> All time</div>
                </div>
                <div class="stat-card active fade-in">
                    <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-value">{{ active_keys }}</div>
                    <div class="stat-label">Active Keys</div>
                    <div class="stat-change up"><i class="fas fa-bolt"></i> In use</div>
                </div>
                <div class="stat-card expired fade-in">
                    <div class="stat-icon"><i class="fas fa-clock"></i></div>
                    <div class="stat-value">{{ expired_keys }}</div>
                    <div class="stat-label">Expired Keys</div>
                    <div class="stat-change down"><i class="fas fa-arrow-down"></i> Needs cleanup</div>
                </div>
                <div class="stat-card banned fade-in">
                    <div class="stat-icon"><i class="fas fa-ban"></i></div>
                    <div class="stat-value">{{ banned_count }}</div>
                    <div class="stat-label">Banned / HW Banned</div>
                    <div class="stat-change down"><i class="fas fa-shield-halved"></i> Blocked</div>
                </div>
            </div>

            <div id="tab-overview" class="tab-content active">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-plus-circle"></i>Generate New Keys</div>
                    </div>
                    <div class="card-body">
                        <div class="tier-grid">
                            {% for tier_id, tier_info in tiers.items() %}
                            <div class="tier-card" onclick="selectTier('{{ tier_id }}')" data-tier="{{ tier_id }}">
                                <div class="tier-name">{{ tier_info.name }}</div>
                                <div class="tier-price">{{ tier_info.price }}</div>
                                <div class="tier-hours">{% if tier_info.hours > 0 %}{{ tier_info.hours }}h{% else %}Forever{% endif %}</div>
                            </div>
                            {% endfor %}
                        </div>
                        <div class="generate-section">
                            <select class="tier-select" id="tierSelect" onchange="updateTierCards()">
                                {% for tier_id, tier_info in tiers.items() %}
                                <option value="{{ tier_id }}">{{ tier_info.name }} - {{ tier_info.price }}</option>
                                {% endfor %}
                            </select>
                            <input type="number" class="count-input" id="keyCount" value="1" min="1" max="100" placeholder="Count">
                            <button class="btn btn-primary" onclick="generateKeys()">
                                <i class="fas fa-wand-magic-sparkles"></i> Generate Keys
                            </button>
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="cleanupExpired()">
                            <i class="fas fa-broom"></i> Cleanup Expired Keys
                        </button>
                        <div class="generated-keys" id="generatedKeys">
                            <h4><i class="fas fa-key"></i> Generated Keys</h4>
                            <div class="key-list" id="keyList"></div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-clock-rotate-left"></i>Recent Activity</div>
                    </div>
                    <div class="card-body">
                        {% if logs %}
                        {% for log in logs %}
                        <div class="log-item">
                            <div class="log-time">{{ log.timestamp | time_ago }}</div>
                            <div class="log-action {{ log.action | action_class }}">{{ log.action }}</div>
                            <div class="log-details">{{ log.details }}</div>
                            <div class="log-ip">{{ log.ip }}</div>
                        </div>
                        {% endfor %}
                        {% else %}
                        <div class="empty-state"><i class="fas fa-inbox"></i><p>No recent activity</p></div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div id="tab-keys" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-key"></i>All Keys</div>
                        <input type="text" placeholder="Search keys or device..." id="keySearch" onkeyup="searchKeys()">
                    </div>
                    <div class="card-body">
                        <div class="table-container">
                            <table id="keysTable">
                                <thead>
                                    <tr>
                                        <th>Key</th><th>Tier</th><th>Device</th><th>Created</th>
                                        <th>Expires</th><th>Uses</th><th>Last Use</th><th>Status</th><th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="keysTableBody">
                                    {% for key, data in keys.items() %}
                                    <tr data-key="{{ key }}" data-device="{{ data.device_id or '' }}">
                                        <td><span class="key-text">{{ key }}</span></td>
                                        <td><span class="badge badge-warning">{{ tiers[data.tier].name if data.tier in tiers else data.tier }}</span></td>
                                        <td>
                                            {% if data.device_id %}
                                            <span class="device-text" title="{{ data.device_id }}
{{ data.device_name or 'Unknown' }}">{{ data.device_id[:14] }}...</span>
                                            {% else %}
                                            <span style="color: var(--text-muted); font-size: 12px;">Unbound</span>
                                            {% endif %}
                                        </td>
                                        <td style="color: var(--text-secondary); font-size: 12px;">{{ data.created | format_time }}</td>
                                        <td style="color: var(--text-secondary); font-size: 12px;">
                                            {% if data.expires == 9999999999 %}
                                            <span style="color: var(--success); font-weight: 700;">Lifetime</span>
                                            {% else %}
                                            {{ data.expires | format_time }}
                                            {% endif %}
                                        </td>
                                        <td style="text-align: center; font-weight: 700;">{{ data.uses }}</td>
                                        <td style="color: var(--text-secondary); font-size: 12px;">{{ data.last_use | time_ago }}</td>
                                        <td>
                                            {% set status = data | key_status %}
                                            {% if status == 'hw_banned' %}
                                            <span class="badge badge-danger"><i class="fas fa-microchip"></i> HW Banned</span>
                                            {% elif status == 'banned' %}
                                            <span class="badge badge-danger"><i class="fas fa-ban"></i> Banned</span>
                                            {% elif status == 'expired' %}
                                            <span class="badge badge-muted"><i class="fas fa-clock"></i> Expired</span>
                                            {% elif status == 'active' %}
                                            <span class="badge badge-success"><i class="fas fa-check"></i> Active</span>
                                            {% else %}
                                            <span class="badge badge-info"><i class="fas fa-unlock"></i> Unused</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <div class="action-btns">
                                                <button class="action-btn copy" onclick="copyKey('{{ key }}')" title="Copy Key"><i class="fas fa-copy"></i></button>
                                                <button class="action-btn extend" onclick="extendKey('{{ key }}')" title="Extend +24h"><i class="fas fa-plus"></i></button>
                                                {% if data.device_id and not data.hw_banned %}
                                                <button class="action-btn hw" onclick="hwBanDevice('{{ data.device_id }}')" title="HW Ban Device"><i class="fas fa-microchip"></i></button>
                                                {% endif %}
                                                {% if data.banned or data.hw_banned %}
                                                <button class="action-btn ban" onclick="unbanKey('{{ key }}')" title="Unban"><i class="fas fa-check"></i></button>
                                                {% else %}
                                                <button class="action-btn ban" onclick="banKey('{{ key }}')" title="Ban Key"><i class="fas fa-ban"></i></button>
                                                {% endif %}
                                                <button class="action-btn delete" onclick="deleteKey('{{ key }}')" title="Delete"><i class="fas fa-trash"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div id="tab-hwbans" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-shield-halved"></i>Hardware Banned Devices</div>
                        <button class="btn btn-sm btn-secondary" onclick="loadHwBans()">
                            <i class="fas fa-rotate"></i> Refresh
                        </button>
                    </div>
                    <div class="card-body" id="hwBansContainer">
                        <div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>
                    </div>
                </div>
            </div>

            <div id="tab-logs" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-clock-rotate-left"></i>System Logs</div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn btn-sm btn-secondary" onclick="loadLogs()">
                                <i class="fas fa-rotate"></i> Refresh
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="clearLogs()">
                                <i class="fas fa-trash"></i> Clear All
                            </button>
                        </div>
                    </div>
                    <div class="card-body" id="logsContainer">
                        <div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading logs...</p></div>
                    </div>
                </div>
            </div>

            <div id="tab-analytics" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-chart-line"></i>Usage Analytics</div>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="usageChart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-pie-chart"></i>Tier Distribution</div>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="tierChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <div class="toast-container" id="toastContainer"></div>
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal">
            <div class="modal-icon danger" id="modalIcon"><i class="fas fa-triangle-exclamation"></i></div>
            <h3 id="modalTitle">Confirm Action</h3>
            <p id="modalMessage">Are you sure?</p>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-danger" id="modalConfirm">Confirm</button>
            </div>
        </div>
    </div>

    <script>
        var currentTab = 'overview', modalCallback = null, usageChart = null, tierChart = null;

        function showTab(tabName) {
            var links = document.querySelectorAll('.nav-link');
            for (var i = 0; i < links.length; i++) links[i].classList.remove('active');
            var target = event.target.closest('.nav-link');
            if (target) target.classList.add('active');
            var tabs = document.querySelectorAll('.tab-content');
            for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            var titles = { 'overview': 'Dashboard Overview', 'keys': 'Key Management', 'hwbans': 'Hardware Bans', 'logs': 'System Logs', 'analytics': 'Usage Analytics' };
            document.getElementById('pageTitle').textContent = titles[tabName] || 'Dashboard';
            currentTab = tabName;
            if (tabName === 'logs') loadLogs();
            if (tabName === 'hwbans') loadHwBans();
            if (tabName === 'analytics') initCharts();
            document.getElementById('sidebar').classList.remove('open');
        }

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

        function selectTier(tierId) {
            var cards = document.querySelectorAll('.tier-card');
            for (var i = 0; i < cards.length; i++) cards[i].classList.remove('selected');
            var selected = document.querySelector('.tier-card[data-tier="' + tierId + '"]');
            if (selected) selected.classList.add('selected');
            document.getElementById('tierSelect').value = tierId;
        }

        function updateTierCards() { selectTier(document.getElementById('tierSelect').value); }

        function showToast(message, type, desc) {
            var container = document.getElementById('toastContainer');
            var toast = document.createElement('div');
            toast.className = 'toast ' + (type || 'success');
            var icons = { success: '&#10003;', error: '&#10007;', warning: '&#9888;' };
            var icon = icons[type] || '&#8505;';
            toast.innerHTML = '<span class="toast-icon">' + icon + '</span><div><div class="toast-message">' + message + '</div>' + (desc ? '<div class="toast-desc">' + desc + '</div>' : '') + '</div>';
            container.appendChild(toast);
            setTimeout(function() { toast.style.opacity = '0'; setTimeout(function() { toast.remove(); }, 300); }, 4000);
        }

        function showModal(title, message, iconClass, cb) {
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('modalMessage').textContent = message;
            document.getElementById('modalIcon').className = 'modal-icon ' + (iconClass || 'danger');
            modalCallback = cb;
            document.getElementById('modalOverlay').classList.add('show');
        }

        function closeModal() { document.getElementById('modalOverlay').classList.remove('show'); modalCallback = null; }

        document.getElementById('modalConfirm').onclick = function() { if (modalCallback) modalCallback(); closeModal(); };

        async function apiCall(endpoint, method, data) {
            try {
                var opts = { method: method || 'GET', headers: { 'Content-Type': 'application/json' } };
                if (data) opts.body = JSON.stringify(data);
                var response = await fetch(endpoint, opts);
                return await response.json();
            } catch (error) { showToast('Network error', 'error'); return null; }
        }

        async function generateKeys() {
            var tier = document.getElementById('tierSelect').value;
            var count = parseInt(document.getElementById('keyCount').value) || 1;
            console.log('Generating keys:', tier, count);
            var result = await apiCall('/api/generate-key', 'POST', { tier: tier, count: count });
            console.log('Result:', result);
            if (result && result.keys) {
                var html = '';
                for (var i = 0; i < result.keys.length; i++) {
                    var k = result.keys[i];
                    html += '<div class="key-item"><span>' + k + '</span><button onclick="copyToClipboard(&quot;' + k + '&quot;)" title="Copy"><i class="fas fa-copy"></i></button></div>';
                }
                document.getElementById('keyList').innerHTML = html;
                document.getElementById('generatedKeys').classList.add('show');
                showToast('Generated ' + result.count + ' keys!', 'success', 'Tier: ' + tier.toUpperCase());
                setTimeout(function() { window.location.reload(); }, 1500);
            } else {
                showToast('Failed to generate keys', 'error');
            }
        }

        async function copyKey(key) { await copyToClipboard(key); showToast('Key copied to clipboard!', 'success'); }

        async function extendKey(key) {
            var result = await apiCall('/api/extend-key', 'POST', { key: key, hours: 24 });
            if (result && result.success) { showToast('Key extended +24h!', 'success'); refreshData(); }
        }

        async function banKey(key) {
            showModal('Ban Key', 'Are you sure you want to ban key:
' + key + '?', 'warning', async function() {
                var result = await apiCall('/api/ban-key', 'POST', { key: key });
                if (result && result.success) { showToast('Key banned!', 'success'); refreshData(); }
            });
        }

        async function unbanKey(key) {
            var result = await apiCall('/api/unban-key', 'POST', { key: key });
            if (result && result.success) { showToast('Key unbanned!', 'success'); refreshData(); }
        }

        async function hwBanDevice(deviceId) {
            showModal('Hardware Ban', 'Ban device permanently:
' + deviceId + '?', 'danger', async function() {
                var result = await apiCall('/api/hw-ban', 'POST', { device_id: deviceId });
                if (result && result.success) { showToast('Device hardware banned!', 'success'); refreshData(); }
            });
        }

        async function deleteKey(key) {
            showModal('Delete Key', 'Permanently delete key:
' + key + '?

This action cannot be undone!', 'danger', async function() {
                var result = await apiCall('/api/delete-key', 'POST', { key: key });
                if (result && result.success) { showToast('Key deleted!', 'success'); refreshData(); }
            });
        }

        async function cleanupExpired() {
            showModal('Cleanup Expired', 'Delete all expired keys?
This action cannot be undone!', 'warning', async function() {
                var result = await apiCall('/api/cleanup', 'POST');
                if (result) { showToast('Deleted ' + result.deleted + ' expired keys!', 'success'); refreshData(); }
            });
        }

        function refreshData() { window.location.reload(); }

        async function loadLogs() {
            var container = document.getElementById('logsContainer');
            container.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>';
            var result = await apiCall('/api/logs');
            if (result && result.logs) {
                if (result.logs.length === 0) {
                    container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No logs found</p></div>';
                } else {
                    var html = '';
                    for (var i = 0; i < result.logs.length; i++) {
                        var l = result.logs[i];
                        var cls = l.action.indexOf('SUCCESS') !== -1 || l.action.indexOf('GENERATE') !== -1 ? 'success'
                            : l.action.indexOf('FAIL') !== -1 || l.action.indexOf('DELETE') !== -1 ? 'fail'
                            : l.action.indexOf('BAN') !== -1 ? 'warn' : 'info';
                        html += '<div class="log-item"><div class="log-time">' + new Date(l.timestamp * 1000).toLocaleTimeString() + '</div><div class="log-action ' + cls + '">' + l.action + '</div><div class="log-details">' + l.details + '</div><div class="log-ip">' + l.ip + '</div></div>';
                    }
                    container.innerHTML = html;
                }
            }
        }

        async function loadHwBans() {
            var container = document.getElementById('hwBansContainer');
            container.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>';
            var result = await apiCall('/api/hw-bans');
            if (result && result.bans) {
                if (result.bans.length === 0) {
                    container.innerHTML = '<div class="empty-state"><i class="fas fa-shield-halved"></i><p>No hardware bans</p></div>';
                } else {
                    var html = '<div class="table-container"><table><thead><tr><th>Device ID</th><th>Banned At</th><th>Reason</th><th>Actions</th></tr></thead><tbody>';
                    for (var i = 0; i < result.bans.length; i++) {
                        var b = result.bans[i];
                        html += '<tr><td><span class="device-text">' + b.device_id + '</span></td><td style="color: var(--text-secondary); font-size: 12px;">' + new Date(b.banned_at * 1000).toLocaleString() + '</td><td style="color: var(--text-secondary); font-size: 12px;">' + (b.reason || 'Manual ban') + '</td><td><button class="action-btn extend" onclick="unbanHwDevice('' + b.device_id + '')" title="Unban Device"><i class="fas fa-check"></i></button></td></tr>';
                    }
                    html += '</tbody></table></div>';
                    container.innerHTML = html;
                }
            }
        }

        async function unbanHwDevice(deviceId) {
            showModal('Unban Device', 'Remove hardware ban for:
' + deviceId + '?', 'warning', async function() {
                var result = await apiCall('/api/hw-unban', 'POST', { device_id: deviceId });
                if (result && result.success) { showToast('Device unbanned!', 'success'); loadHwBans(); refreshData(); }
            });
        }

        async function clearLogs() {
            showModal('Clear Logs', 'Delete all system logs?
This action cannot be undone!', 'danger', async function() {
                var result = await apiCall('/api/clear-logs', 'POST');
                if (result && result.success) { showToast('All logs cleared!', 'success'); loadLogs(); }
            });
        }

        function searchKeys() {
            var q = document.getElementById('keySearch').value.toLowerCase();
            var rows = document.querySelectorAll('#keysTableBody tr');
            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                var key = row.getAttribute('data-key').toLowerCase();
                var device = (row.getAttribute('data-device') || '').toLowerCase();
                row.style.display = (key.indexOf(q) !== -1 || device.indexOf(q) !== -1) ? '' : 'none';
            }
        }

        function exportKeys() {
            apiCall('/api/keys').then(function(result) {
                if (result && result.keys) {
                    var data = '';
                    for (var i = 0; i < result.keys.length; i++) {
                        var k = result.keys[i];
                        data += k.key + ',' + k.tier + ',' + (k.device_id || 'Unbound') + ',' + k.uses + ',' + (k.banned ? 'Banned' : 'Active') + '\n';
                    }
                    var csv = 'Key,Tier,Device,Uses,Status\n' + data;
                    var blob = new Blob([csv], { type: 'text/csv' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url; a.download = 'ff_keys_' + new Date().toISOString().slice(0,10) + '.csv'; a.click();
                    showToast('Keys exported!', 'success');
                }
            });
        }

        async function copyToClipboard(text) {
            try { await navigator.clipboard.writeText(text); }
            catch(e) { var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); }
        }

        function initCharts() {
            if (usageChart) { usageChart.destroy(); tierChart.destroy(); }
            apiCall('/api/stats').then(function(stats) {
                if (!stats) return;
                var ctx1 = document.getElementById('usageChart').getContext('2d');
                usageChart = new Chart(ctx1, {
                    type: 'line',
                    data: {
                        labels: ['Total', 'Active', 'Expired', 'Banned'],
                        datasets: [{
                            label: 'Keys',
                            data: [stats.total, stats.active, stats.expired, stats.banned],
                            borderColor: '#FF6B00',
                            backgroundColor: 'rgba(255,107,0,0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#FF6B00',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 6
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#999' } },
                            x: { grid: { display: false }, ticks: { color: '#999' } }
                        }
                    }
                });
                apiCall('/api/keys').then(function(result) {
                    if (!result || !result.keys) return;
                    var tierCounts = {};
                    for (var i = 0; i < result.keys.length; i++) {
                        var t = result.keys[i].tier;
                        tierCounts[t] = (tierCounts[t] || 0) + 1;
                    }
                    var labels = Object.keys(tierCounts);
                    var values = Object.values(tierCounts);
                    var ctx2 = document.getElementById('tierChart').getContext('2d');
                    tierChart = new Chart(ctx2, {
                        type: 'doughnut',
                        data: {
                            labels: labels,
                            datasets: [{
                                data: values,
                                backgroundColor: ['#FF6B00', '#FF8533', '#FFB347', '#00FF88', '#3399FF'],
                                borderWidth: 0,
                                hoverOffset: 10
                            }]
                        },
                        options: {
                            responsive: true, maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'right', labels: { color: '#999', padding: 20, font: { size: 12 } } }
                            },
                            cutout: '65%'
                        }
                    });
                });
            });
        }

        setInterval(function() { if (currentTab === 'logs') loadLogs(); }, 30000);

        document.addEventListener('click', function(e) {
            var sidebar = document.getElementById('sidebar');
            var toggle = document.querySelector('.menu-toggle');
            if (window.innerWidth <= 768 && sidebar.classList.contains('open') && !sidebar.contains(e.target) && !toggle.contains(e.target))
                sidebar.classList.remove('open');
        });
    </script>
</body>
</html>"""

# ==================== ROUTES ====================

@app.route('/')
def root():
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_login():
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template_string(ADMIN_LOGIN_HTML)

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin'] = True
        add_log('ADMIN_LOGIN', "Admin logged in")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(ADMIN_LOGIN_HTML, error='Invalid credentials')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    keys = load_keys()
    logs = load_logs()
    hw_bans = load_hw_bans()
    now = int(time.time())
    total = len(keys)
    active = sum(1 for k in keys.values() if is_key_valid(k))
    expired = sum(1 for k in keys.values() if k['expires'] != 9999999999 and k['expires'] < now)
    banned = sum(1 for k in keys.values() if k.get('banned') or k.get('hw_banned'))
    recent_logs = logs[-20:][::-1] if logs else []
    return render_template_string(ADMIN_DASHBOARD_HTML,
                         total_keys=total, active_keys=active,
                         expired_keys=expired, banned_count=banned,
                         hw_ban_count=len(hw_bans),
                         keys=keys, logs=recent_logs, tiers=TIERS)

# ==================== API ====================

@app.route('/verify', methods=['POST'])
def verify():
    keys = load_keys()
    hw_bans = load_hw_bans()
    key = request.form.get('key', '').strip().upper()
    device_id = request.form.get('device_id', '').strip()
    device_name = request.form.get('device_name', 'Unknown').strip()

    if any(b['device_id'] == device_id for b in hw_bans):
        add_log('VERIFY_HW_BANNED', f"HW banned device tried: {device_id}")
        return jsonify({"valid": False, "message": "Device hardware banned!"})

    if not key or key not in keys:
        add_log('VERIFY_FAIL', f"Invalid key: {key}")
        return jsonify({"valid": False, "message": "Invalid key!"})

    key_data = keys[key]
    if key_data.get('banned'):
        return jsonify({"valid": False, "message": "Key banned!"})
    if key_data.get('hw_banned'):
        return jsonify({"valid": False, "message": "Key hardware banned!"})
    if not is_key_valid(key_data):
        add_log('VERIFY_EXPIRED', f"Expired key: {key}")
        return jsonify({"valid": False, "message": "Key expired!"})
    if key_data.get('device_id') and key_data['device_id'] != device_id:
        add_log('VERIFY_DEVICE_MISMATCH', f"Key {key} used on different device")
        return jsonify({"valid": False, "message": "Key used on another device!"})

    if not key_data.get('device_id'):
        keys[key]['device_id'] = device_id
        keys[key]['device_name'] = device_name
    keys[key]['uses'] += 1
    keys[key]['last_use'] = int(time.time())
    save_keys(keys)
    add_log('VERIFY_SUCCESS', f"Key {key} verified")
    return jsonify({
        "valid": True,
        "expires": key_data['expires'] * 1000 if key_data['expires'] != 9999999999 else 0,
        "tier": key_data['tier'],
        "uses": keys[key]['uses'],
        "message": "Success!"
    })

@app.route('/check-key', methods=['POST'])
def check_key():
    keys = load_keys()
    hw_bans = load_hw_bans()
    key = request.form.get('key', '').strip().upper()
    device_id = request.form.get('device_id', '').strip()

    if any(b['device_id'] == device_id for b in hw_bans):
        return jsonify({"valid": False})

    if not key or key not in keys:
        return jsonify({"valid": False})

    key_data = keys[key]
    if key_data.get('banned') or key_data.get('hw_banned') or not is_key_valid(key_data):
        return jsonify({"valid": False})
    if key_data.get('device_id') and key_data['device_id'] != device_id:
        return jsonify({"valid": False})
    return jsonify({"valid": True})

@app.route('/api/generate-key', methods=['POST'])
@login_required
def api_generate_key():
    data = request.get_json()
    tier = data.get('tier', '24h')
    count = min(data.get('count', 1), 100)
    if tier not in TIERS:
        return jsonify({"error": "Invalid tier"}), 400
    keys = load_keys()
    generated = []
    for _ in range(count):
        key = f"FF-PRO-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"
        now = int(time.time())
        hours = TIERS[tier]['hours']
        expires = now + (hours * 3600) if hours > 0 else 9999999999
        keys[key] = {
            "key": key, "tier": tier, "created": now, "expires": expires,
            "device_id": None, "device_name": None, "uses": 0,
            "last_use": None, "banned": False, "hw_banned": False
        }
        generated.append(key)
    save_keys(keys)
    add_log('GENERATE_KEYS', f"Generated {count} {tier} keys")
    return jsonify({"keys": generated, "count": count})

@app.route('/api/delete-key', methods=['POST'])
@login_required
def api_delete_key():
    data = request.get_json()
    key = data.get('key', '')
    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)
        add_log('DELETE_KEY', f"Deleted key: {key}")
    return jsonify({"success": True})

@app.route('/api/ban-key', methods=['POST'])
@login_required
def api_ban_key():
    data = request.get_json()
    key = data.get('key', '')
    keys = load_keys()
    if key in keys:
        keys[key]['banned'] = True
        save_keys(keys)
        add_log('BAN_KEY', f"Banned key: {key}")
    return jsonify({"success": True})

@app.route('/api/unban-key', methods=['POST'])
@login_required
def api_unban_key():
    data = request.get_json()
    key = data.get('key', '')
    keys = load_keys()
    if key in keys:
        keys[key]['banned'] = False
        keys[key]['hw_banned'] = False
        save_keys(keys)
        add_log('UNBAN_KEY', f"Unbanned key: {key}")
    return jsonify({"success": True})

@app.route('/api/extend-key', methods=['POST'])
@login_required
def api_extend_key():
    data = request.get_json()
    key = data.get('key', '')
    hours = data.get('hours', 24)
    keys = load_keys()
    if key in keys:
        if keys[key]['expires'] != 9999999999:
            keys[key]['expires'] += (hours * 3600)
        save_keys(keys)
        add_log('EXTEND_KEY', f"Extended key {key} by {hours}h")
    return jsonify({"success": True})

@app.route('/api/hw-ban', methods=['POST'])
@login_required
def api_hw_ban():
    data = request.get_json()
    device_id = data.get('device_id', '')
    if device_id:
        hw_bans = load_hw_bans()
        if not any(b['device_id'] == device_id for b in hw_bans):
            hw_bans.append({
                'device_id': device_id,
                'banned_at': int(time.time()),
                'reason': data.get('reason', 'Manual ban')
            })
            save_hw_bans(hw_bans)
            keys = load_keys()
            for k, v in keys.items():
                if v.get('device_id') == device_id:
                    v['hw_banned'] = True
            save_keys(keys)
            add_log('HW_BAN', f"HW banned device: {device_id}")
    return jsonify({"success": True})

@app.route('/api/hw-unban', methods=['POST'])
@login_required
def api_hw_unban():
    data = request.get_json()
    device_id = data.get('device_id', '')
    if device_id:
        hw_bans = load_hw_bans()
        hw_bans = [b for b in hw_bans if b['device_id'] != device_id]
        save_hw_bans(hw_bans)
        keys = load_keys()
        for k, v in keys.items():
            if v.get('device_id') == device_id:
                v['hw_banned'] = False
        save_keys(keys)
        add_log('HW_UNBAN', f"HW unbanned device: {device_id}")
    return jsonify({"success": True})

@app.route('/api/cleanup', methods=['POST'])
@login_required
def api_cleanup():
    keys = load_keys()
    now = int(time.time())
    expired = [k for k, v in keys.items() if v['expires'] != 9999999999 and now > v['expires']]
    for k in expired:
        del keys[k]
    save_keys(keys)
    add_log('CLEANUP', f"Deleted {len(expired)} expired keys")
    return jsonify({"deleted": len(expired)})

@app.route('/api/keys')
@login_required
def api_keys():
    return jsonify({"keys": list(load_keys().values())})

@app.route('/api/logs')
@login_required
def api_logs():
    logs = load_logs()
    return jsonify({"logs": logs[-100:][::-1]})

@app.route('/api/hw-bans')
@login_required
def api_hw_bans():
    return jsonify({"bans": load_hw_bans()})

@app.route('/api/clear-logs', methods=['POST'])
@login_required
def api_clear_logs():
    save_logs([])
    add_log('CLEAR_LOGS', "All logs cleared")
    return jsonify({"success": True})

@app.route('/api/stats')
@login_required
def api_stats():
    keys = load_keys()
    now = int(time.time())
    return jsonify({
        'total': len(keys),
        'active': sum(1 for k in keys.values() if is_key_valid(k)),
        'expired': sum(1 for k in keys.values() if k['expires'] != 9999999999 and k['expires'] < now),
        'banned': sum(1 for k in keys.values() if k.get('banned') or k.get('hw_banned'))
    })

# ==================== TEMPLATE FILTERS ====================
@app.template_filter('format_time')
def _format_time(timestamp):
    return format_time(timestamp)

@app.template_filter('time_ago')
def _time_ago(timestamp):
    return time_ago(timestamp)

@app.template_filter('action_class')
def _action_class(action):
    if 'SUCCESS' in action or 'GENERATE' in action:
        return 'success'
    elif 'FAIL' in action or 'DELETE' in action:
        return 'fail'
    elif 'BAN' in action:
        return 'warn'
    return 'info'

@app.template_filter('key_status')
def _key_status(key_data):
    return get_key_status(key_data)

@app.context_processor
def inject_now():
    return {'now': int(time.time())}

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('admin_login'))

# ==================== MAIN ====================
if __name__ == '__main__':
    app.run(debug=True)
