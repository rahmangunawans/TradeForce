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
    asset: str = ''  # TIDAK ADA -OTC
    
    # Signal Configuration
    signal_type: str = 'manual_input'  # Signal Type - HANYA MANUAL INPUT
    signal_content: str = ''  # Signal content untuk manual input
    
    # Session Configuration (opsional)
    start_time: str = '09:00'
    end_time: str = '17:00'
    timezone: str = 'UTC'
    user_timezone: str = 'auto'  # User's timezone for signal timing
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
            'user_timezone': self.user_timezone,
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
            asset=getattr(settings, 'asset', ''),
            signal_type=getattr(settings, 'signal_type', 'manual_input'),
            signal_content=getattr(settings, 'signal_content', ''),  # Tidak ada default signal
            start_time=getattr(settings, 'start_time', '09:00'),
            end_time=getattr(settings, 'end_time', '17:00'),
            timezone=getattr(settings, 'timezone', 'UTC'),
            user_timezone=getattr(settings, 'user_timezone', 'auto'),
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
        
        # Martingale Tracking
        self.current_martingale_step = 0
        self.consecutive_losses = 0
        self.current_amount = self.config.trading_amount
        
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
                
                asset = None  # Asset dari signal, atau gunakan default config
                
                if len(parts) == 1:
                    # Format: CALL atau PUT
                    direction = parts[0].strip()
                elif len(parts) == 2:
                    # Format: CALL,1 atau PUT,2
                    direction = parts[0].strip()
                    timeframe = int(parts[1].strip())
                elif len(parts) == 4:
                    # Format: 2025-08-08 16:45:00,EURUSD,CALL,1
                    timestamp_str = parts[0].strip()  # Waktu eksekusi
                    asset = parts[1].strip().upper()  # Asset dari signal
                    direction = parts[2].strip()  # CALL atau PUT ada di posisi ke-3
                    timeframe = int(parts[3].strip()) if parts[3].strip().isdigit() else 1
                    print(f"🎯 Signal dengan asset: {asset} pada {timestamp_str}")
                    
                    # Parse timestamp untuk eksekusi terjadwal (assume local timezone)
                    from datetime import datetime
                    try:
                        # Parse timestamp dan konversi timezone
                        from datetime import datetime, timedelta
                        execution_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        current_time = datetime.now()
                        
                        # Get user timezone setting from config
                        user_timezone = getattr(self.config, 'user_timezone', 'auto')
                        
                        # Konversi berdasarkan setting user timezone
                        if user_timezone == 'auto':
                            # Auto-detect timezone user berdasarkan selisih waktu
                            raw_diff = execution_time - current_time
                            hours_diff = raw_diff.total_seconds() / 3600
                            
                            # Deteksi timezone berdasarkan pola selisih waktu
                            timezone_offset = 0
                            timezone_name = "UTC"
                            
                            # Deteksi timezone umum (range ±1 jam untuk toleransi)
                            if 6 <= abs(hours_diff) <= 8:
                                if hours_diff > 0:
                                    timezone_offset = 7  # UTC+7 (Indonesia, Thailand, Vietnam)
                                    timezone_name = "UTC+7 (Indonesia/Thailand/Vietnam)"
                                else:
                                    timezone_offset = -7  # User di UTC-7 tapi tidak umum
                                    timezone_name = "UTC-7"
                            elif 4 <= abs(hours_diff) <= 6:
                                if hours_diff > 0:
                                    timezone_offset = 5  # UTC+5 (Pakistan, Uzbekistan)
                                    timezone_name = "UTC+5 (Pakistan/Uzbekistan)"
                                else:
                                    timezone_offset = -5  # UTC-5 (Eastern US)
                                    timezone_name = "UTC-5 (Eastern US)"
                            elif 2 <= abs(hours_diff) <= 4:
                                if hours_diff > 0:
                                    timezone_offset = 3  # UTC+3 (Saudi Arabia, Russia)
                                    timezone_name = "UTC+3 (Saudi Arabia/Russia)"
                                else:
                                    timezone_offset = -3  # UTC-3 (Brazil)
                                    timezone_name = "UTC-3 (Brazil)"
                            elif 7 <= abs(hours_diff) <= 9:
                                if hours_diff > 0:
                                    timezone_offset = 8  # UTC+8 (China, Malaysia, Singapore)
                                    timezone_name = "UTC+8 (China/Malaysia/Singapore)"
                                else:
                                    timezone_offset = -8  # UTC-8 (Pacific US)
                                    timezone_name = "UTC-8 (Pacific US)"
                            
                            # Konversi ke UTC jika terdeteksi timezone
                            if timezone_offset != 0:
                                if hours_diff > 0:
                                    execution_time = execution_time - timedelta(hours=timezone_offset)
                                else:
                                    execution_time = execution_time + timedelta(hours=abs(timezone_offset))
                                print(f"🌏 Auto-detected & converted: {timezone_name} → UTC")
                        else:
                            # Manual timezone setting dari user
                            try:
                                timezone_offset = int(user_timezone)
                                execution_time = execution_time - timedelta(hours=timezone_offset)
                                print(f"🌏 Manual timezone converted: UTC{user_timezone:+d} → UTC")
                            except (ValueError, TypeError):
                                print(f"⚠️ Invalid timezone setting: {user_timezone}, using auto-detect")
                                # Fallback ke auto-detect jika setting tidak valid
                        
                        time_diff = execution_time - current_time
                        
                        print(f"🕐 Timestamp analysis:")
                        print(f"   Signal time (original): {datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')}")
                        print(f"   Signal time (UTC): {execution_time}")
                        print(f"   Current time (UTC): {current_time}")
                        print(f"   Time difference: {time_diff.total_seconds():.0f} seconds")
                        
                        # Jika signal sudah lewat (lebih dari 1 menit), eksekusi langsung
                        if time_diff.total_seconds() < -60:  # Sudah lewat lebih dari 1 menit
                            print(f"⚡ EKSEKUSI LANGSUNG - Signal sudah lewat!")
                            execution_time = None  # Set ke None agar eksekusi langsung
                        # Jika signal lebih dari 2 jam di masa depan, eksekusi langsung juga
                        elif time_diff.total_seconds() > 7200:  # Lebih dari 2 jam
                            print(f"⚡ EKSEKUSI LANGSUNG - Signal terlalu jauh di masa depan!")
                            execution_time = None  # Set ke None agar eksekusi langsung
                        else:
                            # Signal masih valid untuk eksekusi terjadwal
                            print(f"⏰ MENUNGGU EKSEKUSI TEPAT WAKTU: {execution_time}")
                            print(f"   Waktu tunggu: {time_diff.total_seconds():.0f} detik")
                    except:
                        execution_time = None
                        print(f"⚠️ Format timestamp salah: {timestamp_str}")
                else:
                    print(f"⚠️ Format signal salah: {line}")
                    continue
                
                if direction not in ['CALL', 'PUT']:
                    print(f"⚠️ Signal salah: {line} (harus CALL atau PUT)")
                    continue
                
                signal = {
                    'asset': asset,  # Asset dari signal (bisa None jika format simple)
                    'direction': direction,
                    'timeframe': timeframe,
                    'execution_time': locals().get('execution_time', None),  # Waktu eksekusi terjadwal
                    'processed': False
                }
                self.parsed_signals.append(signal)
                print(f"✅ Signal {line_num}: {direction} {timeframe} menit - SIAP")
                    
            except Exception as e:
                print(f"❌ Error parsing line {line_num}: {line} - {e}")
                
        print(f"📊 Total {len(self.parsed_signals)} signals siap untuk trading")
        
        # Tampilkan jadwal eksekusi jika ada
        scheduled_signals = [s for s in self.parsed_signals if s.get('execution_time')]
        if scheduled_signals:
            print("⏰ JADWAL EKSEKUSI:")
            for i, signal in enumerate(scheduled_signals, 1):
                print(f"   {i}. {signal['execution_time']} - {signal['direction']} {signal.get('asset', self.config.asset)}")
        else:
            print("⚡ Semua signal akan dieksekusi langsung")
    
    def get_next_signal(self):
        """
        Ambil signal berikutnya yang belum diproses dan sudah waktunya eksekusi
        """
        from datetime import datetime
        current_time = datetime.now()
        
        for signal in self.parsed_signals:
            if not signal['processed']:
                # Cek apakah ada waktu eksekusi terjadwal
                if signal.get('execution_time'):
                    # Jika signal timestamp sudah lewat lebih dari 1 jam, eksekusi langsung
                    time_diff = current_time - signal['execution_time']
                    if time_diff.total_seconds() > 0:  # Signal sudah lewat
                        signal['processed'] = True
                        print(f"⏰ SIGNAL TIMESTAMP SUDAH LEWAT - EKSEKUSI LANGSUNG: {signal['direction']}")
                        if signal.get('asset'):
                            print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {signal['asset']}")
                        else:
                            print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {self.config.asset}")
                        return signal
                    elif current_time >= signal['execution_time']:
                        signal['processed'] = True
                        print(f"⏰ WAKTU EKSEKUSI TIBA: {signal['direction']} pada {signal['execution_time']}")
                        if signal.get('asset'):
                            print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {signal['asset']}")
                        else:
                            print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {self.config.asset}")
                        return signal
                    else:
                        # Tunggu eksekusi normal - TIDAK ADA BATAS WAKTU TUNGGU
                        time_left = signal['execution_time'] - current_time
                        hours = int(time_left.total_seconds() // 3600)
                        minutes = int((time_left.total_seconds() % 3600) // 60)
                        seconds = int(time_left.total_seconds() % 60)
                        print(f"⏳ Menunggu eksekusi {signal['direction']} dalam {hours:02d}:{minutes:02d}:{seconds:02d}")
                        continue
                else:
                    # Signal tanpa timestamp, eksekusi langsung
                    signal['processed'] = True
                    if signal.get('asset'):
                        print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {signal['asset']}")
                    else:
                        print(f"🎯 EKSEKUSI SIGNAL: {signal['direction']} - Asset: {self.config.asset}")
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
            
            # Gunakan asset dari signal SAJA, tanpa fallback
            signal_asset = getattr(self, '_current_signal_asset', None)
            
            if not signal_asset:
                print("❌ ERROR: Signal tidak memiliki asset! Format yang benar: YYYY-MM-DD HH:MM:SS,ASSET,CALL/PUT,TIMEFRAME")
                return False, None
                
            base_asset = signal_asset
            
            print(f"📊 Trading: {direction.upper()} {base_asset} - ${amount}")
            
            # Coba asset dari signal terlebih dahulu, tanpa fallback otomatis ke EURUSD
            asset_variants = []
            
            # Jika signal memiliki asset spesifik, gunakan itu saja
            if signal_asset:
                # STRICT MODE: Gunakan HANYA asset yang ada di signal
                if signal_asset.endswith('-OTC'):
                    asset_variants = [signal_asset]  # Sudah ada OTC, gunakan as-is
                    print(f"🎯 Signal menyebutkan OTC: {signal_asset}")
                else:
                    # PILIHAN: Apakah mau strict atau dengan fallback OTC?
                    # STRICT: Hanya gunakan asset persis dari signal
                    # asset_variants = [signal_asset]
                    # FALLBACK: Coba asset asli dulu, kalau gagal coba OTC
                    asset_variants = [
                        signal_asset,
                        f"{signal_asset}-OTC"
                    ]
                    print(f"🎯 Signal: {signal_asset} (akan coba regular dulu, jika gagal akan coba {signal_asset}-OTC)")
                print(f"📝 Asset dari signal content: {signal_asset}")
            else:
                # Error jika tidak ada asset
                print("❌ ERROR: Signal harus memiliki asset!")
                return False, None
            
            success = False
            order_id = None
            
            # Skip checking status pasar untuk menghindari error
            print("📅 Melanjutkan tanpa cek status pasar")
            
            for asset in asset_variants:
                try:
                    print(f"🔍 Mencoba asset: {asset}")
                    
                    # Skip individual asset status check untuk menghindari error
                    print(f"📊 Memproses asset: {asset}")
                    
                    success, order_id = self.api.buy(amount, asset, direction, expiration)
                    print(f"🔄 Hasil API buy: success={success}, order_id={order_id}")
                    
                    if success and order_id:
                        if asset != signal_asset:
                            print(f"✅ Order berhasil! Asset yang digunakan: {asset} (signal asli: {signal_asset})")
                            print(f"ℹ️  Alasan: {signal_asset} tidak tersedia, menggunakan {asset}")
                        else:
                            print(f"✅ Order berhasil! Asset: {asset}, ID: {order_id}")
                        # Update config dengan asset yang berhasil
                        self.config.asset = asset
                        return True, order_id
                    else:
                        print(f"❌ Gagal dengan asset: {asset} - success: {success}, order_id: {order_id}")
                        
                except Exception as asset_error:
                    print(f"❌ Error dengan asset {asset}: {asset_error}")
                    import traceback
                    print(f"📋 Traceback: {traceback.format_exc()}")
                    continue
            
            print("❌ Semua variasi asset gagal")
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
            elif result == 0:
                # Draw/Tie - no profit, no loss, refund the amount
                print(f"🤝 DRAW! Refund: ${self.current_amount:.2f} | Total: ${self.profit_total:.2f}")
                return "draw", 0
            else:
                loss = self.current_amount
                self.profit_total -= loss
                print(f"😢 LOSS! Loss: ${loss:.2f} | Total: ${self.profit_total:.2f}")
                return "loss", loss
                
        except Exception as e:
            print(f"❌ Error hasil: {e}")
            return "error", 0
    
    def reset_martingale(self):
        """Reset Martingale setelah win"""
        self.current_martingale_step = 0
        self.consecutive_losses = 0
        self.current_amount = self.config.trading_amount
        print(f"🔄 Martingale reset - Amount: ${self.current_amount:.2f}")

    def apply_martingale(self):
        """Apply logika Martingale setelah loss"""
        if self.current_martingale_step < self.config.step_martingale:
            self.current_martingale_step += 1
            self.consecutive_losses += 1
            self.current_amount = self.config.trading_amount * (self.config.martingale_multiple ** self.current_martingale_step)
            print(f"💸 MARTINGALE Step {self.current_martingale_step}/{self.config.step_martingale}")
            print(f"   Next Amount: ${self.current_amount:.2f} (x{self.config.martingale_multiple ** self.current_martingale_step:.1f})")
            return True
        else:
            print(f"🚫 MARTINGALE MAX STEP REACHED ({self.config.step_martingale})")
            self.reset_martingale()
            return False

    def trading_loop(self):
        """
        TRADING LOOP DENGAN MARTINGALE - SIGNAL INPUT
        """
        print("🚀 MULAI TRADING - SIGNAL INPUT WITH MARTINGALE")
        print(f"💰 Initial Amount: ${self.config.trading_amount}")
        print(f"🎯 Martingale Steps: {self.config.step_martingale}")
        print(f"📈 Martingale Multiple: {self.config.martingale_multiple}x")
        print(f"📊 Signals: {len(self.parsed_signals)} siap untuk trading")
        print("=" * 50)
        
        self.start_balance = self.balance
        self.reset_martingale()  # Initialize Martingale
        
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
                    
                    # Set asset dari signal jika ada
                    if signal.get('asset'):
                        self._current_signal_asset = signal['asset']
                        print(f"🎯 TRADING: {direction.upper()} {signal['asset']} (dari signal)")
                    else:
                        print("❌ ERROR: Signal tidak memiliki asset - trading dihentikan")
                        break
                    
                    # Gunakan current_amount untuk Martingale
                    print(f"💰 Trading Amount: ${self.current_amount:.2f} (Step: {self.current_martingale_step})")
                    success, order_id = self.place_order(direction, self.current_amount)
                    
                    if success:
                        result, amount = self.wait_for_result(order_id)
                        
                        # Proses hasil trading dengan Martingale
                        if result == "win":
                            print("🎉 WIN - Reset Martingale")
                            self.reset_martingale()
                        elif result == "loss":
                            print("😢 LOSS - Cek Martingale")
                            martingale_continues = self.apply_martingale()
                            if not martingale_continues:
                                print("⚠️ Martingale selesai - reset ke amount awal")
                        elif result == "draw":
                            print("🤝 DRAW - Amount tidak berubah (refund)")
                            # Untuk draw, tidak reset atau apply martingale
                        
                        # Simpan history dengan asset yang benar
                        actual_asset = self._current_signal_asset or self.config.asset
                        trade_data = {
                            'timestamp': datetime.now().isoformat(),
                            'asset': actual_asset,
                            'direction': direction,
                            'amount': self.current_amount,
                            'result': result,
                            'profit_loss': amount if result == 'win' else (-amount if result == 'loss' else 0),
                            'martingale_step': self.current_martingale_step
                        }
                        self.trades_history.append(trade_data)
                else:
                    # Cek apakah ada signal yang menunggu waktu eksekusi
                    waiting_signals = [s for s in self.parsed_signals if not s['processed'] and s.get('execution_time')]
                    if waiting_signals:
                        next_signal = min(waiting_signals, key=lambda x: x['execution_time'])
                        time_left = next_signal['execution_time'] - datetime.now()
                        if time_left.total_seconds() > 0:
                            hours = int(time_left.total_seconds() // 3600)
                            minutes = int((time_left.total_seconds() % 3600) // 60)
                            seconds = int(time_left.total_seconds() % 60)
                            print(f"⏳ Menunggu signal {next_signal['direction']} dalam {hours:02d}:{minutes:02d}:{seconds:02d}")
                            time.sleep(min(30, time_left.total_seconds()))  # Tunggu maksimal 30 detik
                        else:
                            time.sleep(1)  # Cek lagi dalam 1 detik
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
        
        # Parse signal content jika ada
        if self.config.signal_content:
            self.parse_signal_content()
        
        # Jika tidak ada parsed signals, tampilkan pesan error
        if not self.parsed_signals:
            print("❌ TIDAK ADA SIGNAL INPUT YANG VALID!")
            print("📋 Format yang diperlukan: YYYY-MM-DD HH:MM:SS,ASSET,CALL/PUT,TIMEFRAME")
            print("📋 Contoh: 2025-08-09 16:30:00,EURUSD,CALL,1")
            return False
        
        print("🚀 MULAI SIGNAL INPUT TRADING...")
        print(f"📊 Total {len(self.parsed_signals)} signals siap untuk trading")
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
        draws = len([t for t in self.trades_history if t['result'] == 'draw'])
        total_trades = len(self.trades_history)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 RINGKASAN")
        print("=" * 50)
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Draws: {draws}")
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