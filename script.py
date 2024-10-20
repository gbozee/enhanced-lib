%load_ext autoreload
%autoreload 2
from enhanced_lib.exchange import ExchangeCache,Database
from enhanced_lib.exchange.types import TradeEntry

db = Database('https://app-dev.beeola.me')
# db = Database('http://localhost:8000')

# await db.generate_and_save_future_trades('main_account','BTCUSDT','gbozee1_sub_account')
# account = 'main_account'
account = 'sub_account'
symbol = 'ETHUSDT'
async def run(account,symbol):
    exchange = await db.get_initialized_exchange(account,symbol,account,True)
    # zones = exchange.future_instance.trade_entries
    # result = [{'entry':x['entry'],'stop':x['stop']} for x in zones]
    # # result
    # config = exchange.future_instance.config
    # config.strategy = 'quantity'
    # config.risk_per_trade = 1
    # config.determine_optimum_risk('short',result[1],max_size=.1,gap=.1,ignore=False)
    # risk_results = map(lambda x: config.determine_optimum_risk('long',x,max_size=.1,gap=.1),result)
    # print(list(risk_results))
    result = exchange.get_calculations_for_kind(kind='short')
    # result
    await exchange.save_trades(result)
    await exchange.get_trades()
    
    