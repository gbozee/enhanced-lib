import logging
import os
from dataclasses import dataclass
from typing import Literal, TypedDict


from ..calculations.utils import to_f
from .cache import ExchangeCache
from .account import Account, AccountKeys

# https://docs.python.org/3/library/logging.html#logging-levels
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.basename(__file__) + ".log",
    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
    style="{",
)


class TradeZoneDict(TypedDict):
    kind: Literal["long", "short"]
    entry: float
    stop: float
    gap: float


@dataclass
class Database:
    base_url: str
    data = {}

    def __post_init__(self):
        self.started_generation = False

    def save_position_information(self, owner: str, symbol: str, payload: dict):
        owner_data = self.data.get(owner) or {}
        symbol_position_information = owner_data.get(symbol.upper()) or {}
        symbol_position_information[AccountKeys.POSITION_INFORMATION] = payload
        owner_data[symbol.upper()] = symbol_position_information
        self.data[owner] = owner_data

    def get_position_information(self, owner: str, symbol: str):
        owner_data = self.data.get(owner) or {}
        symbol_position_information = owner_data.get(symbol.upper()) or {}
        return symbol_position_information.get(AccountKeys.POSITION_INFORMATION) or {}

    def save_future_trades(self, owner: str, symbol: str, payload: dict):
        owner_data = self.data.get(owner) or {}
        symbol_position_information = owner_data.get(symbol.upper()) or {}
        symbol_position_information[AccountKeys.FUTURE_TRADES] = payload or {}
        owner_data[symbol.upper()] = symbol_position_information
        self.data[owner] = owner_data

    def get_future_trades(self, owner: str, symbol: str):
        owner_data = self.data.get(owner) or {}
        symbol_position_information = owner_data.get(symbol.upper()) or {}
        return symbol_position_information.get(AccountKeys.FUTURE_TRADES) or {}

    def generate_future_trades(
        self, exchange: ExchangeCache, kind=None, gap=None, full=None
    ):
        self.started_generation = True
        existing = self.get_future_trades(exchange.account.owner, exchange.symbol)
        long_trades = existing.get("long") or []
        short_trades = existing.get("short") or []
        if kind == "long" or not kind:
            long_trades = exchange.config_params_for_future_trades(
                "long", True, gap=gap, full=full
            )
        if kind == "short" or not kind:
            short_trades = exchange.config_params_for_future_trades(
                "short", True, gap=gap, full=full
            )
        self.save_future_trades(
            exchange.account.owner,
            exchange.symbol,
            {
                "long": long_trades,
                "short": short_trades,
            },
        )
        self.started_generation = False

    def get_trades_for_entry(
        self, owner: str, symbol: str, payload: TradeZoneDict, places="%.1f"
    ):
        future_trades = self.get_future_trades(owner, symbol)
        if not future_trades:
            return None
        kind_entry = future_trades.get(payload["kind"]) or []
        entity = [
            x
            for x in kind_entry
            if to_f(x["entry"], places) == to_f(payload["entry"], places)
        ]
        if entity:
            return entity[0]
        return None

    def get_trade_zones(self, owner: str, symbol: str, places="%.1f"):
        future_trades = self.get_future_trades(owner, symbol)
        if not future_trades:
            return {"long": [], "short": []}
        long_entry = [
            {
                "entry": to_f(x["entry"], places),
                "stop": to_f(x["stop"], places),
                "risk_reward": x["risk_reward"],
                "risk_per_trade": x["risk_per_trade"],
                "max-size": x["trades"][0]["avg_size"] if x["trades"] else 0,
            }
            for x in future_trades.get("long") or []
        ]
        short_entry = [
            {
                "entry": to_f(x["entry"], places),
                "stop": to_f(x["stop"], places),
                "risk_reward": x["risk_reward"],
                "risk_per_trade": x["risk_per_trade"],
                "max-size": x["trades"][0]["avg_size"] if x["trades"] else 0,
            }
            for x in future_trades.get("short") or []
        ]
        return {"long": long_entry, "short": short_entry}

    async def get_initialized_exchange(
        self, owner: str, symbol: str, owner_config=None, refresh=False
    ):
        existing_position = self.get_position_information(owner, symbol)
        config = None
        if not existing_position or refresh:
            account = Account(self.base_url, owner=owner, config_owner=owner_config)
            await account.fetch_latest(symbol, True)
            position_information = account.general_config.get(
                AccountKeys.POSITION_INFORMATION
            )[symbol.upper()]
            self.save_position_information(owner, symbol, position_information)
            existing_position = self.get_position_information(owner, symbol)
            config = account.general_config[AccountKeys.CONFIG][symbol.upper()]
        account = Account(self.base_url, owner=owner, config_owner=owner_config)
        if not config:
            config = await account.fetch_config(symbol)
        self.save_position_information(owner, symbol, existing_position)
        account.general_config = {
            AccountKeys.POSITION_INFORMATION: {symbol.upper(): existing_position},
            AccountKeys.CONFIG: {symbol.upper(): config},
        }
        return ExchangeCache(account, symbol)
