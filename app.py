import os
from flask import Flask, render_template, url_for, request, flash, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

class Base(DeclarativeBase):
    pass

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "auto-trade-vip-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set. Please ensure PostgreSQL database is configured.")
    
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db = SQLAlchemy(app, model_class=Base)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'  # Redirect to main page instead of separate login page

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Landing page for AUTO TRADE VIP"""
    
    # Broker data for carousel - Using static path directly for better reliability
    brokers = [
        {
            'name': 'Binomo',
            'logo': '/static/images/brokers/binomo.png'
        },
        {
            'name': 'Olymptrade', 
            'logo': '/static/images/brokers/olymptrade.png'
        },
        {
            'name': 'Stockity',
            'logo': '/static/images/brokers/stockity.png'
        },
        {
            'name': 'IQ Option',
            'logo': '/static/images/brokers/iqoption.png'
        },
        {
            'name': 'Quotex',
            'logo': '/static/images/brokers/quotex.png'
        },
        {
            'name': 'Pocket Option',
            'logo': '/static/images/brokers/pocket-option.png'
        }
    ]
    
    # Package data
    packages = [
        {
            'id': 'free-demo',
            'name': 'TRADING ROBOT – FREE DEMO',
            'price': 'FREE',
            'period': 'selamanya',
            'brokers': ['Semua Broker', 'Demo Account Only'],
            'broker_logos': [
                '/static/images/brokers/binomo.png',
                '/static/images/brokers/olymptrade.png',
                '/static/images/brokers/iqoption.png',
                '/static/images/brokers/quotex.png'
            ],
            'features': [
                'Auto trade via MetaTrader 4 (MT4) - Demo Account',
                'Manual trade via MT4 - Demo Account', 
                'Akses Grup Telegram Public',
                'Back-tester untuk strategi',
                'MetaTrader 4 Platform',
                '3 indikator eksklusif: \'Binary Profit\', \'Golden Moment\', dan \'Price Action\'',
                'Konektor indikator dan input sinyal',
                'Fitur lengkap (Full Features+) - Demo Only',
                'Tutorial pengguna lengkap',
                'Update gratis selamanya'
            ]
        },
        {
            'id': 'multi-platform',
            'name': 'TRADING ROBOT – MULTI PLATFORM',
            'price': '$39.00',
            'period': 'bulan',
            'brokers': ['IQ Option', 'Olymptrade', 'Quotex', 'Pocket Option'],
            'broker_logos': [
                '/static/images/brokers/iqoption.png',
                '/static/images/brokers/olymptrade.png',
                '/static/images/brokers/quotex.png',
                '/static/images/brokers/pocket-option.png'
            ],
            'features': [
                'Auto trade via MetaTrader 4 (MT4) ke IQ Option',
                'Manual trade via MT4 ke IQ Option',
                'Akses Grup VIP Telegram',
                'Back-tester untuk strategi',
                'MetaTrader 4 Platform',
                '3 indikator eksklusif: \'Binary Profit\', \'Golden Moment\', dan \'Price Action\'',
                'Konektor indikator dan input sinyal',
                'Fitur lengkap (Full Features+)',
                'Tutorial pengguna lengkap',
                'Update gratis selamanya'
            ]
        },
        {
            'id': 'binomo-stockity',
            'name': 'TRADING ROBOT – BINOMO & STOCKITY',
            'price': '$46.00',
            'period': 'bulan',
            'brokers': ['Binomo', 'Stockity'],
            'broker_logos': [
                '/static/images/brokers/binomo.png',
                '/static/images/brokers/stockity.png'
            ],
            'features': [
                'Auto trade via MetaTrader 4 (MT4) ke Binomo & Stockity',
                'Manual trade via MT4 ke Binomo & Stockity',
                'Akses Grup VIP Telegram',
                'Back-tester untuk strategi',
                'MetaTrader 4 Platform',
                '3 indikator eksklusif: \'Binary Profit\', \'Golden Moment\', dan \'Price Action\'',
                'Konektor indikator dan input sinyal',
                'Fitur lengkap (Full Features+)',
                'Tutorial pengguna lengkap',
                'Update gratis selamanya'
            ]
        }
    ]
    
    return render_template('index.html', brokers=brokers, packages=packages, current_user=current_user)

@app.route('/login', methods=['POST'])
def login():
    """Handle login via AJAX from modal"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username dan password harus diisi'})
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'success': True, 'message': 'Login berhasil!'})
    else:
        return jsonify({'success': False, 'message': 'Username atau password salah'})

@app.route('/register', methods=['POST'])
def register():
    """Handle registration via AJAX from modal"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Semua field harus diisi'})
    
    # Check if user exists
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username sudah digunakan'})
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email sudah digunakan'})
    
    # Create new user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'success': True, 'message': 'Registrasi berhasil!'})

@app.route('/logout')
@login_required
def logout():
    """Handle logout"""
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
