from .database import Database

# db = Database('http://localhost:35969')

# await db.generate_and_save_future_trades('main_account','BTCUSDT','gbozee1_sub_account')
# account = 'main_account'


async def run(account, symbol, url):
    db = Database(url)
    exchange = await db.get_initialized_exchange(account, symbol, account, True)
    # zones = exchange.future_instance.trade_entries
    # result = [{'entry':x['entry'],'stop':x['stop']} for x in zones]
    # # result
    # config = exchange.future_instance.config
    # config.strategy = 'quantity'
    # config.risk_per_trade = 1
    # config.determine_optimum_risk('short',result[1],max_size=.1,gap=.1,ignore=False)
    # risk_results = map(lambda x: config.determine_optimum_risk('long',x,max_size=.1,gap=.1),result)
    # print(list(risk_results))
    result = exchange.get_calculations_for_kind(kind="long")
    # result
    await exchange.save_trades(result)
    await exchange.get_trades()


async def main(symbol, host, accounts):
    for account in accounts:
        if isinstance(symbol, list):
            for s in symbol:
                await run(account, s, host)
        else:
            await run(account, symbol, host)
        print(f"Completed {account}")



async def get_exchange(account,symbol,host='https://app-dev.beeola.me'):
    db = Database(host)
    exchange = await db.get_initialized_exchange(account,symbol,account,True)
    return exchange