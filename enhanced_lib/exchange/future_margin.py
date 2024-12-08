from dataclasses import dataclass
from typing import Literal, TypedDict
from .client import TradeClient
from functools import cached_property


@dataclass
class FutureMargin:
    owner: str
    type: Literal["coin", "usdt"]
    base_url: str

    @cached_property
    def client(self):
        return TradeClient(self.base_url)

    def make_api_call(self, symbol, method, **kwargs):
        return self.client.api_call(
            f"api/{self.owner}/remote-actions",
            "POST",
            {
                "action": "",
                "symbol": symbol,
                "name": "client_call",
                "params": {
                    "args": [method],
                    "kwargs": kwargs,
                },
            },
        )

    def make_call(self, symbol, method, **kwargs):
        return self.client.api_call(
            f"api/{self.owner}/remote-actions",
            "POST",
            {
                "action": "",
                "symbol": symbol,
                "name": method,
                "params": {
                    "args": [],
                    "kwargs": kwargs,
                },
            },
        )

    def make_base_call(self, symbol, method, owner=None, **kwargs):
        _owner = owner or self.owner
        return self.client.api_call(
            f"api/{owner}/remote-actions",
            "POST",
            {
                "action": method,
                "symbol": symbol,
                "name": method,
                "params": {
                    "args": [],
                    "kwargs": kwargs,
                },
            },
        )

    def get_balance(self, symbol: str) -> float:
        result = self.make_call(symbol, "get_account_balance")["data"]
        return result

    def get_position(
        self, symbol: str, kind: Literal["long", "short"]
    ) -> "PositionDetail":
        result = self.make_call(symbol, "get_position", skip=True)["data"]
        return result[kind]

    def transfer_balance(self, symbol: str, amount: float, _from: str, base_asset=None):
        asset = "USDT" if self.type == "usdt" else base_asset
        result = self.make_base_call(
            symbol,
            "cross_account_transfer",
            owner="main_account",
            **{
                "from": {"owner": _from, "wallet": "spot"},
                "to": {"owner": self.owner, "wallet": "future"},
                "asset": asset,
                "amount": amount,
            },
        )
        return result["data"]

    def withdraw(self, symbol: str, amount: float, to: str, base_asset=None):
        asset = "USDT" if self.type == "usdt" else base_asset
        result = self.make_base_call(
            symbol,
            "cross_account_transfer",
            owner="main_account",
            **{
                "to": {"owner": to, "wallet": "spot"},
                "from": {"owner": self.owner, "wallet": "future"},
                "asset": asset,
                "amount": amount,
            },
        )
        return result["data"]


class PositionDetail(TypedDict):
    symbol: str
    positionAmt: float
    entryPrice: float
    markPrice: float
    unRealizedProfit: float
    liquidationPrice: float
    leverage: int
    maxQty: float
    marginType: Literal["cross", "isolated"]
    isolatedMargin: float
    isAutoAddMargin: str
    positionSide: Literal["LONG", "SHORT"]
    notionalValue: float
    isolatedWallet: float
    updateTime: int
    breakEvenPrice: str
    maxNotionalValue: float
