#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contoh penggunaan IQ Option Trading Robot
"""

from iq_trading_robot import IQTradingRobot
import time

def simple_trading_example():
    """
    Contoh sederhana untuk menjalankan trading robot
    """
    print("🎯 Contoh Penggunaan IQ Option Trading Robot")
    print("=" * 50)
    
    # Masukkan kredensial IQ Option Anda
    email = "email_anda@example.com"  # Ganti dengan email Anda
    password = "password_anda"        # Ganti dengan password Anda
    
    # Buat robot instance
    robot = IQTradingRobot(email, password)
    
    # Konfigurasi robot
    robot.asset = "EURUSD-OTC"  # Asset yang akan ditrade
    robot.trading_amount = 1    # Jumlah trading $1
    robot.strategy = "martingale"  # Strategy yang digunakan
    robot.timeframe = 1         # Timeframe 1 menit
    robot.max_consecutive_losses = 3  # Maksimal 3 loss berturut-turut
    
    try:
        # 1. Connect ke IQ Option
        print("🔄 Menghubungkan ke IQ Option...")
        if not robot.connect():
            print("❌ Gagal terhubung. Periksa kredensial Anda.")
            return
        
        print("✅ Berhasil terhubung!")
        print(f"💰 Saldo: ${robot.balance}")
        
        # 2. Start trading
        print("🚀 Memulai trading robot...")
        robot.start_trading()
        
        # 3. Biarkan robot berjalan selama beberapa menit
        print("⏳ Robot sedang berjalan. Tekan Ctrl+C untuk berhenti...")
        
        # Trading akan berjalan sampai dihentikan atau mencapai max losses
        while robot.is_trading:
            time.sleep(10)
            # Tampilkan status setiap 10 detik
            print(f"📊 Status: Trading aktif | Total Profit: ${robot.profit_total:.2f}")
        
    except KeyboardInterrupt:
        print("\n🛑 Trading dihentikan oleh user")
    
    finally:
        # 4. Stop trading dan disconnect
        robot.stop_trading()
        robot.disconnect()
        
        # 5. Tampilkan ringkasan
        robot.get_trading_summary()

def advanced_trading_example():
    """
    Contoh lanjutan dengan kustomisasi lebih detail
    """
    print("🎯 Trading Robot - Mode Advanced")
    print("=" * 50)
    
    # Setup robot dengan konfigurasi kustom
    robot = IQTradingRobot("your_email@example.com", "your_password")
    
    # Konfigurasi advanced
    robot.asset = "GBPUSD-OTC"
    robot.trading_amount = 2
    robot.strategy = "martingale"
    robot.martingale_multiplier = 2.5
    robot.timeframe = 1
    robot.max_consecutive_losses = 5
    
    try:
        if robot.connect():
            print("✅ Terhubung! Memulai advanced trading...")
            
            # Custom trading logic bisa ditambahkan di sini
            # Misalnya: cek kondisi market, waktu trading, dll
            
            current_hour = time.localtime().tm_hour
            if 8 <= current_hour <= 17:  # Trading hanya jam 8 pagi - 5 sore
                robot.start_trading()
                
                # Monitor dan kontrol lebih detail
                trade_count = 0
                max_trades = 10  # Maksimal 10 trades per session
                
                while robot.is_trading and trade_count < max_trades:
                    time.sleep(60)  # Check setiap menit
                    trade_count = len(robot.trades_history)
                    
                    # Stop jika profit sudah mencapai target
                    if robot.profit_total >= 20:  # Target profit $20
                        print("🎉 Target profit tercapai! Menghentikan trading...")
                        break
                    
                    # Stop jika loss terlalu besar
                    if robot.profit_total <= -20:  # Maximum loss $20
                        print("⚠️ Maximum loss tercapai! Menghentikan trading...")
                        break
            else:
                print("⏰ Trading hanya dilakukan pada jam 08:00 - 17:00")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        robot.stop_trading()
        robot.disconnect()
        robot.get_trading_summary()

if __name__ == "__main__":
    print("Pilih mode trading:")
    print("1. Simple Trading")
    print("2. Advanced Trading")
    
    choice = input("Pilihan (1/2): ").strip()
    
    if choice == "1":
        simple_trading_example()
    elif choice == "2":
        advanced_trading_example()
    else:
        print("❌ Pilihan tidak valid!")