import os
from flask import Flask, render_template, url_for, request, flash, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import os
sys.path.append('.')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from iq_trading_robot import IQTradingRobot
import threading
import json

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
login_manager.login_view = 'index'  # type: ignore # Redirect to main page instead of separate login page

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationship with bot settings
    bot_settings = db.relationship('BotSetting', backref='user', lazy=True)

# Bot Settings Model
class BotSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    broker_domain = db.Column(db.String(100), nullable=False, default='iqoption.com')
    iq_email = db.Column(db.String(120), nullable=False)
    iq_password = db.Column(db.String(256), nullable=False)  # Encrypted
    account_type = db.Column(db.String(10), nullable=False, default='demo')  # demo or real
    
    # Trading Configuration
    trading_amount = db.Column(db.Float, default=1.0)
    stop_win = db.Column(db.Float, default=10.0)  # Stop trading when profit reaches this
    stop_loss = db.Column(db.Float, default=10.0)  # Stop trading when loss reaches this
    step_martingale = db.Column(db.Integer, default=3)  # Number of martingale steps
    martingale_multiple = db.Column(db.Float, default=2.2)  # Martingale multiplier
    
    asset = db.Column(db.String(50), default='EURUSD-OTC')
    strategy = db.Column(db.String(50), default='martingale')
    signal_type = db.Column(db.String(100), default='mt4_next_signal')  # Signal source type
    max_consecutive_losses = db.Column(db.Integer, default=3)
    
    # Trading Session Configuration
    start_time = db.Column(db.String(10), default='09:00')  # Trading start time
    end_time = db.Column(db.String(10), default='17:00')  # Trading end time
    timezone = db.Column(db.String(50), default='UTC')  # Trading timezone
    active_days = db.Column(db.String(20), default='weekdays')  # Trading active days
    
    is_active = db.Column(db.Boolean, default=False)
    balance_info = db.Column(db.Text)  # JSON string to store balance data
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'})
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'success': True, 'message': 'Login successful!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'})

@app.route('/register', methods=['POST'])
def register():
    """Handle registration via AJAX from modal"""
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    gender = data.get('gender')
    country = data.get('country')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    agree_terms = data.get('agree_terms')
    
    if not all([name, email, gender, country, password, confirm_password]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match'})
        
    if not agree_terms:
        return jsonify({'success': False, 'message': 'You must agree to the terms and conditions'})
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'})
    
    # Create new user
    user = User(
        name=name,
        email=email,
        gender=gender,
        country=country,
        password_hash=generate_password_hash(password)
    )
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'success': True, 'message': 'Registration successful!'})

@app.route('/logout')
@login_required
def logout():
    """Handle logout and clear user sessions"""
    user_id = current_user.id
    
    # Stop and clean up any active bot sessions for this user
    if user_id in active_bots:
        try:
            # Stop the bot if it's running
            if active_bots[user_id].is_trading:
                active_bots[user_id].stop_trading()
            # Disconnect and clean up
            active_bots[user_id].disconnect()
            del active_bots[user_id]
        except:
            # Handle any cleanup errors silently
            pass
    
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page for logged in users"""
    # Get user statistics or any dashboard data here
    user_stats = {
        'total_trades': 0,
        'active_packages': 0,
        'profit_percentage': 0,
        'account_balance': 0
    }
    
    # Get bot settings info
    bot_settings = BotSetting.query.filter_by(user_id=current_user.id).first()
    bot_configured = bot_settings is not None
    bot_active = current_user.id in active_bots and active_bots[current_user.id].is_trading if current_user.id in active_bots else False
    
    return render_template('dashboard.html', 
                         user_stats=user_stats, 
                         current_user=current_user,
                         bot_configured=bot_configured,
                         bot_active=bot_active)

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        # Check if email exists in database
        user = User.query.filter_by(email=email).first()
        
        if user:
            # In a production app, you would send an actual email here
            # For demo purposes, we'll just return success
            return jsonify({
                'success': True, 
                'message': f'Password reset instructions have been sent to {email}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Email address not found in our system'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

# Global variable to store active bots
active_bots = {}

@app.route('/bot-settings')
@login_required
def bot_settings():
    """Bot trading settings page"""
    # Get user's bot settings
    settings = BotSetting.query.filter_by(user_id=current_user.id).first()
    
    # Available broker domains by region
    broker_domains = {
        'Global': 'iqoption.com',
        'Europe': 'eu.iqoption.com', 
        'Asia': 'iqoption.com',
        'Brazil': 'iqoption.com.br',
        'Indonesia': 'iqoption.com',
        'India': 'iqoption.com'
    }
    
    return render_template('bot_settings.html', 
                         settings=settings, 
                         broker_domains=broker_domains,
                         current_user=current_user)

@app.route('/save-bot-settings', methods=['POST'])
@login_required
def save_bot_settings():
    """Save bot settings"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['broker_domain', 'iq_email', 'iq_password', 'account_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'})
        
        # Get or create bot settings
        settings = BotSetting.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = BotSetting(user_id=current_user.id)
        
        # Update settings
        settings.broker_domain = data['broker_domain']
        settings.iq_email = data['iq_email']
        settings.iq_password = generate_password_hash(data['iq_password'])  # Encrypt password
        settings.account_type = data['account_type']
        
        # Trading Configuration
        settings.trading_amount = float(data.get('trading_amount', 1.0))
        settings.stop_win = float(data.get('stop_win', 10.0))
        settings.stop_loss = float(data.get('stop_loss', 10.0))
        settings.step_martingale = int(data.get('step_martingale', 3))
        settings.martingale_multiple = float(data.get('martingale_multiple', 2.2))
        
        settings.signal_type = data.get('signal_type', 'mt4_next_signal')
        
        # Trading Session Configuration
        settings.start_time = data.get('start_time', '09:00')
        settings.end_time = data.get('end_time', '17:00')
        settings.timezone = data.get('timezone', 'UTC')
        settings.active_days = data.get('active_days', 'weekdays')
        
        db.session.add(settings)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Bot settings saved successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving settings: {str(e)}'})

@app.route('/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test IQ Option connection and get balance"""
    try:
        data = request.get_json()
        broker_domain = data['broker_domain']
        iq_email = data['iq_email']
        iq_password = data['iq_password']
        account_type = data['account_type']
        
        # Clear any existing session for this user before testing
        user_id = current_user.id
        if user_id in active_bots:
            try:
                active_bots[user_id].disconnect()
                del active_bots[user_id]
            except:
                pass
        
        # Create temporary robot instance for testing
        test_robot = IQTradingRobot(iq_email, iq_password)
        test_robot.api = None  # Reset to ensure fresh connection
        
        # Configure robot with current form data for testing
        test_robot.trading_amount = float(data.get('trading_amount', 1.0))
        test_robot.stop_win = float(data.get('stop_win', 10.0))
        test_robot.stop_loss = float(data.get('stop_loss', 10.0))
        test_robot.step_martingale = int(data.get('step_martingale', 3))
        test_robot.martingale_multiple = float(data.get('martingale_multiple', 2.2))
        test_robot.signal_type = data.get('signal_type', 'mt4_next_signal')
        
        # Try to connect
        success = test_robot.connect()
        
        if success:
            # Switch to demo/real account based on setting
            if account_type == 'demo':
                test_robot.change_balance('PRACTICE')
            else:
                test_robot.change_balance('REAL')
            
            # Get balance after switching
            balance = test_robot.get_balance()
            
            # Save balance info to database
            settings = BotSetting.query.filter_by(user_id=current_user.id).first()
            if settings:
                balance_info = {
                    'balance': balance,
                    'account_type': account_type,
                    'last_checked': str(db.func.current_timestamp()),
                    'status': 'connected'
                }
                settings.balance_info = json.dumps(balance_info)
                db.session.commit()
            
            # Disconnect test connection
            test_robot.disconnect()
            
            return jsonify({
                'success': True,
                'message': 'Connection successful!',
                'balance': balance,
                'account_type': account_type
            })
        else:
            # Clear any cached balance info on failed connection
            settings = BotSetting.query.filter_by(user_id=current_user.id).first()
            if settings:
                balance_info = {
                    'balance': 0,
                    'account_type': 'none',
                    'last_checked': str(db.func.current_timestamp()),
                    'status': 'disconnected'
                }
                settings.balance_info = json.dumps(balance_info)
                db.session.commit()
            
            return jsonify({
                'success': False,
                'message': 'Failed to connect. Please check your credentials.'
            })
            
    except Exception as e:
        # Clear any cached balance info on exception
        try:
            settings = BotSetting.query.filter_by(user_id=current_user.id).first()
            if settings:
                balance_info = {
                    'balance': 0,
                    'account_type': 'none',
                    'last_checked': str(db.func.current_timestamp()),
                    'status': 'error'
                }
                settings.balance_info = json.dumps(balance_info)
                db.session.commit()
        except:
            pass
            
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        })

@app.route('/start-bot', methods=['POST'])
@login_required
def start_bot():
    """Start trading bot"""
    try:
        user_id = current_user.id
        
        # Check if bot is already running
        if user_id in active_bots and active_bots[user_id].is_trading:
            return jsonify({
                'success': False,
                'message': 'Trading bot is already running!'
            })
        
        # Get user's bot settings
        settings = BotSetting.query.filter_by(user_id=user_id).first()
        if not settings:
            return jsonify({
                'success': False,
                'message': 'Bot settings not found. Please configure bot settings first.'
            })
        
        # Decrypt password (in real app, use proper decryption)
        # For now, we'll need user to re-enter password or store it differently
        return jsonify({
            'success': False,
            'message': 'Please test connection first to start trading bot.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting bot: {str(e)}'
        })

@app.route('/stop-bot', methods=['POST'])
@login_required  
def stop_bot():
    """Stop trading bot"""
    try:
        user_id = current_user.id
        
        if user_id in active_bots:
            active_bots[user_id].stop_trading()
            active_bots[user_id].disconnect()
            del active_bots[user_id]
            
            return jsonify({
                'success': True,
                'message': 'Trading bot stopped successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No active trading bot found.'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error stopping bot: {str(e)}'
        })

@app.route('/bot-status')
@login_required
def bot_status():
    """Get current bot status"""
    try:
        user_id = current_user.id
        settings = BotSetting.query.filter_by(user_id=user_id).first()
        
        status_data = {
            'is_configured': settings is not None,
            'is_active': user_id in active_bots and active_bots[user_id].is_trading if user_id in active_bots else False,
            'balance_info': json.loads(settings.balance_info) if settings and settings.balance_info else None
        }
        
        if user_id in active_bots:
            robot = active_bots[user_id]
            status_data.update({
                'total_trades': len(robot.trades_history),
                'profit_total': robot.profit_total,
                'consecutive_losses': robot.consecutive_losses
            })
        
        return jsonify(status_data)
        
    except Exception as e:
        return jsonify({
            'error': f'Error getting bot status: {str(e)}'
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
