from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
import secrets
import time
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ==================== CONFIG ====================
ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin123')
KEYS_FILE = '/tmp/keys.json'
LOGS_FILE = '/tmp/logs.json'

TIERS = {
    '1h': {'name': '1 Hour', 'hours': 1},
    '24h': {'name': '1 Day', 'hours': 24},
    '7d': {'name': '1 Week', 'hours': 168},
    '30d': {'name': '1 Month', 'hours': 720},
    'lifetime': {'name': 'Lifetime', 'hours': 0}
}

# ==================== HELPERS ====================
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

def load_keys():
    return load_json(KEYS_FILE, {})

def save_keys(keys):
    save_json(KEYS_FILE, keys)

def load_logs():
    return load_json(LOGS_FILE, [])

def save_logs(logs):
    save_json(LOGS_FILE, logs)

def add_log(action, details=""):
    logs = load_logs()
    logs.append({
        'timestamp': int(time.time()),
        'action': action,
        'details': details,
        'ip': request.remote_addr or 'unknown'
    })
    save_logs(logs[-500:])

def is_key_valid(key_data):
    if not key_data or key_data.get('banned'):
        return False
    if key_data['expires'] != 9999999999 and int(time.time()) > key_data['expires']:
        return False
    return True

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== HTML TEMPLATES ====================

INDEX_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FF Mod Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF6B00;
            --bg: #0a0a0a;
            --bg-card: #111111;
            --text: #ffffff;
            --text-secondary: #888888;
            --text-muted: #555555;
            --success: #00FF88;
            --border: #222222;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
        }
        .bg-animation {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(ellipse at 50% 0%, rgba(255,107,0,0.15) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }
        .particles {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            z-index: 0;
        }
        .particle {
            position: absolute;
            width: 2px; height: 2px;
            background: var(--primary);
            border-radius: 50%;
            animation: float 15s infinite;
            opacity: 0.3;
        }
        @keyframes float {
            0% { transform: translateY(100vh) scale(0); opacity: 0; }
            50% { opacity: 0.5; }
            100% { transform: translateY(-100vh) scale(1); opacity: 0; }
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            position: relative;
            z-index: 1;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo-icon { font-size: 28px; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 900;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .nav-links {
            display: flex;
            gap: 30px;
        }
        .nav-links a {
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: color 0.3s;
        }
        .nav-links a:hover { color: var(--primary); }
        .admin-btn {
            background: var(--gradient);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 20px rgba(255,107,0,0.3);
        }
        .admin-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255,107,0,0.4);
        }
        .hero {
            text-align: center;
            padding: 80px 20px 60px;
            max-width: 900px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,107,0,0.1);
            border: 1px solid rgba(255,107,0,0.3);
            padding: 8px 20px;
            border-radius: 50px;
            font-size: 13px;
            color: var(--primary);
            margin-bottom: 30px;
        }
        .hero-badge .dot {
            width: 8px; height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        .hero h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 56px;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #fff 0%, var(--primary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero p {
            font-size: 18px;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 40px;
            line-height: 1.6;
        }
        .hero-buttons {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .btn-primary {
            background: var(--gradient);
            color: white;
            border: none;
            padding: 16px 40px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 30px rgba(255,107,0,0.3);
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 40px rgba(255,107,0,0.4);
        }
        .btn-secondary {
            background: transparent;
            color: var(--text);
            border: 1px solid var(--border);
            padding: 16px 40px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        .btn-secondary:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        .features {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }
        .section-title {
            text-align: center;
            margin-bottom: 50px;
        }
        .section-title h2 {
            font-family: 'Orbitron', sans-serif;
            font-size: 36px;
            margin-bottom: 12px;
        }
        .section-title p {
            color: var(--text-secondary);
            font-size: 16px;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
        }
        .feature-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        .feature-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: var(--gradient);
            transform: scaleX(0);
            transition: transform 0.3s;
        }
        .feature-card:hover::before {
            transform: scaleX(1);
        }
        .feature-card:hover {
            border-color: var(--primary);
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .feature-icon {
            width: 50px; height: 50px;
            background: rgba(255,107,0,0.1);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-bottom: 20px;
        }
        .feature-card h3 {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .feature-card p {
            color: var(--text-secondary);
            font-size: 14px;
            line-height: 1.6;
        }
        .pricing {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }
        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }
        .pricing-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px 24px;
            text-align: center;
            transition: all 0.3s;
            position: relative;
        }
        .pricing-card.popular {
            border-color: var(--primary);
            background: linear-gradient(180deg, rgba(255,107,0,0.05) 0%, var(--bg-card) 100%);
        }
        .popular-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--gradient);
            color: white;
            padding: 4px 16px;
            border-radius: 50px;
            font-size: 11px;
            font-weight: 700;
        }
        .pricing-card h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-secondary);
        }
        .price {
            font-family: 'Orbitron', sans-serif;
            font-size: 36px;
            font-weight: 900;
            color: var(--primary);
            margin: 16px 0;
        }
        .price span {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 400;
        }
        .pricing-card ul {
            list-style: none;
            margin: 20px 0;
            text-align: left;
        }
        .pricing-card ul li {
            padding: 6px 0;
            font-size: 13px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pricing-card ul li::before {
            content: '✓';
            color: var(--success);
            font-weight: 700;
        }
        .footer {
            text-align: center;
            padding: 40px 20px;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 13px;
            position: relative;
            z-index: 1;
        }
        @media (max-width: 768px) {
            .hero h1 { font-size: 36px; }
            .nav-links { display: none; }
            .header { padding: 15px 20px; }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <div class="particles" id="particles"></div>
    <header class="header">
        <div class="logo">
            <div class="logo-icon">🔥</div>
            <div class="logo-text">FF MOD PRO</div>
        </div>
        <nav class="nav-links">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="/admin">Admin</a>
        </nav>
        <a href="/admin" class="admin-btn">🔐 Admin Panel</a>
    </header>
    <section class="hero">
        <div class="hero-badge">
            <span class="dot"></span>
            v2.0 Key System Active
        </div>
        <h1>Free Fire Mod Menu<br>Key System</h1>
        <p>Professional access control system with device binding, expiration management, and real-time monitoring.</p>
        <div class="hero-buttons">
            <a href="#pricing" class="btn-primary">
                <span>⚡</span> Get Access Key
            </a>
            <a href="/admin" class="btn-secondary">
                <span>🎛️</span> Admin Dashboard
            </a>
        </div>
    </section>
    <section class="features" id="features">
        <div class="section-title">
            <h2>System Features</h2>
            <p>Enterprise-grade security for your mod menu</p>
        </div>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">🔐</div>
                <h3>Device Binding</h3>
                <p>Each key is locked to a single device.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⏱️</div>
                <h3>Time-Limited Access</h3>
                <p>Flexible duration from 1 hour to lifetime.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h3>Real-Time Analytics</h3>
                <p>Monitor key usage from admin dashboard.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🚫</div>
                <h3>Ban System</h3>
                <p>Instantly ban keys or devices.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔄</div>
                <h3>Auto-Check</h3>
                <p>Periodic validation during gameplay.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📱</div>
                <h3>Android Integration</h3>
                <p>Seamless Sketchware Pro setup.</p>
            </div>
        </div>
    </section>
    <section class="pricing" id="pricing">
        <div class="section-title">
            <h2>Access Plans</h2>
            <p>Choose the plan that fits your needs</p>
        </div>
        <div class="pricing-grid">
            <div class="pricing-card"><h3>1 Hour Trial</h3><div class="price">$0.50 <span>/hour</span></div><ul><li>Full feature access</li><li>Single device</li></ul></div>
            <div class="pricing-card"><h3>1 Day Pass</h3><div class="price">$2.00 <span>/day</span></div><ul><li>24 hours access</li><li>Single device</li></ul></div>
            <div class="pricing-card popular"><div class="popular-badge">POPULAR</div><h3>1 Week</h3><div class="price">$8.00 <span>/week</span></div><ul><li>7 days access</li><li>Premium support</li></ul></div>
            <div class="pricing-card"><h3>1 Month</h3><div class="price">$25.00 <span>/month</span></div><ul><li>30 days access</li><li>VIP support</li></ul></div>
            <div class="pricing-card" style="border-color: var(--success);"><h3>Lifetime</h3><div class="price" style="color: var(--success);">$50.00 <span>/once</span></div><ul><li>Permanent access</li><li>All features</li></ul></div>
        </div>
    </section>
    <footer class="footer">
        <p>FF Mod Pro Key System v2.0 | Professional Access Control</p>
        <p style="margin-top: 8px; font-size: 11px;">Contact admin to purchase keys</p>
    </footer>
    <script>
        const particlesContainer = document.getElementById('particles');
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 15 + 's';
            particle.style.animationDuration = (10 + Math.random() * 20) + 's';
            particlesContainer.appendChild(particle);
        }
    </script>
</body>
</html>'''

GET_KEY_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Get Key - FF Mod Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF6B00;
            --bg: #0a0a0a;
            --bg-card: #111111;
            --bg-elevated: #1a1a1a;
            --text: #ffffff;
            --text-secondary: #888888;
            --border: #222222;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container { max-width: 500px; width: 100%; text-align: center; }
        .logo {
            font-family: 'Orbitron', sans-serif;
            font-size: 28px;
            font-weight: 900;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle { color: var(--text-secondary); font-size: 13px; margin-bottom: 40px; }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 40px;
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: var(--gradient);
        }
        .device-box {
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }
        .device-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }
        .device-id {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            color: var(--primary);
            word-break: break-all;
            cursor: pointer;
            padding: 10px;
            border-radius: 8px;
            transition: background 0.3s;
        }
        .device-id:hover { background: rgba(255,107,0,0.1); }
        .instructions { text-align: left; margin-bottom: 30px; }
        .instructions h3 { font-size: 14px; margin-bottom: 15px; }
        .instructions ol { padding-left: 20px; color: var(--text-secondary); font-size: 13px; line-height: 2; }
        .instructions ol li::marker { color: var(--primary); font-weight: 700; }
        .warning { margin-top: 25px; padding: 15px; background: rgba(255,68,68,0.1); border: 1px solid rgba(255,68,68,0.3); border-radius: 10px; font-size: 12px; color: #ff4444; }
        .back-link { display: inline-block; margin-top: 25px; color: var(--text-secondary); text-decoration: none; font-size: 13px; }
        .back-link:hover { color: var(--primary); }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🔥 FF MOD PRO</div>
        <div class="subtitle">Key Authentication System</div>
        <div class="card">
            <div class="device-box">
                <div class="device-label">Your Device ID</div>
                <div class="device-id" id="deviceId" onclick="copyDeviceId()">{{ device }}</div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-top: 8px;">Tap to copy</div>
            </div>
            <div class="instructions">
                <h3>How to get your key:</h3>
                <ol>
                    <li>Copy your Device ID above</li>
                    <li>Send it to the developer</li>
                    <li>Receive your unique access key</li>
                    <li>Enter the key in the app</li>
                </ol>
            </div>
            <div class="warning"><strong>⚠️ Important:</strong><br>Your key will be permanently bound to this device.</div>
        </div>
        <a href="/" class="back-link">← Back to Home</a>
    </div>
    <script>
        function copyDeviceId() {
            const el = document.getElementById('deviceId');
            const text = el.textContent;
            navigator.clipboard.writeText(text).then(() => {
                el.style.background = 'rgba(0,255,136,0.2)';
                el.style.color = '#00FF88';
                el.textContent = '✓ Copied!';
                setTimeout(() => {
                    el.style.background = 'transparent';
                    el.style.color = '#FF6B00';
                    el.textContent = text;
                }, 1500);
            });
        }
    </script>
</body>
</html>'''

ADMIN_LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - FF Mod Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF6B00;
            --bg: #0a0a0a;
            --bg-card: #111111;
            --bg-elevated: #1a1a1a;
            --text: #ffffff;
            --text-secondary: #888888;
            --danger: #ff4444;
            --border: #222222;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 50%, #FFB347 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-container { width: 100%; max-width: 420px; }
        .login-header { text-align: center; margin-bottom: 40px; }
        .login-header .logo {
            font-family: 'Orbitron', sans-serif;
            font-size: 28px;
            font-weight: 900;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .login-header p { color: var(--text-secondary); font-size: 14px; }
        .login-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 40px;
            position: relative;
            overflow: hidden;
        }
        .login-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: var(--gradient);
        }
        .form-group { margin-bottom: 24px; }
        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .form-group input {
            width: 100%;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 14px 16px;
            border-radius: 12px;
            font-size: 15px;
            outline: none;
        }
        .form-group input:focus { border-color: var(--primary); }
        .login-btn {
            width: 100%;
            background: var(--gradient);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }
        .login-btn:hover { transform: translateY(-2px); }
        .error-message {
            background: rgba(255,68,68,0.1);
            border: 1px solid rgba(255,68,68,0.3);
            color: var(--danger);
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 14px;
            margin-bottom: 20px;
            display: none;
        }
        .error-message.show { display: block; }
        .back-link { display: block; text-align: center; margin-top: 25px; color: var(--text-secondary); text-decoration: none; font-size: 14px; }
        .back-link:hover { color: var(--primary); }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="logo">🔐 ADMIN PANEL</div>
            <p>FF Mod Pro Key Management System</p>
        </div>
        <div class="login-card">
            {% if error %}
            <div class="error-message show">⚠️ {{ error }}</div>
            {% endif %}
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" placeholder="Enter username" required autofocus>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter password" required>
                </div>
                <button type="submit" class="login-btn">🔐 Secure Login</button>
            </form>
        </div>
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>'''

# Using simplified dashboard for Vercel
ADMIN_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dev Panel - FF Mod Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --primary: #FF6B00;
            --bg: #0a0a0a;
            --bg-card: #111111;
            --bg-elevated: #1a1a1a;
            --bg-hover: #222222;
            --text: #ffffff;
            --text-secondary: #888888;
            --text-muted: #555555;
            --success: #00FF88;
            --danger: #ff4444;
            --warning: #FFB347;
            --border: #1a1a1a;
            --border-light: #222222;
            --gradient: linear-gradient(135deg, #FF6B00 0%, #FF8533 50%, #FFB347 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }
        .dashboard { display: flex; min-height: 100vh; }
        .sidebar {
            width: 260px; background: #080808; border-right: 1px solid var(--border);
            padding: 24px 0; position: fixed; height: 100vh; overflow-y: auto; z-index: 100;
        }
        .sidebar-header { padding: 0 24px 24px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
        .sidebar-logo {
            font-family: 'Orbitron', sans-serif; font-size: 20px; font-weight: 900;
            background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            display: flex; align-items: center; gap: 10px;
        }
        .sidebar-logo i { font-size: 24px; -webkit-text-fill-color: var(--primary); }
        .sidebar-subtitle { font-size: 11px; color: var(--text-muted); margin-top: 4px; letter-spacing: 1px; }
        .nav-menu { list-style: none; padding: 0 12px; }
        .nav-item { margin-bottom: 4px; }
        .nav-link {
            display: flex; align-items: center; gap: 12px; padding: 12px 16px;
            color: var(--text-secondary); border-radius: 10px; font-size: 14px; font-weight: 500;
            cursor: pointer; border: none; background: none; width: 100%; text-align: left;
        }
        .nav-link:hover, .nav-link.active { background: var(--bg-elevated); color: var(--primary); }
        .nav-link i { width: 20px; text-align: center; font-size: 16px; }
        .sidebar-footer {
            position: absolute; bottom: 0; left: 0; right: 0; padding: 20px 24px; border-top: 1px solid var(--border);
        }
        .logout-btn { display: flex; align-items: center; gap: 10px; color: var(--danger); text-decoration: none; font-size: 14px; font-weight: 600; }
        .main-content { flex: 1; margin-left: 260px; padding: 24px 32px; min-height: 100vh; }
        .top-bar {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;
            padding-bottom: 20px; border-bottom: 1px solid var(--border);
        }
        .page-title { font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; }
        .refresh-btn {
            background: var(--bg-elevated); border: 1px solid var(--border-light); color: var(--text-secondary);
            padding: 10px 16px; border-radius: 10px; cursor: pointer; font-size: 13px;
            display: flex; align-items: center; gap: 8px;
        }
        .refresh-btn:hover { border-color: var(--primary); color: var(--primary); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 32px; }
        .stat-card {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
            padding: 24px; position: relative; overflow: hidden;
        }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }
        .stat-card.total::before { background: var(--primary); }
        .stat-card.active::before { background: var(--success); }
        .stat-card.expired::before { background: var(--danger); }
        .stat-card.banned::before { background: var(--warning); }
        .stat-icon {
            width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center;
            justify-content: center; font-size: 20px; margin-bottom: 16px;
        }
        .stat-card.total .stat-icon { background: rgba(255,107,0,0.1); color: var(--primary); }
        .stat-card.active .stat-icon { background: rgba(0,255,136,0.1); color: var(--success); }
        .stat-card.expired .stat-icon { background: rgba(255,68,68,0.1); color: var(--danger); }
        .stat-card.banned .stat-icon { background: rgba(255,179,71,0.1); color: var(--warning); }
        .stat-value { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 900; margin-bottom: 4px; }
        .stat-card.total .stat-value { color: var(--primary); }
        .stat-card.active .stat-value { color: var(--success); }
        .stat-card.expired .stat-value { color: var(--danger); }
        .stat-card.banned .stat-value { color: var(--warning); }
        .stat-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; margin-bottom: 24px; }
        .card-header { padding: 20px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .card-title { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .card-title i { color: var(--primary); }
        .card-body { padding: 20px 24px; }
        .generate-section { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
        .tier-select {
            background: var(--bg-elevated); border: 1px solid var(--border-light); color: var(--text);
            padding: 12px 16px; border-radius: 10px; font-size: 14px; min-width: 150px; outline: none; cursor: pointer;
        }
        .tier-select option { background: var(--bg-elevated); }
        .count-input {
            background: var(--bg-elevated); border: 1px solid var(--border-light); color: var(--text);
            padding: 12px 16px; border-radius: 10px; font-size: 14px; width: 80px; outline: none;
        }
        .btn {
            padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: 600;
            cursor: pointer; border: none; display: inline-flex; align-items: center; gap: 8px;
        }
        .btn-primary { background: var(--gradient); color: white; }
        .btn-primary:hover { transform: translateY(-2px); }
        .btn-danger { background: var(--danger); color: white; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .btn-secondary { background: var(--bg-elevated); color: var(--text); }
        .generated-keys { background: var(--bg-elevated); border-radius: 12px; padding: 16px; margin-top: 16px; display: none; }
        .generated-keys.show { display: block; }
        .generated-keys h4 { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
        .key-list { display: flex; flex-direction: column; gap: 8px; }
        .key-item {
            background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 8px;
            padding: 12px 16px; font-family: 'Courier New', monospace; font-size: 14px;
            color: var(--primary); display: flex; justify-content: space-between; align-items: center;
        }
        .key-item button { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 16px; }
        .key-item button:hover { color: var(--primary); }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th {
            text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 600;
            color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid var(--border);
        }
        td { padding: 14px 16px; font-size: 13px; border-bottom: 1px solid var(--border); }
        tr:hover td { background: var(--bg-hover); }
        .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: 700; }
        .badge-success { background: rgba(0,255,136,0.1); color: var(--success); }
        .badge-danger { background: rgba(255,68,68,0.1); color: var(--danger); }
        .badge-warning { background: rgba(255,179,71,0.1); color: var(--warning); }
        .key-text { font-family: 'Courier New', monospace; font-size: 12px; color: var(--primary); }
        .device-text { font-family: 'Courier New', monospace; font-size: 11px; color: var(--text-secondary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
        .action-btns { display: flex; gap: 6px; }
        .action-btn {
            width: 28px; height: 28px; border-radius: 6px; border: none; cursor: pointer;
            display: flex; align-items: center; justify-content: center; font-size: 12px;
        }
        .action-btn.copy { background: rgba(51,153,255,0.1); color: #3399FF; }
        .action-btn.ban { background: rgba(255,179,71,0.1); color: var(--warning); }
        .action-btn.delete { background: rgba(255,68,68,0.1); color: var(--danger); }
        .action-btn.extend { background: rgba(0,255,136,0.1); color: var(--success); }
        .action-btn:hover { transform: scale(1.1); }
        .log-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
        .log-time { font-size: 11px; color: var(--text-muted); min-width: 80px; font-family: 'Courier New', monospace; }
        .log-action { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; min-width: 100px; text-align: center; }
        .log-action.success { background: rgba(0,255,136,0.1); color: var(--success); }
        .log-action.fail { background: rgba(255,68,68,0.1); color: var(--danger); }
        .log-action.warn { background: rgba(255,179,71,0.1); color: var(--warning); }
        .log-action.info { background: rgba(51,153,255,0.1); color: #3399FF; }
        .log-details { font-size: 12px; color: var(--text-secondary); flex: 1; }
        .toast-container { position: fixed; top: 24px; right: 24px; z-index: 1000; display: flex; flex-direction: column; gap: 10px; }
        .toast {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            padding: 16px 20px; display: flex; align-items: center; gap: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4); animation: slideIn 0.3s ease; min-width: 300px;
        }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .toast.success { border-left: 4px solid var(--success); }
        .toast.error { border-left: 4px solid var(--danger); }
        .toast-icon { font-size: 20px; }
        .toast.success .toast-icon { color: var(--success); }
        .toast.error .toast-icon { color: var(--danger); }
        .toast-message { font-size: 14px; font-weight: 500; }
        .modal-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: none; align-items: center; justify-content: center;
            z-index: 1000; backdrop-filter: blur(5px);
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px;
            padding: 32px; max-width: 400px; width: 90%; text-align: center;
        }
        .modal h3 { font-size: 20px; margin-bottom: 12px; }
        .modal p { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }
        .modal-actions { display: flex; gap: 12px; justify-content: center; }
        .menu-toggle {
            display: none; position: fixed; top: 20px; left: 20px; z-index: 200;
            background: var(--bg-card); border: 1px solid var(--border); color: var(--text);
            width: 44px; height: 44px; border-radius: 10px; cursor: pointer; font-size: 18px;
        }
        #keySearch {
            background: var(--bg-elevated); border: 1px solid var(--border-light); color: var(--text);
            padding: 8px 14px; border-radius: 8px; font-size: 13px; outline: none; width: 200px;
        }
        .empty-state { text-align: center; padding: 40px; color: var(--text-muted); }
        .empty-state i { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 4px; }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .sidebar.open { transform: translateX(0); }
            .main-content { margin-left: 0; padding: 20px; }
            .menu-toggle { display: flex; align-items: center; justify-content: center; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .generate-section { flex-direction: column; }
        }
    </style>
</head>
<body>
    <button class="menu-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
    <div class="dashboard">
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-logo"><i class="fas fa-fire"></i><span>FF MOD PRO</span></div>
                <div class="sidebar-subtitle">DEV CONTROL PANEL</div>
            </div>
            <ul class="nav-menu">
                <li class="nav-item"><button class="nav-link active" onclick="showTab('overview')"><i class="fas fa-chart-pie"></i><span>Overview</span></button></li>
                <li class="nav-item"><button class="nav-link" onclick="showTab('keys')"><i class="fas fa-key"></i><span>Keys</span></button></li>
                <li class="nav-item"><button class="nav-link" onclick="showTab('logs')"><i class="fas fa-history"></i><span>Logs</span></button></li>
            </ul>
            <div class="sidebar-footer">
                <a href="/admin/logout" class="logout-btn"><i class="fas fa-sign-out-alt"></i><span>Logout</span></a>
            </div>
        </aside>
        <main class="main-content">
            <div class="top-bar">
                <h1 class="page-title" id="pageTitle">Dashboard Overview</h1>
                <button class="refresh-btn" onclick="refreshData()" id="refreshBtn"><i class="fas fa-sync-alt"></i><span>Refresh</span></button>
            </div>
            <div class="stats-grid">
                <div class="stat-card total"><div class="stat-icon"><i class="fas fa-key"></i></div><div class="stat-value">{{ total_keys }}</div><div class="stat-label">Total Keys</div></div>
                <div class="stat-card active"><div class="stat-icon"><i class="fas fa-check-circle"></i></div><div class="stat-value">{{ active_keys }}</div><div class="stat-label">Active Keys</div></div>
                <div class="stat-card expired"><div class="stat-icon"><i class="fas fa-times-circle"></i></div><div class="stat-value">{{ expired_keys }}</div><div class="stat-label">Expired Keys</div></div>
                <div class="stat-card banned"><div class="stat-icon"><i class="fas fa-ban"></i></div><div class="stat-value">{{ banned_count }}</div><div class="stat-label">Banned</div></div>
            </div>
            <div id="tab-overview" class="tab-content" style="display:block">
                <div class="card">
                    <div class="card-header"><div class="card-title"><i class="fas fa-plus-circle"></i>Generate Keys</div></div>
                    <div class="card-body">
                        <div class="generate-section">
                            <select class="tier-select" id="tierSelect">
                                {% for tier_id, tier_info in tiers.items() %}
                                <option value="{{ tier_id }}">{{ tier_info.name }}</option>
                                {% endfor %}
                            </select>
                            <input type="number" class="count-input" id="keyCount" value="1" min="1" max="50" placeholder="Count">
                            <button class="btn btn-primary" onclick="generateKeys()"><i class="fas fa-magic"></i> Generate</button>
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="cleanupExpired()"><i class="fas fa-trash"></i> Cleanup Expired</button>
                        <div class="generated-keys" id="generatedKeys"><h4>Generated Keys</h4><div class="key-list" id="keyList"></div></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><div class="card-title"><i class="fas fa-clock"></i>Recent Activity</div></div>
                    <div class="card-body">
                        {% if logs %}
                        {% for log in logs %}
                        <div class="log-item">
                            <div class="log-time">{{ log.timestamp | timestamp_to_time }}</div>
                            <div class="log-action {{ log.action | action_class }}">{{ log.action }}</div>
                            <div class="log-details">{{ log.details }} <span style="color: var(--text-muted);">({{ log.ip }})</span></div>
                        </div>
                        {% endfor %}
                        {% else %}
                        <div class="empty-state"><i class="fas fa-inbox"></i><p>No recent activity</p></div>
                        {% endif %}
                    </div>
                </div>
            </div>
            <div id="tab-keys" class="tab-content" style="display:none">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-key"></i>All Keys</div>
                        <input type="text" placeholder="Search keys..." id="keySearch" onkeyup="searchKeys()">
                    </div>
                    <div class="card-body">
                        <div class="table-container">
                            <table id="keysTable">
                                <thead><tr><th>Key</th><th>Tier</th><th>Device</th><th>Created</th><th>Expires</th><th>Uses</th><th>Status</th><th>Actions</th></tr></thead>
                                <tbody id="keysTableBody">
                                    {% for key, data in keys.items() %}
                                    <tr data-key="{{ key }}">
                                        <td><span class="key-text">{{ key }}</span></td>
                                        <td><span class="badge badge-warning">{{ data.tier }}</span></td>
                                        <td>{% if data.device_id %}<span class="device-text" title="{{ data.device_id }}">{{ data.device_id[:12] }}...</span>{% else %}<span style="color: var(--text-muted);">Unbound</span>{% endif %}</td>
                                        <td style="color: var(--text-secondary); font-size: 12px;">{{ data.created | timestamp_to_date }}</td>
                                        <td style="color: var(--text-secondary); font-size: 12px;">{% if data.expires == 9999999999 %}<span style="color: var(--success);">Lifetime</span>{% else %}{{ data.expires | timestamp_to_date }}{% endif %}</td>
                                        <td style="text-align: center;">{{ data.uses }}</td>
                                        <td>
                                            {% if data.banned %}<span class="badge badge-danger"><i class="fas fa-ban"></i> Banned</span>
                                            {% elif data.expires != 9999999999 and data.expires < now %}<span class="badge badge-danger"><i class="fas fa-clock"></i> Expired</span>
                                            {% elif data.device_id %}<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>
                                            {% else %}<span class="badge badge-warning"><i class="fas fa-unlock"></i> Unused</span>{% endif %}
                                        </td>
                                        <td>
                                            <div class="action-btns">
                                                <button class="action-btn copy" onclick="copyKey('{{ key }}')" title="Copy"><i class="fas fa-copy"></i></button>
                                                <button class="action-btn extend" onclick="extendKey('{{ key }}')" title="Extend +24h"><i class="fas fa-plus"></i></button>
                                                {% if data.banned %}
                                                <button class="action-btn ban" onclick="unbanKey('{{ key }}')" title="Unban"><i class="fas fa-check"></i></button>
                                                {% else %}
                                                <button class="action-btn ban" onclick="banKey('{{ key }}')" title="Ban"><i class="fas fa-ban"></i></button>
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
            <div id="tab-logs" class="tab-content" style="display:none">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title"><i class="fas fa-history"></i>System Logs</div>
                        <button class="btn btn-sm btn-danger" onclick="clearLogs()"><i class="fas fa-trash"></i> Clear</button>
                    </div>
                    <div class="card-body" id="logsContainer">
                        <div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <div class="toast-container" id="toastContainer"></div>
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal">
            <h3 id="modalTitle">Confirm Action</h3>
            <p id="modalMessage">Are you sure?</p>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-danger" id="modalConfirm">Confirm</button>
            </div>
        </div>
    </div>
    <script>
        let currentTab = 'overview';
        let modalCallback = null;

        function showTab(tabName) {
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            event.target.closest('.nav-link')?.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.getElementById('tab-' + tabName).style.display = 'block';
            document.getElementById('pageTitle').textContent = tabName === 'overview' ? 'Dashboard Overview' : tabName === 'keys' ? 'Key Management' : 'System Logs';
            currentTab = tabName;
            if (tabName === 'logs') loadLogs();
            document.getElementById('sidebar').classList.remove('open');
        }

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

        function showToast(message, type = 'success') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            toast.innerHTML = '<span class="toast-icon">' + (type === 'success' ? '✓' : type === 'error' ? '✕' : '⚠') + '</span><span class="toast-message">' + message + '</span>';
            container.appendChild(toast);
            setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
        }

        function showModal(title, message, cb) {
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('modalMessage').textContent = message;
            modalCallback = cb;
            document.getElementById('modalOverlay').classList.add('show');
        }

        function closeModal() { document.getElementById('modalOverlay').classList.remove('show'); modalCallback = null; }

        document.getElementById('modalConfirm').onclick = function() { if (modalCallback) modalCallback(); closeModal(); };

        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const response = await fetch(endpoint, { method, headers: { 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : null });
                return await response.json();
            } catch (error) { showToast('Network error', 'error'); return null; }
        }

        async function generateKeys() {
            const tier = document.getElementById('tierSelect').value;
            const count = parseInt(document.getElementById('keyCount').value) || 1;
            const result = await apiCall('/api/generate-key', 'POST', { tier, count });
            if (result && result.keys) {
                document.getElementById('keyList').innerHTML = result.keys.map(k => '<div class="key-item"><span>' + k + '</span><button onclick="copyToClipboard(\'' + k + '\')"><i class="fas fa-copy"></i></button></div>').join('');
                document.getElementById('generatedKeys').classList.add('show');
                showToast('Generated ' + result.count + ' keys!');
                refreshData();
            }
        }

        async function copyKey(key) { await copyToClipboard(key); showToast('Key copied!'); }
        async function extendKey(key) { if ((await apiCall('/api/extend-key', 'POST', { key, hours: 24 }))?.success) { showToast('Extended!'); refreshData(); } }
        async function banKey(key) { showModal('Ban Key', 'Ban ' + key + '?', async () => { if ((await apiCall('/api/ban-key', 'POST', { key }))?.success) { showToast('Banned!'); refreshData(); } }); }
        async function unbanKey(key) { if ((await apiCall('/api/unban-key', 'POST', { key }))?.success) { showToast('Unbanned!'); refreshData(); } }
        async function deleteKey(key) { showModal('Delete', 'Delete ' + key + '?', async () => { if ((await apiCall('/api/delete-key', 'POST', { key }))?.success) { showToast('Deleted!'); refreshData(); } }); }
        async function cleanupExpired() { showModal('Cleanup', 'Delete all expired?', async () => { const r = await apiCall('/api/cleanup', 'POST'); if (r) { showToast('Deleted ' + r.deleted + ' keys!'); refreshData(); } }); }
        function refreshData() { window.location.reload(); }

        async function loadLogs() {
            const container = document.getElementById('logsContainer');
            container.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>';
            const result = await apiCall('/api/logs');
            if (result?.logs) {
                container.innerHTML = result.logs.length === 0 ? '<div class="empty-state"><i class="fas fa-inbox"></i><p>No logs</p></div>' :
                    result.logs.map(l => '<div class="log-item"><div class="log-time">' + new Date(l.timestamp * 1000).toLocaleTimeString() + '</div><div class="log-action ' + (l.action.includes('SUCCESS')||l.action.includes('GENERATE')?'success':l.action.includes('FAIL')||l.action.includes('DELETE')?'fail':l.action.includes('BAN')?'warn':'info') + '">' + l.action + '</div><div class="log-details">' + l.details + ' <span style="color:var(--text-muted)">(' + l.ip + ')</span></div></div>').join('');
            }
        }

        function searchKeys() {
            const q = document.getElementById('keySearch').value.toLowerCase();
            document.querySelectorAll('#keysTableBody tr').forEach(row => {
                row.style.display = (row.getAttribute('data-key').toLowerCase().includes(q) || (row.querySelector('.device-text')?.textContent.toLowerCase() || '').includes(q)) ? '' : 'none';
            });
        }

        function clearLogs() { showModal('Clear Logs', 'Delete all logs?', () => { showToast('Cleared!', 'success'); loadLogs(); }); }

        async function copyToClipboard(text) {
            try { await navigator.clipboard.writeText(text); } catch {
                const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
            }
        }

        setInterval(() => { if (currentTab === 'logs') loadLogs(); }, 30000);
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.querySelector('.menu-toggle');
            if (window.innerWidth <= 768 && sidebar.classList.contains('open') && !sidebar.contains(e.target) && !toggle.contains(e.target)) sidebar.classList.remove('open');
        });
    </script>
</body>
</html>'''

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/get-key')
def get_key_page():
    device = request.args.get('device', 'unknown')
    return render_template_string(GET_KEY_HTML, device=device)

@app.route('/verify', methods=['POST'])
def verify():
    keys = load_keys()
    key = request.form.get('key', '').strip().upper()
    device_id = request.form.get('device_id', '').strip()
    device_name = request.form.get('device_name', 'Unknown').strip()

    if not key or key not in keys:
        add_log('VERIFY_FAIL', f"Invalid key: {key}")
        return jsonify({"valid": False, "message": "Invalid key!"})

    key_data = keys[key]

    if key_data.get('banned'):
        return jsonify({"valid": False, "message": "Key banned!"})

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

    add_log('VERIFY_SUCCESS', f"Key {key} verified by {device_id}")

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
    key = request.form.get('key', '').strip().upper()
    device_id = request.form.get('device_id', '').strip()

    if not key or key not in keys:
        return jsonify({"valid": False})

    key_data = keys[key]
    if key_data.get('banned') or not is_key_valid(key_data):
        return jsonify({"valid": False})
    if key_data.get('device_id') and key_data['device_id'] != device_id:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

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
        add_log('ADMIN_LOGIN', f"Admin logged in")
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
    now = int(time.time())

    total = len(keys)
    active = sum(1 for k in keys.values() if is_key_valid(k))
    expired = sum(1 for k in keys.values() if k['expires'] != 9999999999 and k['expires'] < now)
    banned = sum(1 for k in keys.values() if k.get('banned'))
    recent_logs = logs[-20:][::-1] if logs else []

    return render_template_string(ADMIN_DASHBOARD_HTML,
                         total_keys=total, active_keys=active,
                         expired_keys=expired, banned_count=banned,
                         keys=keys, logs=recent_logs, tiers=TIERS)

@app.route('/api/generate-key', methods=['POST'])
@login_required
def api_generate_key():
    data = request.get_json()
    tier = data.get('tier', '24h')
    count = min(data.get('count', 1), 50)

    if tier not in TIERS:
        return jsonify({"error": "Invalid tier"}), 400

    keys = load_keys()
    generated = []

    for _ in range(count):
        prefix = 'FF-PRO'
        key = f"{prefix}-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"
        now = int(time.time())
        hours = TIERS[tier]['hours']
        expires = now + (hours * 3600) if hours > 0 else 9999999999

        keys[key] = {
            "key": key, "tier": tier, "created": now, "expires": expires,
            "device_id": None, "device_name": None, "uses": 0,
            "last_use": None, "banned": False
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

@app.route('/api/stats')
@login_required
def api_stats():
    keys = load_keys()
    now = int(time.time())
    return jsonify({
        'total': len(keys),
        'active': sum(1 for k in keys.values() if is_key_valid(k)),
        'expired': sum(1 for k in keys.values() if k['expires'] != 9999999999 and k['expires'] < now),
        'banned': sum(1 for k in keys.values() if k.get('banned'))
    })

# ==================== TEMPLATE FILTERS ====================
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    if timestamp == 9999999999:
        return "Lifetime"
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')

@app.template_filter('timestamp_to_time')
def timestamp_to_time(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')

@app.template_filter('action_class')
def action_class(action):
    if 'SUCCESS' in action or 'GENERATE' in action:
        return 'success'
    elif 'FAIL' in action or 'DELETE' in action:
        return 'fail'
    elif 'BAN' in action:
        return 'warn'
    return 'info'

@app.context_processor
def inject_now():
    return {'now': int(time.time())}

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

# ==================== FOR VERCEL ====================
if __name__ == '__main__':
    app.run(debug=True)
