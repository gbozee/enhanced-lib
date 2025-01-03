from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, TypedDict, Literal
import requests
import asyncio
from enhanced_lib.calculations.utils import create_trader

ROOT = "your_root_value_here"  # Replace with the actual value


async def loop_helper(callback):
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, callback)
    return await future


class TradeActionParamType(TypedDict):
    symbol: str
    action: Literal["get", "save"]
    owner: str
    trades: Dict[str, Any]


class BorrowRepayParamType(TypedDict):
    symbol: str
    base: float
    quote: str
    owner: str


class SyncBalanceType(TypedDict):
    owner: str
    symbol: str
    base: float
    quote: float
    to: Literal["spot", "margin"]


class NewTradeType(TypedDict):
    symbol: str
    owner: str
    amount: float
    price: float
    increase: float
    diff: float
    decimal_places: str


class ALLExchangeParamType(TypedDict):
    symbol: str
    exchanges: List[str]
    future_only: bool
    save: bool


class CandleStickParamType(TypedDict):
    symbol: str
    interval: Literal[
        "weekly",
        "daily",
        "monthly",
        "hours_4",
        "hours_1",
        "minutes_15",
        "hours_12",
        "minutes_3",
        "minutes_1",
    ]
    count: int
    raw: bool


class DepositParamType(TypedDict):
    owner: str
    amount: float


class WithdrawParamType(TypedDict):
    symbol: str
    amount: float
    invoice: str
    owner: str


class TradeSignalType(TypedDict):
    symbol: str
    kind: str
    cancel: bool
    # orders: typing.list[typing.Dict(str, typing.Any)]
    orders: List[Dict[str, Any]]
    sub_account: List[str]


class TradeUpdatePriceType(TypedDict):
    symbol: str
    kind: str
    # orders: typing.list[typing.Dict(str, typing.Any)]
    orders: List[Dict[str, Any]]
    sub_account: List[str]


class PlaceMarginType(TypedDict):
    symbol: str
    size: float
    entry: float
    kind: str
    stop: float
    cancel: bool
    owner: str
    mode: Literal["isolated", "cross"]


class UpdateMarginType(TypedDict):
    symbol: str
    size: float
    take_profit: float
    kind: str
    owner: str


class AccountOrdersType(TypedDict):
    owner: str
    symbol: str


class CreateOrdersType(TypedDict):
    config: Any
    symbol: str


class CreateSingleOrdersType(TypedDict):
    symbol: str


class PlaceFutureType(TypedDict):
    symbol: str
    kind: str


class UpdateProtectProfitType(TypedDict):
    symbol: str
    owner: str


class ClosePosionType(TypedDict):
    symbol: str
    kind: str
    owner: str


class SpotProfileType(TypedDict):
    symbol: str
    spot_symbol: str
    owner: str


class ProfileConfig(TypedDict):
    price_places: str
    support: float
    resistance: float
    decimal_places: str
    min_size: float
    risk_per_trade: float


class CreateSpotProfileType(TypedDict):
    owner: str
    symbol: str
    profile: ProfileConfig


class SpotSymbolType(TypedDict):
    coin: str
    owner: str


class OpenOrderType(TypedDict):
    symbol: str
    owner: str


class NotifyType(TypedDict):
    message: str
    owner: str


class RunProfileType(TypedDict):
    symbol: str
    owner: str
    profile_id: Any
    start: str
    old_mode: str
    new_future: str


class JobType(TypedDict):
    job_id: str


class SymbolType(TypedDict):
    owner: str
    symbol: str


class StopTradeType(TypedDict):
    owner: str
    symbol: str
    order: Any


class UpdateOrderType(TypedDict):
    owner: str
    symbol: str
    action: bool


class UpdateConfigType(TypedDict):
    owner: str
    confg: Any


class MarketType(TypedDict):
    owner: str


class StopLossType:
    id: int
    entryPrice: float
    quantity: float
    symbol: str
    kind: str
    pip: float
    stopPrice: float
    takeProfitPrice: float
    percent: float
    risk: float


class TradeType:
    symbol: str
    entry: float
    quantity: float
    stop: float
    kind: str
    isMarketTrade: bool


class PositionType:
    entry: float
    kind: str
    quantity: float
    symbol: str


class BulkTradeType:
    owner: str
    symbol: str
    trades: List[Any]


class GetExchangeInfoType(TypedDict):
    owner: str
    symbol: str
    future_only: bool
    save: bool


class UpdateTakeProfitNewType:
    owner: str
    symbol: str
    kind: str
    price: float


class UpdateStopLossNewType:
    owner: str
    symbol: str
    kind: str
    price: float


class CloseOpenOrdersType:
    owner: str
    symbol: str
    order_ids: List[str]


class IncreasePositionType:
    owner: str
    symbol: str
    orders: List[Dict[str, Any]]


class SwingInfo:
    timeFrame: str
    symbol: str
    count: float
    kind: str


class AnalyzePositionType:
    owner: str
    symbol: str
    kind: str


class SendMessageType:
    title: str
    body: str
    userId: float


class Constants:
    """
    The list of api calls that can be used with trade clients.
    """

    GET_SPOT_VALUE = "get_spot_config"
    UPDATE_TAKE_PROFIT_NEW = "update_take_profit_new"
    EXCHANGE_INFO = "get_exchange_info"
    SAVE_SPOT_PROFILE = "create_spot_profile"
    GET_CANDLESTICKS = "get_candlesticks"
    PLACE_SIGNAL_ORDERS = "place_signal_orders"


class TradeClient:
    def __init__(self, base_url="") -> None:
        self.base_url = base_url

    def api_call(self, path: str, method: str, params: dict):
        url = f"{self.base_url}/{path}"
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=params)
        else:
            raise ValueError(f"Method {method} not supported")
        if response.status_code < 400:
            result = response.json()
            return result
        return None

    def get_current_position(self, account: str, symbol: str):
        result = self.api_call(
            "get_current_position", "GET", {"account": account, "symbol": symbol}
        )
        return result

    def bulk_trades(self, params: BulkTradeType):
        result = self.api_call(
            "bulk-margin-future-orders",
            "POST",
            {
                "symbol": params.symbol,
                "future_orders": params.trades,
                "margin_orders": [],
            },
            f"/ft{params.owners}",
        )
        return result

    def increase_position(self, params: PositionType):
        result = self.api_call(
            "simple-order", "POST", {**params, "side": "buy" if params.kind else "sell"}
        )
        openTrade = {
            "symbol": result["symbol"],
            "entryPrice": result["entryPrice"],
            "kind": params.kind,
            "quantity": abs(result["positionAmt"]),
        }
        return openTrade

    def get_swing_info(self, params: SwingInfo):
        _count = 500
        if "minute" in params.timeFrame:
            _count = 300
        result = self.api_call("swing-high-low", "POST", {**params, "count": _count})
        return result

    def load_initial_data(self, params):
        result = {
            "pip": 0,
            "balance": 0,
            "places": 2,
            "position": [],
            "stop_orders": [],
        }
        return {
            "pip": result["pip"],
            "balance": result["balance"],
            "places": result["places"],
            "positions": [
                {
                    "symbol": o["symbol"],
                    "entryPrice": o["entryPrice"],
                    "kind": o["positionSide"].lower() if o["positionSide"] else None,
                    "quantity": abs(o["positionAmt"] or 0),
                    "leverage": o["leverage"],
                    "maximumLeverage": o["maximumLeverage"],
                }
                for o in result["positions"]
            ],
            "stop_orders": {
                "long": result["stop_orders"].get("long"),
                "short": result["stop_orders"].get("short"),
            },
        }

    def create_new_trade(self, params: TradeType):
        result = self.api_call("create-new-trade", "POST", params)
        return {
            "symbol": result["symbol"],
            "entryPrice": result["entryPrice"],
            "kind": params.kind,
            "quantity": abs(result["positionAmt"]),
            "stop": result["stop"],
            "takeProfit": None,
        }

    def update_stop_loss(self, params: StopLossType):
        result = self.api_call(
            "market-update-stop-loss",
            "POST",
            {
                "symbol": params.symbol,
                "kind": params.kind,
                "pip": params.pip,
                "price": params.stopPrice,
                "trade": True,
                "delete": True,
                "style": "stop",
            },
        )
        return result.stop

    def update_take_profit(self, params: StopLossType):
        result = self.api_call(
            "simple-order",
            "POST",
            {
                "symbol": params.symbol,
                "kind": params.kind,
                "entry": params.takeProfitPrice,
                "quantity": params.quantity,
                "side": "sell" if params.kind == "long" else "buy",
            },
        )
        return {**result, "takeProfit": params["takeProfitPrice"]}

    def market_close_trade(self, params: StopLossType):
        result = self.api_call(
            "simple-order",
            "POST",
            {
                "symbol": params.symbol,
                "kind": params.kind,
                "entry": params.stopPrice,
                "quantity": params.quantity,
                "side": "sell" if params.kind == "long" else "buy",
            },
        )
        openTrade = {
            "symbol": result["symbol"],
            "entryPrice": result["entryPrice"],
            "kind": params.kind,
            "quantity": abs(result["positionAmt"]),
        }
        return openTrade

    def fetch_all_market(self, params: MarketType):
        result = self.api_call(f"/ft/{params.owner}/tradeable-markets`", "GET", {})
        return {"allMarkets": result["usdt"] + result["coin"]}

    def get_bot_account(self, params):
        today = datetime.now()
        result = self.api_call(
            f"/get-bots/all?timestamp={int(today.timestamp() * 1000)}", "GET", {}
        )
        return [
            {
                "owner": o["owner"],
                # "configs": o["config"][0],
                "configs": o["config"],
                "exchanges": o.get("exchanges", []),
            }
            for o in result["data"]
        ]

    def update_config(self, params: UpdateConfigType):
        result = self.api_call(
            "/save-watch-config",
            "POST",
            {
                "owner": params.owner,
                "data": params.config,
            },
        )
        return result.status

    def update_orders(self, params: UpdateOrderType):
        variable = "t" if params.action else ""
        result = self.api_call(
            f"/check-if-trade-can-be-placed/{params.owner}/{params.symbol}?trade={variable}",
            "GET",
            {},
        )
        return result.result

    def update_stop_trade(self, params: StopTradeType):
        result = self.api_call(
            f"/ft/{params.owner}/replace-stop-market-trade",
            "POST",
            {
                "symbol": params.symbol,
                "entry": params.order["entry"],
                "size": params.order["size"],
                "kind": params.order["kind"],
            },
        )
        return result.status

    def add_symbol_to_background(self, params: SymbolType):
        result = self.api_call("/api/scheduler/add-symbol", "POST", params)
        return result.status

    def remove_symbol_from_background(self, params: SymbolType):
        result = self.api_call("/api/scheduler/delete-symbol", "POST", params)
        return result.status

    def create_job(self, params):
        result = self.api_call("/api/scheduler/run-future-job", "POST", params)
        return result.status

    def add_new_symbol(self, params: SymbolType):
        result = self.api_call(
            f"/ft/{params.owner}/get_bot_config/{params.symbol}", "GET", {}
        )
        response = self.api_call(
            "/save-watch-config", "POST", {"owner": params.owner, "data": result}
        )
        return response.status

    def delete_symbol(self, params: SymbolType):
        result = self.api_call(
            f"delete-watch-config/{params.owner}/{params.symbol}", "GET", {}
        )
        return result.data

    def delete_job(self, params):
        result = self.api_call("/api/scheduler/delete-future-job", "POST", params)
        return result.status

    def pause_job(self, params):
        result = self.api_call("/api/scheduler/toggle-future-job", "POST", params)
        return result.status

    def run_job(self, params):
        result = self.api_call("/api/scheduler/process-future-job", "POST", params)
        return result.status

    def edit_job(self, params):
        result = self.api_call("/api/edit-job-config", "POST", params)
        return result.data

    def toogle_jobs_with_action(self, params):
        result = self.api_call("/api/scheduler/toggle-jobs-with-action", "POST", params)
        return result.data

    def bulk_job_action(self, params):
        result = self.api_call("/api/scheduler/symbol-action", "POST", params)
        return result.data

    def get_job_status(self, params: JobType):
        result = self.api_call(f"api/scheduler/job-info/{params.job_id}", "GET", {})
        return result.data

    def create_profile(self, params):
        result = self.api_call("/api/scheduler/create-profile", "POST", params)
        return result.data

    def edit_profile(self, params):
        result = self.api_call("/api/scheduler/edit-profile", "POST", params)
        return result.data

    def delete_profile(self, params):
        result = self.api_call("/api/scheduler/delete-profile", "POST", params)
        return result.data

    def temp_pause_market(self, params):
        result = self.api_call("/api/scheduler/reduce-position", "POST", params)
        return result.data

    def run_profile(self, params: RunProfileType):
        result = self.api_call(
            f"/api/scheduler/run-profile/{params.owner}/{params.symbol}/{params.profile_id}?start={params.start}&old_mode={params.old_mode}&new_future={params.new_future}",
            "GET",
            {},
        )
        return result.data

    def remove_open_orders(self, params: OpenOrderType):
        result = self.api_call(f"/ft/{params.owner}/cancel-all-orders", "POST", params)
        return result.msg

    def get_spot_symbols(self, params: SpotSymbolType):
        result = self.api_call(
            f"/ft/{params.owner}/spot/{params.coin}/symbols", "GET", {}
        )
        return result.data

    def create_spot_profile(self, params: CreateSpotProfileType):
        profile = params["profile"]
        payload = {
            "symbol": "BTCUSDT",
            "spot_symbol": params["symbol"],
            "owner": params["owner"],
            "profile": {
                "symbol": params["symbol"],
                "focus": profile["support"],
                "zone_risk": 0,
                "gap": 1,
                "zone_split": 4,
                "price_places": profile["price_places"],
                "buy_more": False,
                "is_margin": False,
                "budget": 100,
                "expected_loss": 10,
                "risk_reward": 1,
                "spread": 0,
                "follow_profit": False,
                "follow_stop": False,
                "entry_price": 0,
                "dollar_price": 0,
                "max_size": 0.001,
                "bull_factor": 3,
                "bear_factor": 1,
                "loss_factor": 3,
                "support": profile["support"],
                "resistance": profile["resistance"],
                "tradeSplit": 5,
                "futureBudget": 5,
                "decimal_places": profile["decimal_places"],
                "min_size": profile["min_size"],
                "transfer_funds": True,
                "sub_accounts": [],
                "margin_sub_account": "",
                "risk_per_trade": 30,
                "profit_quote_price": 10000,
                "profit_base_price": 100000,
                "fee_percent": 0.0005,
            },
        }
        result = self.api_call("api/spot/create-profile", "POST", payload)
        return result["data"]

    def updateTPSL(self, params: SpotProfileType):
        result = self.api_call("/api/spot/update-take-profit-stop", "POST", params)
        return result.data

    def delete_spot_profile(self, params: SpotProfileType):
        result = self.api_call("/api/spot/delete-spot-symbol", "POST", params)
        return result.data

    def run_spot_profile(self, params: SpotProfileType):
        result = self.api_call(
            f"api/spot/run-profile/{params.owner}/{params.symbol}/{params.spot_symbol}",
            "GET",
            {},
        )
        return result.data

    def close_position(self, params: ClosePosionType):
        result = self.api_call("/api/scheduler/update-protect-profit", "POST", params)
        return result

    def update_protect_profit(self, params: UpdateProtectProfitType):
        result = self.api_call("api/scheduler/update-protect-profit", "POST", params)
        return result

    def place_future_order(self, params: PlaceFutureType):
        if params.kind in ["spot", "margin"]:
            return self.api_call(
                f"/api/${params.kind}/${params.symbol}/place-oco-orders", "POST", params
            )
        result = self.api_call(
            f"/api/multi-trade/{params.symbol}/place-orders",
            "POST",
            {
                **params,
                "multipier": None,
                "place_order": True,
                "cancel_orders": False,
                "another_order": None,
                "new": True,
                "start_price": None,
            },
        )
        return result

    def create_single_controlled_order(self, params: CreateSingleOrdersType):
        result = self.api_call(
            f"/api/single-trade/{params.symbol}/place-orders", "POST", params
        )
        return result

    def analyzePosition(self, params: AnalyzePositionType):
        pass

    def place_signal_orders(self, params: TradeSignalType):
        result = self.api_call(
            "api/signals/place-orders",
            "POST",
            {
                "symbol": params["symbol"].upper(),
                "cancel": bool(params.get("cancel")),
                "kind": params.get("kind"),
                "orders": params["orders"],
                "sub_accounts": [params["sub_accounts"]],
            },
        )
        return result

    def update_close_prices(self, params: TradeUpdatePriceType):
        result = self.api_call(
            "api/signals/update-close-prices",
            "POST",
            {
                "trades": {
                    params["kind"]: {
                        params["symbol"].upper(): params["orders"],
                    }
                },
                "reduce": params.get("reduce"),
                "sub_accounts": params["sub_accounts"],
                "fee_rate": params.get("fee_rate"),
            },
        )
        return result

    def reduce_position(self, params):
        result = self.api_call(
            "api/signals/reduce-position",
            "POST",
            {
                "symbol": params["symbol"],
                "kind": params["kind"],
                "owner": params["owner"],
                "cancel": params.get("cancel"),
                "close_price": params.get("close_price"),
                "quantity": params.get("quantity"),
            },
        )
        return result

    def place_margin_signal_trade(self, params: PlaceMarginType):
        result = self.api_call(
            "api/signals/place-margin-order",
            "POST",
            {**params, "symbol": params["symbol"].upper()},
        )
        return result

    def update_margin_close_prices(self, params: UpdateMarginType):
        result = self.api_call(
            "api/signals/update-margin-close-prices",
            "POST",
            {**params, "symbol": params["symbol"].upper()},
        )
        return result

    def get_exchange_info(self, params: GetExchangeInfoType):
        symbol = params.get("symbol")
        owner = params.get("owner")
        future_only = params.get("future_only") or False
        result = self.api_call(
            "api/all-alerts/action",
            "POST",
            {
                "action": "data",
                "style": "new",
                "data": {
                    "margin": {symbol: []},
                    "future": {symbol: []},
                },
                "owner": owner,
                "future_only": future_only,
                "from_profile": False,
                "from_cache": False if params.get("save") else True,
                "symbol": symbol,
            },
        )
        return result["data"]

    async def get_exchange_info_for_account(self, params: dict):
        symbol = params.get("symbol")
        owners = params.get("owners")
        # Prepare the request data
        request_data = {
            "action": "data",
            "style": "new",
            "data": {
                "margin": {symbol: []},
                "future": {symbol: []},
            },
            "owner": owners,
            "future_only": False,
            "from_profile": False,
        }

        # Make the API call
        result = self.api_call("api/get-accounts-info", "POST", request_data)
        return result["data"]

    def update_take_profit_new(self, params: UpdateTakeProfitNewType):
        result = self.api_call(
            "api/signals/update-close-prices",
            "POST",
            {
                "trades": {
                    params["kind"]: {
                        params["symbol"].upper(): {"sell-price": params["price"]},
                    },
                },
                "sub_accounts": [params["owner"]],
            },
        )
        return result

    def update_stop_loss_new(self, params: UpdateStopLossNewType):
        result = self.api_call(
            "api/signals/reduce-position",
            "POST",
            {
                "symbol": params["symbol"].upper(),
                "kind": params["kind"],
                "owner": params["owner"],
                "price": params["price"],
            },
        )
        return result

    def close_open_orders(self, params: CloseOpenOrdersType):
        result = self.api_call(
            "api/cancel-orders",
            "POST",
            {
                "symbol": params["symbol"],
                "owner": params["owner"],
                "orders": params["order_ids"],
                "market_type": params.get("market_type"),
            },
        )
        print(result, "here")
        return result

    def increase_position(self, params: IncreasePositionType):
        result = self.api_call(
            "api/signals/place-orders",
            "POST",
            {
                "symbol": params["symbol"],
                "orders": params["orders"],
                "sub_accounts": [params["owner"]],
            },
        )
        return result

    def get_orders_for_account(self, params: AccountOrdersType):
        result = self.api_call(
            "/api/all-alerts/action",
            "POST",
            {
                "action": "data",
                "style": "new",
                "data": {
                    "margin": {params["symbol"]: []},
                    "future": {params["symbol"]: []},
                },
                "owner": params["owner"],
                "from_profile": False,
            },
        )
        data = result["data"]
        instance = AccountParser(data, params.symbol)
        return {
            "accounts": instance.buildAccounts(),
            "coin": instance.base.upper(),
            "collateral": instance.collateral,
            "loan": instance.loan,
            "quote_loan": instance.QUOTE,
            "base_collateral": instance.base_collateral,
        }

    def create_orders_for_account(self, params: CreateOrdersType):
        result = self.api_call("/api/create-orders", "POST", params)
        return result

    def get_spot_config(self, params: dict):
        result = self.api_call(
            "api/get-spot-config",
            "POST",
            {
                "owner": params["owner"],
                "symbol": params["symbol"],
            },
        )
        return result["data"]

    def get_candlesticks(self, params: CandleStickParamType):
        result = self.api_call(
            "api/analysis/klines",
            "POST",
            {
                "symbol": params["symbol"],
                "interval": params["interval"],
                "count": params["count"],
                "raw": params.get("raw"),
            },
        )
        return result["data"]

    def trade_actions(self, params: TradeActionParamType):
        result = self.api_call(
            "api/generated-trades/actions",
            "POST",
            {
                "symbol": params["symbol"],
                "action": params["action"],
                "owner": params["owner"],
                "trades": params.get("trades"),
            },
        )
        return result["data"]

    def lightning_withdraw(self, params: WithdrawParamType):
        result = self.api_call(
            f"api/{params['owner']}/withdraw",
            "POST",
            {
                "btcAddress": params["invoice"],
                "symbol": params["symbol"],
                "amount": params["amount"],
                "coin": "BTC",
                "network": "LIGHTNING",
                "to": "btc",
            },
        )
        return result["data"]

    def lightning_deposit(self, params: DepositParamType):
        result = self.api_call(
            f"api/{params['owner']}/deposit",
            "POST",
            {
                "amount": params["amount"],
            },
        )
        return result["data"]

    def borrow_repay_margin(self, params: BorrowRepayParamType):
        result = self.api_call(
            f"api/{params['owner']}/margin-actions",
            "POST",
            {
                "action": "borrow_repay",
                "loan": {
                    "base": params["base"],
                    "quote": params["quote"],
                },
                "mode": params.get("mode") or "isolated",
                "symbol": params["symbol"],
            },
        )
        return result

    def transfer_balance(self, params: SyncBalanceType):
        spot_balance = {"base": 0, "quote": 0}
        margin_balance = {"base": 0, "quote": 0}
        if params["to"] == "margin":
            margin_balance["base"] = params.get("base", 0)
            margin_balance["quote"] = params.get("quote", 0)
        else:
            spot_balance["base"] = params.get("base", 0)
            spot_balance["quote"] = params.get("quote", 0)

        result = self.api_call(
            f"api/{params['owner']}/margin-actions",
            "POST",
            {
                "action": "balance_state",
                "balances": {
                    "spot": spot_balance,
                    "margin": margin_balance,
                },
                "symbol": params["symbol"],
                "mode": params.get("mode") or "isolated",
            },
        )
        return result["data"]

    def place_margin_new_trade(self, params: NewTradeType):
        result = self.api_call(
            f"api/{params['owner']}/margin-actions",
            "POST",
            {
                "action": "place_order",
                "order": {
                    "cancel": False,
                    "price": params["price"],
                    "amount": params["amount"],
                    "increase": params.get("increase", 50),
                    "diff": params.get("diff", 0.00001),
                    "decimal_places": params["decimal_places"],
                },
                "type": params.get("type"),
                "symbol": params["symbol"],
                "mode": params.get("mode") or "isolated",
            },
        )
        return result["data"]

    def get_delivery_symbols(self, params):
        result = self.api_call("api/get-delivery-symbols", "GET", {})
        return result["data"]

    def cancel_margin_new_trade(self, params: NewTradeType):
        result = self.api_call(
            f"api/{params['owner']}/margin-actions",
            "POST",
            {
                "action": "place_order",
                "order": {
                    "cancel": True,
                },
                "symbol": params["symbol"],
                "mode": params.get("mode") or "isolated",
            },
        )
        return result["data"]

    def margin_actions(self, params: NewTradeType):
        result = self.api_call(
            f"api/{params['owner']}/margin-actions",
            "POST",
            {
                "action": params["action"],
                "mode": params.get("mode") or "isolated",
                "symbol": params["symbol"],
            },
        )
        return result["data"]

    def get_analyze_candlesticks(self, params):
        result = self.api_call(
            f'api/{params["owner"]}/remote-actions',
            "POST",
            {
                "action": "base_model",
                "symbol": params["symbol"],
                "name": "base_model",
                "params": {
                    "args": ["analyze_candlesticks"],
                    "kwargs": {"symbol": params["symbol"]},
                },
            },
        )
        return result['data']

    def get_open_orders(self, params):
        result = self.api_call(
            f"api/{params['owner']}/remote-actions",
            "POST",
            {
                "action": "get_open_orders",
                "symbol": params["symbol"],
                "name": "get_open_orders",
                "params": {"args": [], "kwargs": {}},
            },
        )
        return result["data"]

    def get_current_positions(self, params):
        result = self.api_call(
            f"api/{params['owner']}/remote-actions",
            "POST",
            {
                "action": "get_position",
                "symbol": params["symbol"],
                "name": "get_position",
                "params": {"args": [], "kwargs": {"skip": True}},
            },
        )
        return result["data"]

    def place_raw_orders(self, params):
        result = self.api_call(
            f'api/{params["owner"]}/remote-actions',
            "POST",
            {
                "action": "create_limit_purchase_orders",
                "symbol": params["symbol"],
                "name": "create_limit_purchase_orders",
                "params": {
                    "args": [params["orders"]],
                    "kwargs": {"_working_type": "contract"},
                },
            },
        )
        return result["data"]

    def get_symbols_for_the_day(self, params):
        result = self.api_call(
            f"api/{params['owner']}/remote-actions",
            "POST",
            {
                "action": "client_call",
                "symbol": params["symbol"],
                "name": "client_call",
                "params": {"args": ["futures_ticker"], "kwargs": {}},
            },
        )
        symbols = [
            {**x, "percent_change": float(x["priceChangePercent"])}
            for x in result["data"]
        ]
        symbols = sorted(symbols, key=lambda x: x["percent_change"], reverse=True)
        return [x for x in symbols if x["percent_change"] > 20]
        print("result", result)
        return result["data"]

    def last_closed_order(self, params: OpenOrderType):
        result = self.api_call(
            f"api/{params['owner']}/remote-actions",
            "POST",
            {
                "action": "last_closed_order",
                "symbol": params["symbol"],
                "name": "last_closed_orders",
                "params": {"args": [], "kwargs": {"entry": True}},
            },
        )
        return result["data"]

    def cross_transfer(self, params):
        result = self.api_call(
            f"api/cross-transfer",
            "POST",
            {
                "amount": params["amount"],
                "asset": params["asset"],
                "from": {"owner": params["owner"], "wallet": params["from"]},
                "to": {"owner": params["owner"], "wallet": params["to"]},
            },
        )
        return result["data"]

    def notify_by_telegram(self, params: NotifyType):
        result = self.api_call(
            "api/send-notification/telegram",
            "POST",
            {"message": params["message"], "owner": params["owner"]},
        )
        return result

    def lightning_decode(self, params):
        result = self.api_call(
            "api/lightning/decode", "POST", {"invoice": params["invoice"]}
        )
        return result

    def repay_loan_in_parent(self, params):
        result = self.api_call(
            "api/signals/transfer-repay-loan",
            "POST",
            {
                "owner": params["owner"],
                "parent": params["parent"],
                "symbol": params["symbol"],
            },
        )
        return result

    def get_credentials(self, params):
        result = self.api_call(
            f'api/websocket-exchange-account-info?access={params["access"]}',
            "POST",
            {
                "owner": params["owner"],
            },
        )
        return result

    def get_listen_key(self, params):
        owner = params.pop("owner")
        symbol = params.pop("symbol")
        new = params.pop("new")
        result = self.api_call(
            f"api/{owner}/remote-actions",
            "POST",
            {
                "action": "",
                "symbol": symbol,
                "name": "client_call",
                "params": {
                    "args": ["get_futures_listen_key"],
                    "kwargs": {"new": new, **params, "symbol": symbol},
                },
            },
        )
        return result["data"]

    async def create_task(self, name, params):
        func = getattr(self, name)
        return func(params)

    def run_async(self, coroutine):
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coroutine)

    def place_create_trader(self, params):
        owner = params.pop("owner")
        symbol = params.pop("symbol")
        trade_type = params.pop("trade_type")
        payload = params.pop("payload")
        price_places = params.pop("price_places", "%0.1f")
        decimal_places = params.pop("decimal_places", "%0.3f")
        action = params.pop("action")
        tp_kind = params.pop("tp_kind", None)

        orders_to_place = create_trader(
            payload,
            price_place=price_places,
            decimal_places=decimal_places,
            trade_type=trade_type,
        )
        long_signal_orders = [
            x for x in orders_to_place["entry"] if x["kind"] == "long"
        ]
        short_signal_orders = [
            x for x in orders_to_place["entry"] if x["kind"] == "short"
        ]
        long_stop_orders = [x for x in orders_to_place["stop"] if x["kind"] == "long"]
        short_stop_orders = [x for x in orders_to_place["stop"] if x["kind"] == "short"]
        long_tp_orders = [
            x for x in orders_to_place["take_profit"] if x["kind"] == "long"
        ]
        short_tp_orders = [
            x for x in orders_to_place["take_profit"] if x["kind"] == "short"
        ]
        if action == "get":
            return orders_to_place
        if action == "entry":
            # cancel all existing orders
            task1 = self.create_task(
                "place_signal_orders",
                {
                    "cancel": True,
                    "symbol": symbol,
                    "orders": long_signal_orders,
                    "sub_accounts": owner,
                    "kind": "long",
                },
            )
            task2 = self.create_task(
                "place_signal_orders",
                {
                    "cancel": True,
                    "symbol": symbol,
                    "orders": short_signal_orders,
                    "sub_accounts": owner,
                    "kind": "short",
                },
            )

            async def run(tasks):
                return await asyncio.gather(*tasks)

            self.run_async(run([task1, task2]))
            # place new orders
            task1 = self.create_task(
                "place_signal_orders",
                {
                    "symbol": symbol,
                    "orders": long_signal_orders,
                    "sub_accounts": owner,
                    "kind": "long",
                },
            )
            task2 = self.create_task(
                "place_signal_orders",
                {
                    "symbol": symbol,
                    "orders": short_signal_orders,
                    "sub_accounts": owner,
                    "kind": "short",
                },
            )
            first, second = self.run_async(run([task1, task2]))
            return {"entry": {"first": first, "second": second}}
        if action == "stop":
            first = self.place_raw_orders(
                {
                    "symbol": symbol,
                    "owner": owner,
                    "orders": long_stop_orders + short_stop_orders,
                }
            )
            return {"stop": first}
        if action == "tp" and tp_kind:
            orders = long_tp_orders if tp_kind == "long" else short_tp_orders
            first = self.update_close_prices(
                {
                    "symbol": symbol,
                    "sub_account": [owner],
                    "orders": orders,
                    "owner": owner,
                    "kind": tp_kind,
                    "reduce": False,
                }
            )
            return {"tp": first}
