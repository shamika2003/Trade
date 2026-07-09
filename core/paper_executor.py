# filename: paper_executor.py

from core.logger import log
from config_core import SYMBOLS


# =====================================================
# PAPER EXECUTOR (OFFLINE SIMULATION)
# =====================================================
class PaperExecutor:


    def __init__(self, capital=1000):

        self.capital = capital

        self.positions = {}

        self.trade_history = []

        log(
            "INFO | Paper Executor initialized"
        )



    # =================================================
    # LOT CALCULATION
    # =================================================

    def _calculate_lot(self, symbol):

        return 0.01



    # =================================================
    # CHECK OPEN TRADE
    # =================================================

    def has_open_trade(self, symbol):

        return symbol in self.positions



    # =================================================
    # GET POSITION
    # =================================================

    def get_position(self, symbol):

        return self.positions.get(symbol)



    # =================================================
    # COMPATIBILITY WITH RISK MANAGER
    # =================================================

    def get_symbol_positions(self, symbol):

        if symbol in self.positions:

            return [
                self.positions[symbol]
            ]

        return []



    def get_all_positions(self):

        return list(
            self.positions.values()
        )



    # =================================================
    # OPEN PAPER TRADE
    # =================================================

    def open_trade(
            self,
            symbol,
            direction,
            lot=None
    ):

        try:


            if symbol not in SYMBOLS:

                log(
                    f"ERROR | Symbol not allowed: {symbol}"
                )

                return False



            if self.has_open_trade(symbol):

                log(
                    f"WARNING | Already open: {symbol}"
                )

                return False



            lot = (
                lot
                or
                self._calculate_lot(symbol)
            )



            position = {

                "symbol": symbol,

                "type": direction,

                "volume": lot,

                "profit": 0.0,

                "status": "OPEN"

            }



            self.positions[symbol] = position


            self.trade_history.append(
                position.copy()
            )


            log(
                f"INFO | PAPER ORDER OPEN "
                f"{symbol} {direction} lot={lot}"
            )


            return True



        except Exception as e:

            log(
                f"ERROR | Paper open failed: {e}"
            )

            return False



    # =================================================
    # UPDATE PAPER PROFIT
    # =================================================

    def update_profit(
            self,
            symbol,
            profit
    ):

        if symbol in self.positions:

            self.positions[symbol]["profit"] = (
                float(profit)
            )



    # =================================================
    # CLOSE PAPER POSITION
    # =================================================

    def close_position(self, position):

        try:


            symbol = position["symbol"]



            if symbol not in self.positions:

                return False



            closed = (
                self.positions
                .pop(symbol)
            )


            closed["status"] = "CLOSED"



            self.trade_history.append(
                closed
            )



            log(
                f"INFO | PAPER POSITION CLOSED "
                f"{symbol} "
                f"profit={closed['profit']:.2f}"
            )



            return True



        except Exception as e:


            log(
                f"ERROR | Paper close failed: {e}"
            )


            return False