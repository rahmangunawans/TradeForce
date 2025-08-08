#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from iqoptionapi.stable_api import IQ_Option
import time
import threading
from datetime import datetime, timedelta
import json

class IQTradingRobot:
    def __init__(self, email, password):
        """
        Inisialisasi Robot Trading IQ Option
        """
        self.email = email
        self.password = password
        self.api = None
        self.balance = 0
        self.is_connected = False
        self.is_trading = False
        self.trading_thread = None
        
        # Trading Settings
        self.trading_amount = 1  # Jumlah trading dalam USD
        self.initial_amount = 1  # Amount awal untuk reset
        self.asset = "EURUSD-OTC"  # Asset yang akan di trade
        self.timeframe = 1  # Timeframe dalam menit
        
        # Stop Settings
        self.stop_win = 10.0  # Stop trading saat profit mencapai ini
        self.stop_loss = 10.0  # Stop trading saat loss mencapai ini
        
        # Martingale Settings
        self.strategy = "martingale"  # Strategy yang digunakan
        self.step_martingale = 3  # Jumlah step martingale
        self.martingale_multiple = 2.2  # Multiplier martingale
        self.current_step = 0  # Current martingale step
        self.max_consecutive_losses = 3  # Maksimal loss berturut-turut
        self.consecutive_losses = 0
        
        # Signal Settings
        self.signal_type = "mt4_next_signal"  # Signal source type
        self.signal_content = ""  # Manual signal content
        self.parsed_signals = []  # Parsed signal list
        self.current_signal_index = 0  # Current signal index for processing
        
        # Trade History
        self.trades_history = []
        self.profit_total = 0
        self.start_balance = 0
        
        print("🤖 IQ Option Trading Robot v1.0")
        print("=" * 50)
    
    def parse_signal_content(self):
        """
        Parse signal content in format: YYYY-MM-DD HH:MM:SS,PAIR,CALL/PUT,TIMEFRAME
        """
        self.parsed_signals = []
        if not self.signal_content:
            return
            
        lines = self.signal_content.strip().split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
                
            try:
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 4:
                    timestamp_str, pair, direction, timeframe = parts[0], parts[1], parts[2], parts[3]
                    
                    # Parse timestamp
                    signal_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Validate direction
                    direction = direction.upper()
                    if direction not in ['CALL', 'PUT']:
                        print(f"⚠️ Invalid direction '{direction}' on line {line_num}, skipping")
                        continue
                    
                    # Parse timeframe
                    timeframe = int(timeframe)
                    
                    signal = {
                        'time': signal_time,
                        'pair': pair.upper(),
                        'direction': direction,
                        'timeframe': timeframe,
                        'processed': False
                    }
                    self.parsed_signals.append(signal)
                else:
                    print(f"⚠️ Invalid signal format on line {line_num}: {line}")
                    
            except ValueError as e:
                print(f"⚠️ Error parsing line {line_num}: {line} - {e}")
                
        print(f"📊 Parsed {len(self.parsed_signals)} signals from content")
    
    def get_next_signal(self):
        """
        Get the next signal that should be executed based on current time
        """
        if self.signal_type != "manual_input" or not self.parsed_signals:
            return None
            
        current_time = datetime.now()
        
        # Find signals that are ready to be executed (time has passed)
        for i, signal in enumerate(self.parsed_signals):
            if not signal['processed'] and signal['time'] <= current_time:
                # Mark as processed and return
                signal['processed'] = True
                return signal
                
        return None
    
    def configure_from_settings(self, settings):
        """
        Configure robot from database settings
        """
        if settings:
            self.trading_amount = settings.trading_amount
            self.initial_amount = settings.trading_amount
            self.stop_win = settings.stop_win
            self.stop_loss = settings.stop_loss
            self.step_martingale = settings.step_martingale
            self.martingale_multiple = settings.martingale_multiple
            self.asset = settings.asset
            self.strategy = settings.strategy
            self.max_consecutive_losses = settings.max_consecutive_losses
            self.signal_type = settings.signal_type
            self.signal_content = settings.signal_content or ""
            
            # Parse signal content if manual_input is selected
            if self.signal_type == "manual_input" and self.signal_content:
                self.parse_signal_content()
            
            print(f"⚙️ Configuration loaded:")
            print(f"   Amount: ${self.trading_amount}")
            print(f"   Stop Win: ${self.stop_win}")
            print(f"   Stop Loss: ${self.stop_loss}")
            if self.strategy == "martingale":
                print(f"   Martingale Steps: {self.step_martingale}")
                print(f"   Multiple: {self.martingale_multiple}")
            print(f"   Asset: {self.asset}")
            print(f"   Strategy: {self.strategy}")
            print(f"   Signal Type: {self.signal_type}")
            if self.signal_type == "manual_input":
                print(f"   Parsed Signals: {len(self.parsed_signals)}")
    
    def connect(self):
        """Koneksi ke IQ Option dengan session clearing"""
        print("🔄 Menghubungkan ke IQ Option...")
        try:
            # Clear any existing connection first
            if self.api:
                try:
                    self.api.api.close()
                except:
                    pass
                self.api = None
            
            # Create fresh connection
            self.api = IQ_Option(self.email, self.password)
            check, reason = self.api.connect()
            
            if check:
                self.is_connected = True
                
                # Get initial balance
                try:
                    self.balance = self.api.get_balance()
                    print(f"✅ Berhasil terhubung!")
                    print(f"💰 Saldo: ${self.balance}")
                    
                    # Keep connection stable
                    time.sleep(1)
                    return True
                except Exception as balance_error:
                    print(f"⚠️ Error getting balance: {balance_error}")
                    self.balance = 0
                    return True  # Still return True if connected but can't get balance
            else:
                print(f"❌ Gagal terhubung: {reason}")
                self.is_connected = False
                return False
        except Exception as e:
            print(f"❌ Error koneksi: {e}")
            self.is_connected = False
            self.api = None
            return False
    
    def disconnect(self):
        """Disconnect dari IQ Option"""
        if self.api:
            self.is_trading = False
            try:
                self.api.api.close()
            except:
                pass
            self.is_connected = False
            print("📡 Koneksi terputus")
    
    def get_balance(self):
        """Get current balance"""
        if self.api and self.is_connected:
            try:
                balance = self.api.get_balance()
                return balance if balance is not None else 0
            except Exception as e:
                print(f"⚠️ Error getting balance: {e}")
                return 0
        return 0
    
    def change_balance(self, balance_type='PRACTICE'):
        """Change balance type (PRACTICE/REAL)"""
        if self.api and self.is_connected:
            try:
                self.api.change_balance(balance_type)
                time.sleep(1)  # Wait for balance change
                return True
            except Exception as e:
                print(f"⚠️ Error changing balance: {e}")
                return False
        return False
    
    def get_candle_data(self, asset, timeframe=1, count=10):
        """Ambil data candle"""
        if not self.api or not self.is_connected:
            print("❌ Not connected to IQ Option")
            return None
            
        try:
            candles = self.api.get_candles(asset, timeframe * 60, count, time.time())
            return candles
        except Exception as e:
            print(f"❌ Error mengambil data candle: {e}")
            return None
    
    def analyze_trend(self, candles):
        """
        Analisis trend sederhana berdasarkan candle
        Return: 'call' untuk naik, 'put' untuk turun, 'sideways' untuk sideways
        """
        if not candles or len(candles) < 3:
            return "sideways"
        
        # Ambil 3 candle terakhir
        last_candles = candles[-3:]
        closes = [candle['close'] for candle in last_candles]
        
        # Trend naik jika close naik terus
        if closes[0] < closes[1] < closes[2]:
            return "call"
        # Trend turun jika close turun terus  
        elif closes[0] > closes[1] > closes[2]:
            return "put"
        else:
            return "sideways"
    
    def rsi_analysis(self, candles, period=14):
        """
        Analisis RSI sederhana
        """
        if not candles or len(candles) < period + 1:
            return 50
        
        closes = [candle['close'] for candle in candles[-period-1:]]
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def should_trade(self, candles):
        """
        Logika untuk menentukan apakah harus trade berdasarkan signal type
        """
        # Handle manual signal input
        if self.signal_type == "manual_input":
            signal = self.get_next_signal()
            if signal:
                print(f"🎯 Signal ditemukan: {signal['pair']} - {signal['direction']} pada {signal['time']}")
                # Update asset untuk signal ini
                self.asset = signal['pair']
                return True, signal['direction'].lower()
            else:
                return False, None
        
        # Original candle-based analysis for other signal types
        if not candles:
            return False, None
        
        trend = self.analyze_trend(candles)
        rsi = self.rsi_analysis(candles)
        
        # Trading signal berdasarkan RSI dan trend
        if rsi < 30 and trend != "put":  # Oversold + tidak downtrend
            return True, "call"
        elif rsi > 70 and trend != "call":  # Overbought + tidak uptrend
            return True, "put"
        elif trend == "call" and rsi < 60:  # Strong uptrend
            return True, "call"  
        elif trend == "put" and rsi > 40:  # Strong downtrend
            return True, "put"
        
        return False, None
    
    def place_order(self, direction, amount):
        """
        Tempatkan order
        """
        if not self.api or not self.is_connected:
            print("❌ Not connected to IQ Option")
            return False, None
            
        try:
            expiration = 1  # 1 menit
            
            print(f"📊 Menempatkan order: {direction.upper()} - ${amount}")
            
            success, order_id = self.api.buy(
                amount, self.asset, direction, expiration
            )
            
            if success:
                print(f"✅ Order berhasil ditempatkan! ID: {order_id}")
                return True, order_id
            else:
                print("❌ Gagal menempatkan order")
                return False, None
                
        except Exception as e:
            print(f"❌ Error place order: {e}")
            return False, None
    
    def wait_for_result(self, order_id):
        """
        Tunggu hasil dari order
        """
        if not self.api or not self.is_connected:
            print("❌ Not connected to IQ Option")
            return "error", 0
            
        print("⏳ Menunggu hasil trading...")
        time.sleep(65)  # Tunggu 1 menit + buffer
        
        try:
            # Cek hasil trade
            result = self.api.check_win_v3(order_id)
            
            if result > 0:
                profit = result
                self.profit_total += profit
                self.consecutive_losses = 0
                print(f"🎉 WIN! Profit: ${profit:.2f} | Total Profit: ${self.profit_total:.2f}")
                return "win", profit
            else:
                loss = self.trading_amount
                self.profit_total -= loss
                self.consecutive_losses += 1
                print(f"😢 LOSS! Loss: ${loss:.2f} | Total Profit: ${self.profit_total:.2f}")
                return "loss", loss
                
        except Exception as e:
            print(f"❌ Error cek hasil: {e}")
            return "error", 0
    
    def update_trading_amount(self, result):
        """
        Update jumlah trading berdasarkan strategy
        """
        if self.strategy == "martingale":
            if result == "loss":
                self.current_step += 1
                if self.current_step <= self.step_martingale:
                    self.trading_amount = float(self.trading_amount) * float(self.martingale_multiple)
                else:
                    # Reset setelah mencapai max step
                    self.trading_amount = self.initial_amount
                    self.current_step = 0
            elif result == "win":
                # Reset ke amount awal setelah win
                self.trading_amount = self.initial_amount
                self.current_step = 0
        elif self.strategy == "fixed":
            # Fixed amount selalu sama
            self.trading_amount = self.initial_amount
        
        # Pastikan tidak melebihi balance
        if self.balance and self.trading_amount > float(self.balance) * 0.1:  # Maksimal 10% dari balance
            self.trading_amount = float(self.balance) * 0.1
    
    def trading_loop(self):
        """
        Loop utama trading
        """
        print("🚀 Memulai trading...")
        print(f"📊 Asset: {self.asset}")
        print(f"💰 Amount: ${self.trading_amount}")
        print(f"📈 Strategy: {self.strategy}")
        if self.strategy == "martingale":
            print(f"🔄 Martingale Steps: {self.step_martingale}")
            print(f"✖️ Multiple: {self.martingale_multiple}")
        print(f"🏆 Stop Win: ${self.stop_win}")
        print(f"🛑 Stop Loss: ${self.stop_loss}")
        print("=" * 50)
        
        # Set start balance for tracking
        self.start_balance = self.balance
        
        while self.is_trading and self.is_connected:
            try:
                # Cek balance
                try:
                    current_balance = self.api.get_balance()
                    if current_balance and current_balance != self.balance:
                        self.balance = current_balance
                        print(f"💰 Balance update: ${self.balance}")
                except:
                    pass
                
                # Cek stop conditions
                if self.consecutive_losses >= self.max_consecutive_losses:
                    print(f"⚠️ Mencapai maksimal loss berturut-turut ({self.max_consecutive_losses}). Berhenti trading.")
                    break
                
                # Cek stop win
                if self.profit_total >= self.stop_win:
                    print(f"🎉 Stop Win tercapai! Profit: ${self.profit_total:.2f}. Berhenti trading.")
                    break
                    
                # Cek stop loss
                if self.profit_total <= -self.stop_loss:
                    print(f"❌ Stop Loss tercapai! Loss: ${abs(self.profit_total):.2f}. Berhenti trading.")
                    break
                
                # Ambil data candle
                candles = self.get_candle_data(self.asset, self.timeframe)
                if not candles:
                    print("⚠️ Tidak bisa ambil data candle. Mencoba lagi...")
                    time.sleep(5)
                    continue
                
                # Analisis apakah harus trade berdasarkan signal type
                should_trade, direction = self.should_trade(candles)
                
                if should_trade:
                    # Place order
                    success, order_id = self.place_order(direction, self.trading_amount)
                    
                    if success:
                        # Tunggu hasil
                        result, amount = self.wait_for_result(order_id)
                        
                        # Simpan ke history
                        trade_data = {
                            'timestamp': datetime.now().isoformat(),
                            'asset': self.asset,
                            'direction': direction,
                            'amount': self.trading_amount,
                            'result': result,
                            'profit_loss': amount if result == 'win' else -amount,
                            'balance_after': self.balance
                        }
                        self.trades_history.append(trade_data)
                        
                        # Update trading amount berdasarkan strategy
                        self.update_trading_amount(result)
                else:
                    print("📊 Tidak ada signal trading. Menunggu...")
                
                # Tunggu sebelum analisis berikutnya
                print(f"⏳ Menunggu {self.timeframe} menit untuk analisis berikutnya...")
                print(f"📊 Current Status: Step {self.current_step}/{self.step_martingale}, Amount: ${self.trading_amount:.2f}")
                time.sleep(self.timeframe * 60)  # Tunggu sesuai timeframe
                
            except KeyboardInterrupt:
                print("\n🛑 Trading dihentikan oleh user")
                break
            except Exception as e:
                print(f"❌ Error dalam trading loop: {e}")
                time.sleep(5)
        
        self.is_trading = False
        print("🏁 Trading selesai")
    
    def start_trading(self):
        """
        Start trading dalam thread terpisah
        """
        if not self.is_connected:
            print("❌ Belum terhubung ke IQ Option")
            return False
            
        if self.is_trading:
            print("⚠️ Trading sudah berjalan")
            return False
        
        self.is_trading = True
        self.trading_thread = threading.Thread(target=self.trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        return True
    
    def stop_trading(self):
        """
        Stop trading
        """
        self.is_trading = False
        if self.trading_thread:
            self.trading_thread.join()
        print("🛑 Trading dihentikan")
    
    def get_trading_summary(self):
        """
        Tampilkan ringkasan trading
        """
        if not self.trades_history:
            print("📊 Belum ada history trading")
            return
        
        wins = len([t for t in self.trades_history if t['result'] == 'win'])
        losses = len([t for t in self.trades_history if t['result'] == 'loss'])
        total_trades = len(self.trades_history)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 RINGKASAN TRADING")
        print("=" * 50)
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total Profit/Loss: ${self.profit_total:.2f}")
        print(f"Current Balance: ${self.balance}")
        print("=" * 50)

def main():
    """
    Fungsi utama untuk menjalankan robot
    """
    print("🤖 IQ Option Trading Robot")
    print("=" * 50)
    
    # Input credentials
    email = input("📧 Masukkan email IQ Option: ").strip()
    password = input("🔐 Masukkan password: ").strip()
    
    if not email or not password:
        print("❌ Email dan password harus diisi!")
        return
    
    # Buat instance robot
    robot = IQTradingRobot(email, password)
    
    # Connect
    if not robot.connect():
        print("❌ Tidak bisa terhubung. Program dihentikan.")
        return
    
    try:
        # Menu pilihan
        while True:
            print("\n🎯 MENU TRADING ROBOT")
            print("1. Start Trading")
            print("2. Stop Trading") 
            print("3. Trading Summary")
            print("4. Settings")
            print("5. Keluar")
            
            choice = input("\nPilih menu (1-5): ").strip()
            
            if choice == "1":
                robot.start_trading()
            elif choice == "2":
                robot.stop_trading()
            elif choice == "3":
                robot.get_trading_summary()
            elif choice == "4":
                # Settings menu
                print(f"\nCurrent Settings:")
                print(f"Asset: {robot.asset}")
                print(f"Trading Amount: ${robot.trading_amount}")
                print(f"Strategy: {robot.strategy}")
                print(f"Timeframe: {robot.timeframe} menit")
                
                new_asset = input(f"Asset baru (default: {robot.asset}): ").strip()
                if new_asset:
                    robot.asset = new_asset
                
                new_amount = input(f"Trading amount (default: ${robot.trading_amount}): ").strip()
                if new_amount and new_amount.isdigit():
                    robot.trading_amount = float(new_amount)
                
                print("✅ Settings updated!")
                
            elif choice == "5":
                robot.stop_trading()
                robot.disconnect()
                print("👋 Terima kasih telah menggunakan Trading Robot!")
                break
            else:
                print("❌ Pilihan tidak valid!")
    
    except KeyboardInterrupt:
        robot.stop_trading()
        robot.disconnect()
        print("\n👋 Program dihentikan")

if __name__ == "__main__":
    main()