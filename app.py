import os
from flask import Flask, render_template

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "auto-trade-vip-secret-key")

@app.route('/')
def index():
    """Landing page for AUTO TRADE VIP"""
    
    # Broker data for carousel
    brokers = [
        {
            'name': 'Binomo',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSK4zylqyfITSoEkIeL8KEz9E-WZmiK4rSy_pYQw6CZfoWvC85vcBXiXwkU&s=10'
        },
        {
            'name': 'Olymptrade',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRsUoKOR44xhomqsCSBhe-Vl8ouy_tPbQx21_ulOz5Hu8_H3pP9PcQCKk8&s=10'
        },
        {
            'name': 'Stockity',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSRMgQ9EISDJH3P7RTavxp-7dA3MPetjfWtFbZcQCno5cUmkdAK96_KrN0&s=10'
        },
        {
            'name': 'IQ Option',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQbXua0ti3GfHAsXE-cvuwOVzES7I1RLQ_2Yl07lffsfxaoYfaDyULClRA&s=10'
        },
        {
            'name': 'Quotex',
            'logo': 'https://play-lh.googleusercontent.com/-ltphEmoRQ5Hf_XF9MWWQ6JHkUhtK1Idblgbe8zIEIcvlIkbUa1IAcNohSK4Bu7X9mGP=w240-h480-rw'
        },
        {
            'name': 'Pocket Option',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTMD00QA51sLIOjLHXYuHooNnoNbArzoaFu3Q&s'
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
                'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQbXua0ti3GfHAsXE-cvuwOVzES7I1RLQ_2Yl07lffsfxaoYfaDyULClRA&s=10',
                'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRsUoKOR44xhomqsCSBhe-Vl8ouy_tPbQx21_ulOz5Hu8_H3pP9PcQCKk8&s=10',
                'https://play-lh.googleusercontent.com/-ltphEmoRQ5Hf_XF9MWWQ6JHkUhtK1Idblgbe8zIEIcvlIkbUa1IAcNohSK4Bu7X9mGP=w240-h480-rw',
                'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTMD00QA51sLIOjLHXYuHooNnoNbArzoaFu3Q&s'
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
                'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSK4zylqyfITSoEkIeL8KEz9E-WZmiK4rSy_pYQw6CZfoWvC85vcBXiXwkU&s=10',
                'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSRMgQ9EISDJH3P7RTavxp-7dA3MPetjfWtFbZcQCno5cUmkdAK96_KrN0&s=10'
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
