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
try:
    from iq_trading_robot import IQTradingRobot
except ImportError:
    IQTradingRobot = None
try:
    from strategy_scalper import AtvScalperM1, fetch_candles_range
except ImportError:
    AtvScalperM1 = None
    fetch_candles_range = None

try:
    from strategy_generator import (
        StrategyGenerator, TradingConfig as GenTradingConfig,
        INDICATOR_CATALOG, backtest_strategy
    )
except ImportError:
    StrategyGenerator = None
    GenTradingConfig = None
    INDICATOR_CATALOG = {}
    backtest_strategy = None
import threading
import json
import time

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
    
    signal_type = db.Column(db.String(100), default='manual_input')  # Signal source type - FOKUS HANYA SIGNAL INPUT
    signal_content = db.Column(db.Text)  # Content for manual signal input
    
    # Trading Session Configuration
    start_time = db.Column(db.String(10), default='09:00')  # Trading start time
    end_time = db.Column(db.String(10), default='17:00')  # Trading end time
    timezone = db.Column(db.String(50), default='UTC')  # Trading timezone
    user_timezone = db.Column(db.String(10), default='auto')  # User's timezone offset for signal timing
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
    user = User()
    user.name = name
    user.email = email
    user.gender = gender
    user.country = country
    user.password_hash = generate_password_hash(password)
    
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
# Cache for market open status per user
market_cache = {}

@app.route('/bot-settings')
@login_required
def bot_settings():
    """Redirect to the dashboard IQ Option section"""
    return redirect(url_for('dashboard'))

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
            settings = BotSetting()
            settings.user_id = current_user.id
        
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
        
        settings.signal_type = data.get('signal_type', 'manual_input')  # Default ke manual input
        settings.signal_content = data.get('signal_content', '')  # Save signal content for manual input
        
        # Trading Session Configuration
        settings.start_time = data.get('start_time', '09:00')
        settings.end_time = data.get('end_time', '17:00')
        settings.timezone = data.get('timezone', 'UTC')
        settings.user_timezone = data.get('user_timezone', 'auto')  # User's timezone for signal timing
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
                active_bots[user_id].stop_trading()
                active_bots[user_id].disconnect()
                del active_bots[user_id]
            except:
                pass
        
        # Create temporary robot instance for testing
        test_robot = IQTradingRobot(iq_email, iq_password)
        test_robot.api = None  # Reset to ensure fresh connection
        
        # Configure robot dengan dataclass config
        from iq_trading_robot import TradingBotConfig
        config = TradingBotConfig(
            iq_email=iq_email,
            iq_password=iq_password,
            account_type=account_type,
            trading_amount=float(data.get('trading_amount', 1.0)),
            stop_win=float(data.get('stop_win', 10.0)),
            stop_loss=float(data.get('stop_loss', 10.0)),
            step_martingale=int(data.get('step_martingale', 3)),
            martingale_multiple=float(data.get('martingale_multiple', 2.2)),
            signal_type=data.get('signal_type', 'manual_input'),
            asset=data.get('asset', 'EURUSD')
        )
        test_robot.config = config
        
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
            
            # Save balance info and password to database
            settings = BotSetting.query.filter_by(user_id=current_user.id).first()
            if settings:
                balance_info = {
                    'balance': balance,
                    'account_type': account_type,
                    'last_checked': str(db.func.current_timestamp()),
                    'status': 'connected'
                }
                settings.balance_info = json.dumps(balance_info)
                # Save encrypted password for later use
                from werkzeug.security import generate_password_hash
                settings.iq_password = generate_password_hash(iq_password)
                db.session.commit()
            
            # Don't disconnect - keep connection alive for potential bot start
            # test_robot.disconnect()
            
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
        
        # Get password from request or try stored password
        data = request.get_json() or {}
        iq_password = data.get('iq_password')
        
        # If no password in request, try to get it from settings
        if not iq_password:
            # Check if we have stored balance info with connection status
            if settings.balance_info:
                balance_data = json.loads(settings.balance_info)
                if balance_data.get('status') == 'connected':
                    # For security, we'll ask the user to provide password each time
                    return jsonify({
                        'success': False,
                        'message': 'Please enter your IQ Option password to start the bot.'
                    })
            
            return jsonify({
                'success': False,
                'message': 'Password required to start bot. Please test connection first.'
            })
        
        # Create new robot instance dengan dataclass config
        from iq_trading_robot import TradingBotConfig
        config = TradingBotConfig.from_db_settings(settings)
        config.iq_password = iq_password  # Set password dari request
        
        # Pastikan ada signal content untuk testing jika kosong
        if not config.signal_content or config.signal_content.strip() == '':
            config.signal_content = 'CALL,1'  # Signal default untuk testing
            print(f"⚠️ Menggunakan signal default: {config.signal_content}")
            
        robot = IQTradingRobot(settings.iq_email, iq_password, config)
        
        # Connect to IQ Option
        if not robot.connect():
            return jsonify({
                'success': False,
                'message': 'Failed to connect to IQ Option. Please check your credentials.'
            })
        
        # Switch to correct account type
        if settings.account_type == 'demo':
            robot.change_balance('PRACTICE')
        else:
            robot.change_balance('REAL')
        
        # Update balance after account type switch
        time.sleep(1)
        robot.balance = robot.get_balance()
        
        # Start trading
        if robot.start_trading():
            active_bots[user_id] = robot
            return jsonify({
                'success': True,
                'message': 'Trading bot started successfully!',
                'balance': robot.balance
            })
        else:
            robot.disconnect()
            return jsonify({
                'success': False,
                'message': 'Failed to start trading bot.'
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

@app.route('/iqoption/market-open', methods=['POST'])
@login_required
def iqoption_market_open():
    """Start a background thread to fetch live market open/closed status from IQ Option"""
    try:
        data = request.get_json() or {}
        user_id = current_user.id
        iq_email = data.get('iq_email', '')
        iq_password = data.get('iq_password', '')
        account_type = data.get('account_type', 'PRACTICE')

        if not iq_email or not iq_password:
            return jsonify({'success': False, 'message': 'Silahkan login IQ Option terlebih dahulu.'})

        if IQTradingRobot is None:
            return jsonify({'success': False, 'message': 'IQ Option API tidak tersedia.'})

        market_cache[user_id] = {'status': 'loading', 'data': None, 'message': ''}

        def fetch_market(uid, email, password, acct):
            try:
                robot = None
                if uid in active_bots and active_bots[uid].check_connect():
                    robot = active_bots[uid]
                else:
                    robot = IQTradingRobot(email, password)
                    if not robot.connect():
                        market_cache[uid] = {'status': 'error', 'data': None,
                                             'message': 'Gagal konek ke IQ Option. Periksa email/password.'}
                        return
                    robot.change_balance(acct)
                    time.sleep(3)

                open_time, error_msg = robot.get_all_open_time()

                if error_msg:
                    market_cache[uid] = {'status': 'error', 'data': None, 'message': error_msg}
                    return

                result = {}
                for category, assets in open_time.items():
                    result[category] = {}
                    for asset_name, info in assets.items():
                        if isinstance(info, dict):
                            result[category][asset_name] = info.get('open', False)
                        else:
                            result[category][asset_name] = bool(info)

                if not result:
                    market_cache[uid] = {'status': 'error', 'data': None,
                                         'message': 'Data pasar kosong. IQ Option mungkin tidak merespons. Coba lagi beberapa saat.'}
                    return

                market_cache[uid] = {'status': 'ready', 'data': result, 'message': ''}
            except Exception as ex:
                market_cache[uid] = {'status': 'error', 'data': None, 'message': f'Error: {str(ex)}'}

        t = threading.Thread(target=fetch_market,
                             args=(user_id, iq_email, iq_password, account_type),
                             daemon=True)
        t.start()

        return jsonify({'success': True, 'status': 'loading'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/iqoption/market-status', methods=['GET'])
@login_required
def iqoption_market_status():
    """Poll endpoint: returns current market fetch status/data for the logged-in user"""
    user_id = current_user.id
    cache = market_cache.get(user_id, {'status': 'idle', 'data': None, 'message': ''})
    return jsonify(cache)


# Chart candle cache: user_id -> {status, data, asset, interval, message}
chart_cache = {}

@app.route('/iqoption/candles', methods=['POST'])
@login_required
def iqoption_candles():
    """Start background fetch of OHLC candle data from IQ Option"""
    try:
        data = request.get_json() or {}
        user_id = current_user.id
        asset = data.get('asset', 'EURUSD-OTC')
        interval = int(data.get('interval', 60))
        count = min(int(data.get('count', 100)), 500)
        iq_email = data.get('iq_email', '')
        iq_password = data.get('iq_password', '')
        account_type = data.get('account_type', 'PRACTICE')

        if not iq_email or not iq_password:
            return jsonify({'success': False, 'message': 'Login IQ Option terlebih dahulu.'})

        chart_cache[user_id] = {'status': 'loading', 'data': None, 'asset': asset, 'interval': interval, 'message': ''}

        def fetch_candles(uid, email, password, acct, act, ivl, cnt):
            try:
                robot = None
                if uid in active_bots and active_bots[uid].check_connect():
                    robot = active_bots[uid]
                else:
                    robot = IQTradingRobot(email, password)
                    if not robot.connect():
                        chart_cache[uid] = {'status': 'error', 'data': None, 'asset': act, 'interval': ivl,
                                            'message': 'Gagal konek ke IQ Option. Periksa email/password.'}
                        return
                    robot.change_balance(acct)
                    time.sleep(2)

                candles_raw = robot.api.get_candles(act, ivl, cnt, time.time())
                if not candles_raw:
                    chart_cache[uid] = {'status': 'error', 'data': None, 'asset': act, 'interval': ivl,
                                        'message': f'Tidak ada data candle untuk {act}.'}
                    return

                result = []
                for c in candles_raw:
                    result.append({
                        'time': int(c.get('from', c.get('id', 0))),
                        'open': float(c.get('open', 0)),
                        'high': float(c.get('max', c.get('high', 0))),
                        'low': float(c.get('min', c.get('low', 0))),
                        'close': float(c.get('close', 0)),
                        'volume': int(c.get('volume', 0))
                    })
                result.sort(key=lambda x: x['time'])
                chart_cache[uid] = {'status': 'ready', 'data': result, 'asset': act,
                                    'interval': ivl, 'message': ''}
            except Exception as ex:
                chart_cache[uid] = {'status': 'error', 'data': None, 'asset': asset,
                                    'interval': interval, 'message': f'Error: {str(ex)}'}

        t = threading.Thread(target=fetch_candles,
                             args=(user_id, iq_email, iq_password, account_type, asset, interval, count),
                             daemon=True)
        t.start()
        return jsonify({'success': True, 'status': 'loading'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/iqoption/candles-data', methods=['GET'])
@login_required
def iqoption_candles_data():
    """Poll endpoint: returns candle fetch status/data"""
    user_id = current_user.id
    cache = chart_cache.get(user_id, {'status': 'idle', 'data': None, 'message': ''})
    return jsonify(cache)


@app.route('/iqoption/candles-more', methods=['POST'])
@login_required
def iqoption_candles_more():
    """Fetch older historical candles for chart scroll-back (lazy-load)"""
    try:
        data        = request.get_json() or {}
        user_id     = current_user.id
        asset       = data.get('asset', 'EURUSD')
        interval    = int(data.get('interval', 60))
        before_time = float(data.get('before_time', time.time()))
        count       = min(int(data.get('count', 150)), 500)
        iq_email    = data.get('iq_email', '')
        iq_password = data.get('iq_password', '')

        # Reuse an already-connected robot when possible (avoids slow reconnect)
        robot = None
        rt = rt_stream_cache.get(user_id)
        if rt and rt.get('status') == 'active' and rt.get('robot'):
            robot = rt['robot']
        elif user_id in active_bots and active_bots[user_id].check_connect():
            robot = active_bots[user_id]

        if robot is None:
            if not iq_email or not iq_password:
                return jsonify({'success': False, 'message': 'Login terlebih dahulu.'})
            robot = IQTradingRobot(iq_email, iq_password)
            if not robot.connect():
                return jsonify({'success': False, 'message': 'Gagal konek ke IQ Option.'})
            time.sleep(1)

        # Fetch candles ending BEFORE before_time so they don't overlap
        candles_raw = robot.api.get_candles(asset, interval, count, before_time - 1)
        if not candles_raw:
            return jsonify({'success': True, 'candles': []})

        result = []
        for c in candles_raw:
            t_val = int(c.get('from', c.get('id', 0)))
            if t_val >= before_time:      # strict: exclude any that overlap
                continue
            result.append({
                'time':   t_val,
                'open':   float(c.get('open', 0)),
                'high':   float(c.get('max', c.get('high', 0))),
                'low':    float(c.get('min', c.get('low', 0))),
                'close':  float(c.get('close', 0)),
                'volume': int(c.get('volume', 0))
            })
        result.sort(key=lambda x: x['time'])
        return jsonify({'success': True, 'candles': result})
    except Exception as e:
        logging.exception(f'candles-more error: {e}')
        return jsonify({'success': False, 'message': str(e)})


# ─── Real-time candle stream cache ───────────────────────────────────────────
# user_id -> {status, robot, asset, interval, message}
rt_stream_cache = {}


def _rt_candle_to_dict(ts, c):
    """Convert a real_time_candles entry to chart-ready dict."""
    return {
        'time':   int(c.get('from', ts)),
        'open':   float(c.get('open',  0)),
        'high':   float(c.get('max',   c.get('high',  0))),
        'low':    float(c.get('min',   c.get('low',   0))),
        'close':  float(c.get('close', 0)),
        'volume': int(c.get('volume',  0))
    }


@app.route('/iqoption/rt-start', methods=['POST'])
@login_required
def iqoption_rt_start():
    """Start (or reuse) a real-time WebSocket candle stream for the given asset/interval."""
    try:
        data         = request.get_json() or {}
        iq_email     = data.get('iq_email', '').strip()
        iq_password  = data.get('iq_password', '')
        account_type = data.get('account_type', 'PRACTICE')
        asset        = data.get('asset', 'EURUSD')
        interval     = int(data.get('interval', 60))
        user_id      = current_user.id

        if not iq_email or not iq_password:
            return jsonify({'success': False, 'message': 'Login IQ Option terlebih dahulu.'})

        existing = rt_stream_cache.get(user_id, {})

        # Reuse if same asset+interval is already active
        if (existing.get('status') == 'active'
                and existing.get('asset') == asset
                and existing.get('interval') == interval):
            return jsonify({'success': True, 'status': 'active'})

        # Stop old stream if different
        if existing.get('status') == 'active' and existing.get('robot'):
            try:
                existing['robot'].api.stop_candles_stream(
                    existing['asset'], existing['interval'])
            except Exception:
                pass

        rt_stream_cache[user_id] = {
            'status': 'starting', 'asset': asset, 'interval': interval,
            'robot': None, 'message': ''
        }

        def _start(uid, email, password, acct, act, ivl):
            try:
                robot = IQTradingRobot(email, password)
                ok = robot.connect()           # returns bool, NOT a tuple
                if not ok:
                    rt_stream_cache[uid] = {
                        'status': 'error', 'asset': act, 'interval': ivl,
                        'robot': None, 'message': 'Gagal konek ke IQ Option. Periksa email/password.'
                    }
                    return
                time.sleep(1)
                rt_stream_cache[uid]['robot'] = robot
                # Blocking – subscribes to WebSocket candle-generated channel
                # Also pre-fills real_time_candles buffer with 300 historical candles
                robot.api.start_candles_stream(act, ivl, 300)
                rt_stream_cache[uid]['status'] = 'active'
                logging.info(f'RT stream ACTIVE: user={uid} asset={act} ivl={ivl}')
            except Exception as ex:
                logging.exception(f'RT stream error: {ex}')
                rt_stream_cache[uid] = {
                    'status': 'error', 'asset': act, 'interval': ivl,
                    'robot': None, 'message': str(ex)
                }

        threading.Thread(
            target=_start,
            args=(user_id, iq_email, iq_password, account_type, asset, interval),
            daemon=True
        ).start()

        return jsonify({'success': True, 'status': 'starting'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/iqoption/rt-candles', methods=['GET'])
@login_required
def iqoption_rt_candles():
    """Return the latest real-time candles from the live WebSocket stream."""
    user_id = current_user.id
    cache   = rt_stream_cache.get(user_id)

    if not cache:
        return jsonify({'status': 'idle'})

    status = cache.get('status', 'idle')

    if status == 'starting':
        return jsonify({'status': 'starting'})

    if status == 'error':
        return jsonify({'status': 'error', 'message': cache.get('message', '')})

    if status == 'active':
        robot = cache.get('robot')
        if not robot:
            return jsonify({'status': 'starting'})
        try:
            asset    = cache['asset']
            interval = cache['interval']
            rt_data  = robot.api.get_realtime_candles(asset, interval)
            if not rt_data:
                return jsonify({'status': 'active', 'data': []})
            candles = [_rt_candle_to_dict(ts, c) for ts, c in rt_data.items()]
            candles.sort(key=lambda x: x['time'])
            return jsonify({'status': 'active', 'data': candles})
        except Exception as ex:
            return jsonify({'status': 'error', 'message': str(ex)})

    return jsonify({'status': status})


@app.route('/iqoption/rt-stop', methods=['POST'])
@login_required
def iqoption_rt_stop():
    """Stop the active real-time candle stream."""
    user_id = current_user.id
    cache   = rt_stream_cache.pop(user_id, None)
    if cache and cache.get('robot'):
        try:
            cache['robot'].api.stop_candles_stream(
                cache['asset'], cache['interval'])
        except Exception:
            pass
    return jsonify({'success': True})


# ─── Backtest cache: user_id → {status, progress, result, message} ────────────
backtest_cache: dict = {}


@app.route('/backtest/run', methods=['POST'])
@login_required
def backtest_run():
    """Launch a background backtest for ATV Aggressive Scalper M1."""
    if AtvScalperM1 is None or fetch_candles_range is None:
        return jsonify({'success': False, 'message': 'Strategy module tidak tersedia.'})

    data        = request.get_json() or {}
    user_id     = current_user.id
    asset       = data.get('asset', 'EURUSD-OTC')
    months      = int(data.get('months', 12))        # 3 / 6 / 12 / 24
    payout      = float(data.get('payout', 0.82))
    iq_email    = data.get('iq_email', '')
    iq_password = data.get('iq_password', '')
    account_type = data.get('account_type', 'PRACTICE')

    if not iq_email or not iq_password:
        return jsonify({'success': False, 'message': 'Masukkan email & password IQ Option.'})

    # Block if already running
    if backtest_cache.get(user_id, {}).get('status') == 'running':
        return jsonify({'success': False, 'message': 'Backtest sedang berjalan…'})

    backtest_cache[user_id] = {
        'status': 'running', 'progress': 0,
        'message': 'Menginisialisasi…', 'result': None
    }

    def _run(uid, email, password, acct, ast, mon, pay):
        def prog(pct, msg):
            backtest_cache[uid]['progress'] = pct
            backtest_cache[uid]['message']  = msg

        try:
            prog(2, 'Menghubungkan ke IQ Option…')
            # Prefer existing connected robot
            robot = None
            rt = rt_stream_cache.get(uid)
            if rt and rt.get('status') == 'active' and rt.get('robot'):
                robot = rt['robot']
            elif uid in active_bots and active_bots[uid].check_connect():
                robot = active_bots[uid]

            if robot is None:
                robot = IQTradingRobot(email, password)
                ok = robot.connect()
                if not ok:
                    backtest_cache[uid] = {
                        'status': 'error', 'progress': 0,
                        'message': 'Gagal konek ke IQ Option.', 'result': None
                    }
                    return
                robot.change_balance(acct)
                time.sleep(1)

            prog(5, f'Mengambil data M1 {ast} ({mon} bulan)…')
            end_ts   = time.time()
            start_ts = end_ts - mon * 30.5 * 24 * 3600  # approximate

            candles = fetch_candles_range(
                robot, ast, 60, start_ts, end_ts, progress_cb=prog)

            if not candles:
                backtest_cache[uid] = {
                    'status': 'error', 'progress': 0,
                    'message': f'Tidak ada data candle untuk {ast}.', 'result': None
                }
                return

            prog(99, f'Menjalankan backtest ({len(candles):,} candle)…')
            strategy = AtvScalperM1()
            result   = strategy.backtest(candles, payout=pay)

            # Fill average signals/day
            if result['total_signals'] > 0 and mon > 0:
                trading_days = mon * 22   # ~22 trading days/month
                result['avg_signals_day'] = round(result['total_signals'] / trading_days, 1)

            result['asset']          = ast
            result['period_months']  = mon
            result['candles_tested'] = len(candles)
            result['start_date']     = datetime.utcfromtimestamp(candles[0]['time']).strftime('%Y-%m-%d')
            result['end_date']       = datetime.utcfromtimestamp(candles[-1]['time']).strftime('%Y-%m-%d')

            backtest_cache[uid] = {
                'status': 'done', 'progress': 100,
                'message': 'Backtest selesai.', 'result': result
            }
            logger.info(f"Backtest done: user={uid} asset={ast} "
                        f"win_rate={result['win_rate']}% signals={result['total_signals']}")

        except Exception as ex:
            logger.exception(f'Backtest error: {ex}')
            backtest_cache[uid] = {
                'status': 'error', 'progress': 0,
                'message': f'Error: {str(ex)}', 'result': None
            }

    from datetime import datetime
    threading.Thread(
        target=_run,
        args=(user_id, iq_email, iq_password, account_type,
              asset, months, payout),
        daemon=True
    ).start()
    return jsonify({'success': True})


@app.route('/backtest/status', methods=['GET'])
@login_required
def backtest_status():
    """Poll endpoint for backtest progress and result."""
    user_id = current_user.id
    cache   = backtest_cache.get(user_id, {
        'status': 'idle', 'progress': 0, 'message': '', 'result': None
    })
    return jsonify(cache)


# ─── Strategy Generator cache: user_id → {status, generator, progress, results} ─
generator_cache: dict = {}


STRATEGY_PRESETS = [
    {
        'rank': 1,
        'name': 'Stoch + Chaikin (Low Risk)',
        'badge': 'Risiko Rendah',
        'badge_color': 'success',
        'win_rate': 70.0,
        'max_drawdown': 8.0,
        'total_trades': 10,
        'min_agreement': 1,
        'indicators': [
            {'id': 'STOCH',      'params': {'k_period': 15, 'k_smooth': 5, 'd_smooth': 2}},
            {'id': 'CHAIKIN_MF', 'params': {'period': 9}},
        ],
    },
    {
        'rank': 2,
        'name': 'Stoch+RSI + Elder Ray + Fractal',
        'badge': 'Risiko Rendah',
        'badge_color': 'success',
        'win_rate': 70.0,
        'max_drawdown': 8.0,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'STOCH_RSI',  'params': {'rsi_period': 10, 'stoch_k': 13}},
            {'id': 'ELDER_RAY',  'params': {'period': 10}},
            {'id': 'FRACTAL',    'params': {'bars': 2}},
        ],
    },
    {
        'rank': 3,
        'name': 'Fractal + Donchian + Vortex ADX',
        'badge': 'Risiko Rendah',
        'badge_color': 'success',
        'win_rate': 70.0,
        'max_drawdown': 10.0,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'FRACTAL',    'params': {'bars': 3}},
            {'id': 'DONCHIAN',   'params': {'period': 55}},
            {'id': 'VORTEX_ADX', 'params': {'period': 18, 'adx_th': 21}},
        ],
    },
    {
        'rank': 4,
        'name': 'Parabolic SAR + Keltner',
        'badge': 'Sedang',
        'badge_color': 'warning',
        'win_rate': 70.0,
        'max_drawdown': 21.5,
        'total_trades': 10,
        'min_agreement': 1,
        'indicators': [
            {'id': 'PARABOLIC_SAR', 'params': {}},
            {'id': 'KELTNER',       'params': {'period': 21}},
        ],
    },
    {
        'rank': 5,
        'name': 'Vortex + EMA + Williams %R',
        'badge': 'Sedang',
        'badge_color': 'warning',
        'win_rate': 70.0,
        'max_drawdown': 21.5,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'VORTEX',    'params': {'period': 10}},
            {'id': 'EMA',       'params': {'period': 192}},
            {'id': 'WILLIAMS_R','params': {'period': 11}},
        ],
    },
    {
        'rank': 6,
        'name': 'MACD+RSI + Stoch + Keltner Break',
        'badge': 'Sedang',
        'badge_color': 'warning',
        'win_rate': 70.0,
        'max_drawdown': 21.5,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'MACD_RSI',      'params': {'rsi_period': 8, 'macd_fast': 15, 'macd_slow': 23}},
            {'id': 'STOCH',         'params': {'k_period': 20, 'k_smooth': 3, 'd_smooth': 3}},
            {'id': 'KELTNER_BREAK', 'params': {'period': 20}},
        ],
    },
    {
        'rank': 7,
        'name': 'Stoch+RSI + Squeeze + Candlestick',
        'badge': 'Agresif',
        'badge_color': 'danger',
        'win_rate': 70.0,
        'max_drawdown': 25.7,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'STOCH_RSI',     'params': {'rsi_period': 9, 'stoch_k': 16}},
            {'id': 'SQUEEZE',       'params': {'period': 24}},
            {'id': 'CANDLE_PATTERN','params': {}},
        ],
    },
    {
        'rank': 8,
        'name': 'ROC + NATR + MACD+RSI',
        'badge': 'Agresif',
        'badge_color': 'danger',
        'win_rate': 70.0,
        'max_drawdown': 25.7,
        'total_trades': 10,
        'min_agreement': 2,
        'indicators': [
            {'id': 'ROC',      'params': {'period': 11}},
            {'id': 'NATR',     'params': {'period': 10}},
            {'id': 'MACD_RSI', 'params': {'rsi_period': 10, 'macd_fast': 10, 'macd_slow': 29}},
        ],
    },
]


@app.route('/strategy-generator/presets', methods=['GET'])
@login_required
def strategy_generator_presets():
    """Return list of pre-searched best strategies as presets."""
    from strategy_generator import INDICATOR_CATALOG
    enriched = []
    for p in STRATEGY_PRESETS:
        inds = []
        for ind in p['indicators']:
            iid  = ind['id']
            meta = INDICATOR_CATALOG.get(iid, {})
            inds.append({
                'id':       iid,
                'label':    meta.get('label', iid),
                'category': meta.get('category', ''),
                'params':   ind['params'],
            })
        enriched.append({**p, 'indicators': inds})
    return jsonify({'success': True, 'presets': enriched})


@app.route('/strategy-generator/indicators', methods=['GET'])
@login_required
def strategy_generator_indicators():
    """Return the full indicator catalog grouped by category."""
    if not INDICATOR_CATALOG:
        return jsonify({'success': False, 'message': 'Strategy generator tidak tersedia.'})
    grouped = {}
    for iid, info in INDICATOR_CATALOG.items():
        cat = info['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            'id': iid,
            'label': info['label'],
            'params': info['params'],
            'defaults': info['defaults'],
        })
    return jsonify({'success': True, 'catalog': grouped})


@app.route('/strategy-generator/run', methods=['POST'])
@login_required
def strategy_generator_run():
    """Start the strategy generator in background."""
    if StrategyGenerator is None:
        return jsonify({'success': False, 'message': 'Strategy generator tidak tersedia.'})

    data = request.get_json() or {}
    user_id = current_user.id

    if generator_cache.get(user_id, {}).get('status') == 'running':
        return jsonify({'success': False, 'message': 'Generator sudah berjalan.'})

    iq_email = data.get('iq_email', '')
    iq_password = data.get('iq_password', '')
    account_type = data.get('account_type', 'PRACTICE')
    asset = data.get('asset', 'EURUSD-OTC')
    interval = int(data.get('interval', 60))
    months = int(data.get('months', 3))
    allowed_indicators = data.get('indicators', list(INDICATOR_CATALOG.keys()))
    min_indicators = int(data.get('min_indicators', 2))
    max_indicators = int(data.get('max_indicators', 4))

    modal = float(data.get('modal', 100.0))
    amount = float(data.get('amount', 10.0))
    stop_loss = float(data.get('stop_loss', 30.0))
    stop_win = float(data.get('stop_win', 50.0))
    martingale_steps = int(data.get('martingale_steps', 3))
    martingale_multiplier = float(data.get('martingale_multiplier', 2.2))
    payout = float(data.get('payout', 0.82))

    if not iq_email or not iq_password:
        return jsonify({'success': False, 'message': 'Masukkan email & password IQ Option.'})

    if not allowed_indicators:
        return jsonify({'success': False, 'message': 'Pilih minimal 1 indikator.'})

    generator_cache[user_id] = {
        'status': 'fetching',
        'iterations': 0,
        'found': 0,
        'best_wr': 0.0,
        'speed': 0.0,
        'results': [],
        'message': 'Mengambil data candle dari IQ Option…',
    }

    def _run(uid, email, password, acct, ast, ivl, mon,
             allowed, min_ind, max_ind, modal, amount, sl, sw, mrt_s, mrt_m, pay):
        try:
            # Connect & fetch candles
            robot = None
            rt = rt_stream_cache.get(uid)
            if rt and rt.get('status') == 'active' and rt.get('robot'):
                robot = rt['robot']
            elif uid in active_bots and active_bots[uid].check_connect():
                robot = active_bots[uid]

            if robot is None:
                robot = IQTradingRobot(email, password)
                if not robot.connect():
                    generator_cache[uid] = {
                        'status': 'error',
                        'message': 'Gagal konek ke IQ Option.',
                        'results': [],
                    }
                    return
                robot.change_balance(acct)
                time.sleep(1)

            generator_cache[uid]['message'] = f'Mengambil candle {ast} ({mon} bulan)…'
            end_ts = time.time()
            start_ts = end_ts - mon * 30.5 * 24 * 3600

            candles = fetch_candles_range(robot, ast, ivl, start_ts, end_ts)
            if not candles:
                generator_cache[uid] = {
                    'status': 'error',
                    'message': f'Tidak ada data candle untuk {ast}.',
                    'results': [],
                }
                return

            generator_cache[uid]['message'] = f'Memulai pencarian strategi ({len(candles):,} candle)…'
            generator_cache[uid]['status'] = 'running'

            trading = GenTradingConfig(
                modal=modal, amount=amount,
                stop_loss=sl, stop_win=sw,
                martingale_steps=mrt_s,
                martingale_multiplier=mrt_m,
                payout=pay,
            )

            gen = StrategyGenerator(
                candles=candles,
                trading=trading,
                allowed_indicators=allowed,
                min_indicators=min_ind,
                max_indicators=max_ind,
            )
            generator_cache[uid]['_gen'] = gen

            def _progress(iterations, found, best_wr, speed):
                if generator_cache.get(uid, {}).get('status') == 'running':
                    generator_cache[uid].update({
                        'iterations': iterations,
                        'found': found,
                        'best_wr': round(best_wr, 2),
                        'speed': round(speed, 1),
                        'results': gen.results_as_dicts(),
                        'message': (
                            f'{iterations:,} kombinasi diuji — '
                            f'{found} strategi valid — '
                            f'Win Rate terbaik: {best_wr:.1f}%'
                        ),
                    })

            gen.run(progress_cb=_progress)

            generator_cache[uid].update({
                'status': 'done',
                'results': gen.results_as_dicts(),
                'iterations': gen.iterations,
                'found': len(gen.best),
                'message': (
                    f'Selesai! {gen.iterations:,} kombinasi diuji, '
                    f'{len(gen.best)} strategi terbaik ditemukan.'
                ),
            })

        except Exception as ex:
            logger.exception(f'Generator error: {ex}')
            generator_cache[uid] = {
                'status': 'error',
                'message': f'Error: {str(ex)}',
                'results': [],
            }

    threading.Thread(
        target=_run,
        args=(user_id, iq_email, iq_password, account_type, asset, interval, months,
              allowed_indicators, min_indicators, max_indicators,
              modal, amount, stop_loss, stop_win, martingale_steps, martingale_multiplier, payout),
        daemon=True,
    ).start()

    return jsonify({'success': True})


@app.route('/strategy-generator/status', methods=['GET'])
@login_required
def strategy_generator_status():
    """Poll endpoint for generator progress."""
    user_id = current_user.id
    cache = generator_cache.get(user_id, {
        'status': 'idle', 'iterations': 0, 'found': 0,
        'best_wr': 0.0, 'speed': 0.0, 'results': [], 'message': '',
    })
    safe = {k: v for k, v in cache.items() if k != '_gen'}
    return jsonify(safe)


@app.route('/strategy-generator/stop', methods=['POST'])
@login_required
def strategy_generator_stop():
    """Stop the running generator."""
    user_id = current_user.id
    cache = generator_cache.get(user_id, {})
    gen = cache.get('_gen')
    if gen:
        gen.stop()
    if cache.get('status') == 'running':
        generator_cache[user_id]['status'] = 'stopped'
        generator_cache[user_id]['message'] = 'Generator dihentikan oleh pengguna.'
    return jsonify({'success': True})


@app.route('/strategy-generator/apply', methods=['POST'])
@login_required
def strategy_generator_apply():
    """Apply a discovered strategy's trading config to the user's bot settings."""
    try:
        data = request.get_json() or {}
        user_id = current_user.id

        settings = BotSetting.query.filter_by(user_id=user_id).first()
        if not settings:
            return jsonify({'success': False, 'message': 'Bot settings belum dikonfigurasi.'})

        if 'amount' in data:
            settings.trading_amount = float(data['amount'])
        if 'stop_win' in data:
            settings.stop_win = float(data['stop_win'])
        if 'stop_loss' in data:
            settings.stop_loss = float(data['stop_loss'])
        if 'martingale_steps' in data:
            settings.step_martingale = int(data['martingale_steps'])
        if 'martingale_multiplier' in data:
            settings.martingale_multiple = float(data['martingale_multiplier'])

        db.session.commit()
        return jsonify({'success': True, 'message': 'Konfigurasi trading berhasil diterapkan ke bot!'})
    except Exception as ex:
        return jsonify({'success': False, 'message': str(ex)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
