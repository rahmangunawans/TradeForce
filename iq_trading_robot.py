#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dataclasses import dataclass
from typing import Optional
from iqoptionapi.stable_api import IQ_Option
import time
import threading
from datetime import datetime, timedelta
import json

@dataclass
class TradingBotConfig:
    """Dataclass untuk konfigurasi trading bot yang sesuai dengan HTML form"""
    # Account Configuration
    broker_domain: str = 'iqoption.com'
    iq_email: str = ''
    iq_password: str = ''
    account_type: str = 'demo'  # demo or real
    
    # Trading Configuration - SESUAI HTML FORM
    trading_amount: float = 1.0  # Amount ($)
    stop_win: float = 10.0       # Stop Win ($)
    stop_loss: float = 10.0      # Stop Loss ($) 
    step_martingale: int = 3     # Step Martingale
    martingale_multiple: float = 2.2  # Multiple
    
    # Asset Configuration
    asset: str = 'EURUSD'  # TIDAK ADA -OTC
    
    # Signal Configuration
    signal_type: str = 'manual_input'  # Signal Type - HANYA MANUAL INPUT
    signal_content: str = ''  # Signal content untuk manual input
    
    # Session Configuration (opsional)
    start_time: str = '09:00'
    end_time: str = '17:00'
    timezone: str = 'UTC'
    active_days: str = 'weekdays'
    
    def to_dict(self) -> dict:
        """Convert dataclass to dictionary"""
        return {
            'broker_domain': self.broker_domain,
            'iq_email': self.iq_email,
            'iq_password': self.iq_password,
            'account_type': self.account_type,
            'trading_amount': self.trading_amount,
            'stop_win': self.stop_win,
            'stop_loss': self.stop_loss,
            'step_martingale': self.step_martingale,
            'martingale_multiple': self.martingale_multiple,
            'asset': self.asset,
            'signal_type': self.signal_type,
            'signal_content': self.signal_content,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'timezone': self.timezone,
            'active_days': self.active_days
        }
    
    @classmethod
    def from_db_settings(cls, settings):
        """Create config from database BotSetting object"""
        return cls(
            broker_domain=getattr(settings, 'broker_domain', 'iqoption.com'),
            iq_email=getattr(settings, 'iq_email', ''),
            iq_password='',  # Password tidak disimpan dalam config object
            account_type=getattr(settings, 'account_type', 'demo'),
            trading_amount=getattr(settings, 'trading_amount', 1.0),
            stop_win=getattr(settings, 'stop_win', 10.0),
            stop_loss=getattr(settings, 'stop_loss', 10.0),
            step_martingale=getattr(settings, 'step_martingale', 3),
            martingale_multiple=getattr(settings, 'martingale_multiple', 2.2),
            asset=getattr(settings, 'asset', 'EURUSD'),
            signal_type=getattr(settings, 'signal_type', 'manual_input'),
            signal_content=getattr(settings, 'signal_content', ''),
            start_time=getattr(settings, 'start_time', '09:00'),
            end_time=getattr(settings, 'end_time', '17:00'),
            timezone=getattr(settings, 'timezone', 'UTC'),
            active_days=getattr(settings, 'active_days', 'weekdays')
        )

class IQTradingRobot:
    def __init__(self, email: str, password: str, config: Optional[TradingBotConfig] = None):
        """
        IQ Option Trading Robot - MENGGUNAKAN DATACLASS CONFIG
        """
        self.email = email
        self.password = password
        self.api = None
        self.balance = 0
        self.is_connected = False
        self.is_trading = False
        self.trading_thread = None
        
        # GUNAKAN DATACLASS CONFIG
        self.config = config or TradingBotConfig()
        self.config.iq_email = email  # Set email dalam config
        
        # SIGNAL INPUT SETTINGS - DARI CONFIG
        self.parsed_signals = []
        
        # Trade History
        self.trades_history = []
        self.profit_total = 0
        self.start_balance = 0
        
        print("🎯 SIGNAL INPUT TRADING ROBOT - DENGAN DATACLASS CONFIG")
        print("📊 FOKUS: Manual Signal Input SAJA")
        print("=" * 50)
    
    def parse_signal_content(self):
        """
        Parse signal input dengan 3 format:
        1. CALL atau PUT (simple)
        2. CALL,1 atau PUT,2 (dengan timeframe)
        3. 2025-08-08 16:45:00,EURUSD,CALL,1 (full format)
        """
        self.parsed_signals = []
        if not self.config.signal_content:
            print("❌ Tidak ada signal input")
            return
            
        lines = self.config.signal_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip().upper()
            if not line or line.startswith('#'):
                continue
                
            try:
                parts = line.split(',')
                direction = None
                timeframe = 1
                
                if len(parts) == 1:
                    # Format: CALL atau PUT
                    direction = parts[0].strip()
                elif len(parts) == 2:
                    # Format: CALL,1 atau PUT,2
                    direction = parts[0].strip()
                    timeframe = int(parts[1].strip())
                elif len(parts) == 4:
                    # Format: 2025-08-08 16:45:00,EURUSD,CALL,1
                    direction = parts[2].strip()  # CALL atau PUT ada di posisi ke-3
                    timeframe = int(parts[3].strip()) if parts[3].strip().isdigit() else 1
                else:
                    print(f"⚠️ Format signal salah: {line}")
                    continue
                
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
        Konfigurasi dari database settings menggunakan dataclass
        """
        if settings:
            # Update config dari database settings
            self.config = TradingBotConfig.from_db_settings(settings)
            
            # Parse signal content jika ada
            if self.config.signal_content:
                self.parse_signal_content()
            
            print(f"⚙️ Konfigurasi (dari HTML form):")
            print(f"   Amount: ${self.config.trading_amount}")
            print(f"   Stop Win: ${self.config.stop_win}")
            print(f"   Stop Loss: ${self.config.stop_loss}")
            print(f"   Step Martingale: {self.config.step_martingale}")
            print(f"   Multiple: {self.config.martingale_multiple}")
            print(f"   Signal Type: {self.config.signal_type}")
            print(f"   Asset: {self.config.asset}")
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
        Tempatkan order trading menggunakan config
        """
        if not self.api or not self.is_connected:
            print("❌ Tidak terhubung ke IQ Option")
            return False, None
            
        try:
            expiration = 1  # 1 menit
            
            print(f"📊 Trading: {direction.upper()} {self.config.asset} - ${amount}")
            
            success, order_id = self.api.buy(
                amount, self.config.asset, direction, expiration
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
                loss = self.config.trading_amount
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
        print(f"📊 Asset: {self.config.asset}")
        print(f"💰 Amount: ${self.config.trading_amount}")
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
                
                # Cek stop conditions dari config
                if self.profit_total >= self.config.stop_win:
                    print(f"🎉 STOP WIN! Profit: ${self.profit_total:.2f}")
                    break
                if self.profit_total <= -self.config.stop_loss:
                    print(f"❌ STOP LOSS! Loss: ${abs(self.profit_total):.2f}")
                    break
                
                # AMBIL DAN EKSEKUSI SIGNAL
                signal = self.get_next_signal()
                
                if signal:
                    direction = signal['direction'].lower()
                    print(f"🎯 TRADING: {direction.upper()} {self.config.asset}")
                    
                    success, order_id = self.place_order(direction, self.config.trading_amount)
                    
                    if success:
                        result, amount = self.wait_for_result(order_id)
                        
                        # Simpan history
                        trade_data = {
                            'timestamp': datetime.now().isoformat(),
                            'asset': self.config.asset,
                            'direction': direction,
                            'amount': self.config.trading_amount,
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
                
                robot.config.signal_content = '\n'.join(signals)
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