import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    IQ_Option = None
    logger.warning("iqoptionapi not available")


@dataclass
class TradingBotConfig:
    iq_email: str = ""
    iq_password: str = ""
    account_type: str = "PRACTICE"
    trading_amount: float = 1.0
    stop_win: float = 10.0
    stop_loss: float = 10.0
    step_martingale: int = 3
    martingale_multiple: float = 2.2
    signal_type: str = "signal_input"
    signal_content: str = ""
    asset: str = "EURUSD-OTC"
    duration: int = 1

    @classmethod
    def from_db_settings(cls, settings):
        return cls(
            iq_email=settings.iq_email,
            iq_password="",
            account_type=settings.account_type.upper() if settings.account_type else "PRACTICE",
            trading_amount=settings.trading_amount or 1.0,
            stop_win=settings.stop_win or 10.0,
            stop_loss=settings.stop_loss or 10.0,
            step_martingale=settings.step_martingale or 3,
            martingale_multiple=settings.martingale_multiple or 2.2,
            signal_type=settings.signal_type or "signal_input",
            signal_content=settings.signal_content or "",
        )


class IQTradingRobot:
    def __init__(self, email: str, password: str, config: Optional[TradingBotConfig] = None):
        self.email = email
        self.password = password
        self.config = config or TradingBotConfig(iq_email=email, iq_password=password)
        self.api = None
        self.is_trading = False
        self.balance = 0.0
        self.trades_history = []
        self.profit_total = 0.0
        self.consecutive_losses = 0
        self._trade_thread = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        if IQ_Option is None:
            logger.error("IQ Option API not available")
            return False
        try:
            self.api = IQ_Option(self.email, self.password)
            check, reason = self.api.connect()
            if check:
                logger.info("Connected to IQ Option successfully")
                return True
            else:
                logger.error(f"Connection failed: {reason}")
                return False
        except Exception as e:
            logger.error(f"Connection exception: {e}")
            return False

    def disconnect(self):
        try:
            if self.api:
                self.api.close()
                self.api = None
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    def check_connect(self) -> bool:
        try:
            if self.api:
                return self.api.check_connect()
            return False
        except Exception:
            return False

    def change_balance(self, mode: str):
        try:
            if self.api:
                self.api.change_balance(mode)
                time.sleep(1)
        except Exception as e:
            logger.error(f"Change balance error: {e}")

    def get_balance(self) -> float:
        try:
            if self.api:
                balance = self.api.get_balance()
                self.balance = balance if balance else 0.0
                return self.balance
        except Exception as e:
            logger.error(f"Get balance error: {e}")
        return 0.0

    def buy(self, amount: float, asset: str, direction: str, duration: int):
        try:
            if self.api:
                status, order_id = self.api.buy(amount, asset, direction, duration)
                return status, order_id
        except Exception as e:
            logger.error(f"Buy error: {e}")
        return False, None

    def check_win(self, order_id) -> float:
        try:
            if self.api and order_id:
                result = self.api.check_win_v3(order_id)
                return result
        except Exception as e:
            logger.error(f"Check win error: {e}")
        return 0.0

    def start_trading(self) -> bool:
        if self.is_trading:
            return False
        self._stop_event.clear()
        self.is_trading = True
        self._trade_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self._trade_thread.start()
        logger.info("Trading bot started")
        return True

    def stop_trading(self):
        self.is_trading = False
        self._stop_event.set()
        logger.info("Trading bot stopped")

    def _trading_loop(self):
        cfg = self.config
        current_amount = cfg.trading_amount
        martingale_step = 0

        while self.is_trading and not self._stop_event.is_set():
            try:
                if not self.check_connect():
                    logger.warning("Lost connection, attempting reconnect...")
                    self.connect()
                    time.sleep(5)
                    continue

                signal = self._get_signal()
                if not signal:
                    time.sleep(2)
                    continue

                direction, asset, duration = signal

                if self.profit_total >= cfg.stop_win:
                    logger.info(f"Stop Win reached: {self.profit_total}")
                    self.is_trading = False
                    break

                if self.profit_total <= -cfg.stop_loss:
                    logger.info(f"Stop Loss reached: {self.profit_total}")
                    self.is_trading = False
                    break

                status, order_id = self.buy(current_amount, asset, direction, duration)
                if not status:
                    logger.warning("Buy failed, retrying...")
                    time.sleep(2)
                    continue

                time.sleep(duration * 60 + 2)

                win_amount = self.check_win(order_id)
                trade_result = {
                    'order_id': order_id,
                    'asset': asset,
                    'direction': direction,
                    'amount': current_amount,
                    'profit': win_amount,
                }
                self.trades_history.append(trade_result)
                self.profit_total += win_amount

                if win_amount > 0:
                    logger.info(f"WIN: +{win_amount}")
                    current_amount = cfg.trading_amount
                    martingale_step = 0
                    self.consecutive_losses = 0
                else:
                    logger.info(f"LOSS: {win_amount}")
                    self.consecutive_losses += 1
                    if martingale_step < cfg.step_martingale:
                        martingale_step += 1
                        current_amount = round(current_amount * cfg.martingale_multiple, 2)
                    else:
                        current_amount = cfg.trading_amount
                        martingale_step = 0
                        self.consecutive_losses = 0

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(5)

        self.is_trading = False

    def get_all_open_time(self) -> dict:
        try:
            if self.api:
                return self.api.get_all_open_time()
        except Exception as e:
            logger.error(f"get_all_open_time error: {e}")
        return {}

    def _get_signal(self):
        cfg = self.config
        signal_type = cfg.signal_type
        asset = getattr(cfg, 'asset', 'EURUSD-OTC')
        duration = getattr(cfg, 'duration', 1)

        if signal_type == "signal_input":
            content = (cfg.signal_content or "").strip()
            if not content:
                return None
            parts = [p.strip() for p in content.split(",")]
            if len(parts) >= 2:
                direction = parts[0].upper()
                try:
                    duration = int(parts[1])
                except ValueError:
                    duration = 1
                if len(parts) >= 3:
                    asset = parts[2].upper()
                return (direction, asset, duration)
            return None

        return None
