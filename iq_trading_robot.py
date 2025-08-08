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
        IQ Option Trading Robot - HANYA SIGNAL INPUT
        """
        self.email = email
        self.password = password
        self.api = None
        self.balance = 0
        self.is_connected = False
        self.is_trading = False
        self.trading_thread = None
        
        # HANYA PENGATURAN DASAR SIGNAL INPUT
        self.trading_amount = 1.0
        self.asset = "EURUSD"  # TIDAK ADA -OTC, asset standar
        self.timeframe = 1  # 1 menit
        
        # Stop Settings (sederhana)
        self.stop_win = 10.0
        self.stop_loss = 10.0
        
        # SIGNAL INPUT SETTINGS - INI SAJA YANG DIPAKAI
        self.signal_content = ""
        self.parsed_signals = []
        
        # Trade History
        self.trades_history = []
        self.profit_total = 0
        self.start_balance = 0
        
        print("🎯 SIGNAL INPUT TRADING ROBOT - VERSI SEDERHANA")
        print("📊 FOKUS: Manual Signal Input SAJA")
        print("=" * 50)
    
    def parse_signal_content(self):
        """
        Parse signal input yang sederhana:
        Format: CALL atau PUT atau CALL,1 atau CALL,2
        """
        self.parsed_signals = []
        if not self.signal_content:
            print("❌ Tidak ada signal input")
            return
            
        lines = self.signal_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip().upper()
            if not line or line.startswith('#'):
                continue
                
            try:
                if ',' in line:
                    parts = line.split(',')
                    direction = parts[0].strip()
                    timeframe = int(parts[1].strip()) if len(parts) > 1 else 1
                else:
                    direction = line.strip()
                    timeframe = 1
                
                if direction not in ['CALL', 'PUT']:
                    print(f"⚠️ Signal salah: {line} (harus CALL atau PUT)")
                    continue
                
                signal = {
                    'direction': direction,
                    'timeframe': timeframe,
                    'processed': False
                }
                self.parsed_signals.append(signal)
                print(f"✅ Signal {line_num}: {direction} {timeframe} menit - SIAP")
                    
            except Exception as e:
                print(f"❌ Error parsing line {line_num}: {line} - {e}")
                
        print(f"📊 Total {len(self.parsed_signals)} signals siap untuk trading")
    
    def get_next_signal(self):
        """
        Ambil signal berikutnya yang belum diproses
        """
        for signal in self.parsed_signals:
            if not signal['processed']:
                signal['processed'] = True
                print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']}")
                return signal
        return None
    
    def configure_from_settings(self, settings):
        """
        Konfigurasi dari database settings
        """
        if settings:
            self.trading_amount = settings.trading_amount
            self.stop_win = settings.stop_win
            self.stop_loss = settings.stop_loss
            self.asset = settings.asset
            self.signal_content = settings.signal_content or ""
            
            # Parse signal content
            if self.signal_content:
                self.parse_signal_content()
            
            print(f"⚙️ Konfigurasi:")
            print(f"   Amount: ${self.trading_amount}")
            print(f"   Asset: {self.asset}")
            print(f"   Stop Win: ${self.stop_win}")
            print(f"   Stop Loss: ${self.stop_loss}")
            print(f"   Signals: {len(self.parsed_signals)}")
    
    def connect(self):
        """Koneksi ke IQ Option"""
        print("🔄 Menghubungkan ke IQ Option...")
        try:
            if self.api:
                try:
                    self.api.api.close()
                except:
                    pass
                self.api = None
            
            self.api = IQ_Option(self.email, self.password)
            check, reason = self.api.connect()
            
            if check:
                self.is_connected = True
                try:
                    self.balance = self.api.get_balance()
                    print(f"✅ Terhubung! Saldo: ${self.balance}")
                    time.sleep(2)
                    return True
                except Exception as balance_error:
                    print(f"⚠️ Error saldo: {balance_error}")
                    self.balance = 0
                    return True
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
            self.api = None
            self.is_connected = False
            print("📡 Koneksi terputus")
    
    def get_balance(self):
        """Dapatkan saldo saat ini"""
        if self.api and self.is_connected:
            try:
                balance = self.api.get_balance()
                return balance if balance is not None else 0
            except Exception as e:
                print(f"⚠️ Error saldo: {e}")
                return 0
        return 0
    
    def change_balance(self, balance_type='PRACTICE'):
        """Ganti tipe akun (PRACTICE/REAL)"""
        if self.api and self.is_connected:
            try:
                self.api.change_balance(balance_type)
                time.sleep(1)
                return True
            except Exception as e:
                print(f"⚠️ Error ganti akun: {e}")
                return False
        return False
    
    def place_order(self, direction, amount):
        """
        Tempatkan order trading
        """
        if not self.api or not self.is_connected:
            print("❌ Tidak terhubung ke IQ Option")
            return False, None
            
        try:
            expiration = 1  # 1 menit
            
            print(f"📊 Trading: {direction.upper()} {self.asset} - ${amount}")
            
            success, order_id = self.api.buy(
                amount, self.asset, direction, expiration
            )
            
            if success:
                print(f"✅ Order berhasil! ID: {order_id}")
                return True, order_id
            else:
                print("❌ Order gagal")
                return False, None
                
        except Exception as e:
            print(f"❌ Error order: {e}")
            return False, None
    
    def wait_for_result(self, order_id):
        """
        Tunggu hasil trading
        """
        if not self.api or not self.is_connected:
            print("❌ Tidak terhubung")
            return "error", 0
            
        print("⏳ Menunggu hasil...")
        time.sleep(65)  # Tunggu 1 menit + buffer
        
        try:
            result = self.api.check_win_v3(order_id)
            
            if result > 0:
                profit = result
                self.profit_total += profit
                print(f"🎉 WIN! Profit: ${profit:.2f} | Total: ${self.profit_total:.2f}")
                return "win", profit
            else:
                loss = self.trading_amount
                self.profit_total -= loss
                print(f"😢 LOSS! Loss: ${loss:.2f} | Total: ${self.profit_total:.2f}")
                return "loss", loss
                
        except Exception as e:
            print(f"❌ Error hasil: {e}")
            return "error", 0
    
    def trading_loop(self):
        """
        TRADING LOOP SEDERHANA - HANYA SIGNAL INPUT
        """
        print("🚀 MULAI TRADING - SIGNAL INPUT ONLY")
        print(f"📊 Asset: {self.asset}")
        print(f"💰 Amount: ${self.trading_amount}")
        print("=" * 50)
        
        self.start_balance = self.balance
        
        while self.is_trading and self.is_connected:
            try:
                # Update balance
                try:
                    if self.api and self.is_connected:
                        current_balance = self.api.get_balance()
                        if current_balance and current_balance != self.balance:
                            self.balance = current_balance
                except:
                    pass
                
                # Cek stop conditions
                if self.profit_total >= self.stop_win:
                    print(f"🎉 STOP WIN! Profit: ${self.profit_total:.2f}")
                    break
                if self.profit_total <= -self.stop_loss:
                    print(f"❌ STOP LOSS! Loss: ${abs(self.profit_total):.2f}")
                    break
                
                # AMBIL DAN EKSEKUSI SIGNAL
                signal = self.get_next_signal()
                
                if signal:
                    direction = signal['direction'].lower()
                    print(f"🎯 TRADING: {direction.upper()} {self.asset}")
                    
                    success, order_id = self.place_order(direction, self.trading_amount)
                    
                    if success:
                        result, amount = self.wait_for_result(order_id)
                        
                        # Simpan history
                        trade_data = {
                            'timestamp': datetime.now().isoformat(),
                            'asset': self.asset,
                            'direction': direction,
                            'amount': self.trading_amount,
                            'result': result,
                            'profit_loss': amount if result == 'win' else -amount
                        }
                        self.trades_history.append(trade_data)
                else:
                    print("⏳ Menunggu signal input...")
                    time.sleep(10)  # Tunggu 10 detik untuk signal baru
                
            except KeyboardInterrupt:
                print("\n🛑 Trading dihentikan")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(10)
        
        self.is_trading = False
        print("🏁 Trading selesai")
    
    def start_trading(self):
        """
        Mulai trading
        """
        if not self.is_connected:
            print("❌ Belum terhubung")
            return False
            
        if self.is_trading:
            print("⚠️ Trading sudah berjalan")
            return False
        
        if not self.parsed_signals:
            print("❌ Tidak ada signal input!")
            return False
        
        print("🚀 MULAI SIGNAL INPUT TRADING...")
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
        Ringkasan trading
        """
        if not self.trades_history:
            print("📊 Belum ada trading")
            return
        
        wins = len([t for t in self.trades_history if t['result'] == 'win'])
        losses = len([t for t in self.trades_history if t['result'] == 'loss'])
        total_trades = len(self.trades_history)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 RINGKASAN")
        print("=" * 50)
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Profit/Loss: ${self.profit_total:.2f}")
        print("=" * 50)

def main():
    """
    Fungsi utama - SIGNAL INPUT ROBOT
    """
    print("🎯 SIGNAL INPUT TRADING ROBOT")
    print("=" * 50)
    
    email = input("📧 Email IQ Option: ").strip()
    password = input("🔐 Password: ").strip()
    
    if not email or not password:
        print("❌ Email dan password harus diisi!")
        return
    
    robot = IQTradingRobot(email, password)
    
    if not robot.connect():
        print("❌ Tidak bisa terhubung")
        return
    
    try:
        while True:
            print("\n🎯 MENU")
            print("1. Input Signal")
            print("2. Start Trading")
            print("3. Stop Trading") 
            print("4. Summary")
            print("5. Keluar")
            
            choice = input("\nPilih (1-5): ").strip()
            
            if choice == "1":
                print("Masukkan signals (CALL atau PUT, satu per baris):")
                print("Contoh: CALL atau PUT atau CALL,1 atau PUT,2")
                signals = []
                while True:
                    signal = input("Signal (enter kosong untuk selesai): ").strip()
                    if not signal:
                        break
                    signals.append(signal)
                
                robot.signal_content = '\n'.join(signals)
                robot.parse_signal_content()
                
            elif choice == "2":
                robot.start_trading()
            elif choice == "3":
                robot.stop_trading()
            elif choice == "4":
                robot.get_trading_summary()
            elif choice == "5":
                robot.stop_trading()
                robot.disconnect()
                print("👋 Selesai!")
                break
            else:
                print("❌ Pilihan salah!")
    
    except KeyboardInterrupt:
        robot.stop_trading()
        robot.disconnect()
        print("\n👋 Program dihentikan")

if __name__ == "__main__":
    main()