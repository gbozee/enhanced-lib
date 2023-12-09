import copy
from typing import List
from tools.client import TradeClient, loop_helper
from .position_control import PositionControl
from .future_config import FutureInstance, Config, use_multi_process
import asyncio


class Exchange:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.long_position = PositionControl(
            avg_entry=self.position["long"]["entryPrice"],
            avg_size=abs(self.position["long"]["positionAmt"]),
            kind="long",
        )
        self.short_position = PositionControl(
            avg_entry=self.position["short"]["entryPrice"],
            avg_size=abs(self.position["short"]["positionAmt"]),
            kind="short",
        )

    def get_balance(self, asset: str):
        found = [x for x in self.account_balance if x["asset"] == asset]
        if found:
            return float(found[0]["balance"])

    @property
    def usdt_balance(self):
        return self.get_balance("USDT")

    @property
    def bnb_balance(self):
        return self.get_balance("BNB")


class ExchangeControl:
    future_trader: FutureInstance

    def __init__(self, exchanges: List[Exchange], config: Config) -> None:
        self.future_trader = FutureInstance(config)
        self.exchanges = exchanges

    def build_entries(self, kind="long", support=None, resistance=None):
        old_support = self.future_trader.config.support
        old_resistance = self.future_trader.config.resistance
        if support and resistance:
            self.future_trader.config.support = support
            self.future_trader.config.resistance = resistance
        results = use_multi_process(
            self.future_trader, _kind=kind, _inner_kind=kind, no_of_cpu=4
        )
        if support and resistance:
            self.future_trader.config.support = old_support
            self.future_trader.config.resistance = old_resistance
        return results


class BotControl:
    symbol = "BTCUSDT"
    control: ExchangeControl

    def __init__(
        self,
        base_url: str,
        config: Config = None,
        trade_accounts: List[str] = None,
        deposit_accounts: List[str] = None,
    ):
        self.client = TradeClient(base_url=base_url)
        self.trade_accounts = trade_accounts or []
        self.deposit_accounts = deposit_accounts or []
        self.config = config or Config()

    async def client_helper(self, method: str, params):
        return await loop_helper(lambda: getattr(self.client, method)(params))

    async def get_exchange_info(self):
        accounts = self.trade_accounts + self.deposit_accounts
        print("accounts", accounts)
        tasks = [
            self.client_helper(
                "get_exchange_info",
                {
                    "owner": x,
                    "symbol": self.symbol,
                    "future_only": x not in self.deposit_accounts,
                },
            )
            for x in accounts
        ]
        return await asyncio.gather(*tasks)

    async def initialize_exchanges(self):
        results = await self.get_exchange_info()
        exchanges = [Exchange(**x["future"][self.symbol.lower()]) for x in results]
        self.control = ExchangeControl(exchanges=exchanges, config=self.config)
