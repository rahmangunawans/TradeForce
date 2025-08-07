import os
from flask import Flask, render_template, url_for

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "auto-trade-vip-secret-key")

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
    
    return render_template('index.html', brokers=brokers, packages=packages)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
