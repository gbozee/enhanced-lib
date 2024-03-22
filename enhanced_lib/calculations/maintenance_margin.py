def calc(floor, value, previous):
    return floor * ((value["m_rate"] - previous["m_rate"]) / 100) + previous["m_a"]


def between(low, position_size, high):
    return low < position_size <= high


def coin_leverage_25(
    position_size,
    symbol,
    m_rate=2.4,
):
    coin_25 = {
        "EGLD": [x * 10000 for x in [1, 2, 5, 10, 15, 20]],
    }
    return coin_leverage_50(position_size, symbol, m_rate, coin_25, "EGLD")


coin_20 = {
    "DOGE": [x * 1000 for x in [1, 5, 25, 100, 250, 1000]],
}


def coin_leverage_20(
    position_size,
    symbol="DOGEUSD_PERP",
    m_rate=1.2,
):
    marketOnly = symbol.split("USD_")[0]
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    func = coin_20.get(marketOnly)
    if not func:
        func = coin_20["DOGE"]

    if between(func[0], position_size, func[1]):
        value["m_rate"] = 2.5
        base_value = func[0]
    elif between(func[1], position_size, func[2]):
        value["m_rate"] = 5
        base_value = func[1]
    elif between(func[2], position_size, func[3]):
        value["m_rate"] = 10
        base_value = func[2]
    elif between(func[3], position_size, func[4]):
        value["m_rate"] = 12.5
        base_value = func[3]
    elif between(func[4], position_size, func[5]):
        value["m_rate"] = 25
        base_value = func[4]
    elif position_size > func[4]:
        value["m_rate"] = 50
        base_value = func[5]

    return {"minimum": func[0], "value": value, "base_value": base_value}


coin_50 = {
    "FIL": [x * 10000 for x in [1, 2, 5, 10, 15, 20]],
}


def coin_leverage_50(
    position_size,
    symbol="FILUSD_PERP",
    m_rate=2.2,
    array=coin_50,
    defaultString="FIL",
    last=25,
):
    marketOnly = symbol.split("USD_")[0]
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    func = array.get(marketOnly)
    if not func:
        func = array[defaultString]

    if between(func[0], position_size, func[1]):
        value["m_rate"] = 4.9
        base_value = func[0]
    elif between(func[1], position_size, func[2]):
        value["m_rate"] = 5
        base_value = func[1]
    elif between(func[2], position_size, func[3]):
        value["m_rate"] = 10
        base_value = func[2]
    elif between(func[3], position_size, func[4]):
        value["m_rate"] = 12.5
        base_value = func[3]
    elif between(func[4], position_size, func[5]):
        value["m_rate"] = 15
        base_value = func[4]
    elif position_size > func[5]:
        value["m_rate"] = last
        base_value = func[5]

    return {"minimum": func[0], "value": value, "base_value": base_value}


def coin_leverage_75(position_size, symbol="BNTUSD_PERP", m_rate=1.85):
    marketOnly = symbol.upper().split("USD_")[0]
    coins_75 = {
        "BNB": [x * 1000 for x in [4, 8, 20, 40, 80, 120, 200]],
        "LTC": [x * 1000 for x in [5, 10, 20, 50, 100, 150, 200]],
        "BCH": [x * 1000 for x in [1, 2, 4, 10, 20, 30, 40]],
        "ADA": [x * 100000 for x in [5, 10, 20, 40, 80, 140, 200]],
        "XRP": [x * 100000 for x in [5, 10, 20, 50, 100, 150, 200]],
        "ETC": [x * 100000 for x in [5, 10, 20, 50, 100, 150, 200]],
        "LINK": [x * 1000 for x in [10, 20, 40, 80, 160, 280, 400]],
        "DOT": [x * 10000 for x in [5, 10, 20, 50, 100, 150, 200]],
        "EOS": [x * 10000 for x in [5, 10, 20, 50, 100, 150, 200]],
        "TRX": [x * 1000000 for x in [5, 10, 20, 50, 100, 200, 300]],
    }
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    func = coins_75.get(marketOnly)
    if not func:
        func = coins_75["BNB"]

    if between(func[0], position_size, func[1]):
        value["m_rate"] = 3.4
        base_value = func[0]
    elif between(func[1], position_size, func[2]):
        value["m_rate"] = 4.9
        base_value = func[1]
    elif between(func[2], position_size, func[3]):
        value["m_rate"] = 5
        base_value = func[2]
    elif between(func[3], position_size, func[4]):
        value["m_rate"] = 10
        base_value = func[3]
    elif between(func[4], position_size, func[5]):
        value["m_rate"] = 12.5
        base_value = func[4]
    elif between(func[5], position_size, func[6]):
        value["m_rate"] = 15
        base_value = func[5]
    elif position_size > func[6]:
        value["m_rate"] = 25
        base_value = func[6]

    return {"minimum": func[0], "value": value, "base_value": base_value}


def coin_leverage_100(position_size, m_rate=0.5):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 100 < position_size <= 500:
        value["m_rate"] = 0.65
        base_value = 100
    elif 500 < position_size <= 1000:
        value["m_rate"] = 1
        base_value = 500
    elif 1000 < position_size <= 2000:
        value["m_rate"] = 2.5
        base_value = 1000
    elif 2000 < position_size <= 4000:
        value["m_rate"] = 5
        base_value = 2000
    elif 4000 < position_size <= 6000:
        value["m_rate"] = 10
        base_value = 2000
    elif 6000 < position_size <= 8000:
        value["m_rate"] = 12.5
        base_value = 6000
    elif 8000 < position_size <= 10000:
        value["m_rate"] = 15
        base_value = 8000
    elif position_size > 10000:
        value["m_rate"] = 25
        base_value = 10000
    return {"minimum": 100, "base_value": base_value, "value": value}


def coin_leverage_125(position_size, m_rate=0.4,**kwargs):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 10 < position_size <= 20:
        value["m_rate"] = 0.5
        base_value = 10
    elif 20 < position_size <= 30:
        value["m_rate"] = 1
        base_value = 20
    elif 30 < position_size <= 50:
        value["m_rate"] = 2.5
        base_value = 30
    elif 50 < position_size <= 100:
        value["m_rate"] = 5
        base_value = 50
    elif 100 < position_size <= 200:
        value["m_rate"] = 10
        base_value = 100
    elif 200 < position_size <= 400:
        value["m_rate"] = 12.5
        base_value = 200
    elif 400 < position_size <= 1000:
        value["m_rate"] = 15
        base_value = 400
    elif position_size > 1000:
        value["m_rate"] = 25
        base_value = 1000
    return {"minimum": 10, "value": value, "base_value": base_value}


def leverage_25(position_size, m_rate=1,**kwargs):
    return leverage_50(position_size, m_rate=m_rate)


def leverage_20(position_size, m_rate=1.2,**kwargs):
    return leverage_25(position_size, m_rate=m_rate)


def leverage_50(position_size, m_rate=1,**kwargs):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 5000 < position_size <= 25000:
        value["m_rate"] = 2.5
        base_value = 5000
    elif 25000 < position_size <= 100000:
        value["m_rate"] = 5
        base_value = 25000
    elif 100000 < position_size <= 250000:
        value["m_rate"] = 10
        base_value = 100000
    elif 250000 < position_size <= 1000000:
        value["m_rate"] = 12.5
        base_value = 250000
    elif position_size > 1000000:
        value["m_rate"] = 50
        base_value = 1000000
    return {"minimum": 5000, "value": value, "base_value": base_value}


def leverage_75(position_size, m_rate=0.65,**kwargs):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 10000 < position_size <= 50000:
        value["m_rate"] = 1
        base_value = 10000
    elif 50000 < position_size <= 250000:
        value["m_rate"] = 2
        base_value = 50000
    elif 250000 < position_size <= 1000000:
        value["m_rate"] = 5
        base_value = 250000
    elif 1000000 < position_size <= 2000000:
        value["m_rate"] = 10
        base_value = 1000000
    elif 2000000 < position_size <= 5000000:
        value["m_rate"] = 12.5
        base_value = 2000000
    elif 5000000 < position_size <= 10000000:
        value["m_rate"] = 15
        base_value = 5000000
    elif position_size > 10000000:
        value["m_rate"] = 25
        base_value = 10000000
    return {"minimum": 10000, "value": value, "base_value": base_value}


def leverage_100(position_size, m_rate=0.5,**kwargs):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 10000 < position_size <= 100000:
        value["m_rate"] = 0.65
        base_value = 10000
    elif 100000 < position_size <= 500000:
        value["m_rate"] = 1
        base_value = 100000
    elif 500000 < position_size <= 1000000:
        value["m_rate"] = 2
        base_value = 500000
    elif 1000000 < position_size <= 2000000:
        value["m_rate"] = 5
        base_value = 1000000
    elif 2000000 < position_size <= 5000000:
        value["m_rate"] = 10
        base_value = 2000000
    elif 5000000 < position_size <= 10000000:
        value["m_rate"] = 12.5
        base_value = 5000000
    elif 10000000 < position_size <= 20000000:
        value["m_rate"] = 15
        base_value = 10000000
    elif position_size > 20000000:
        value["m_rate"] = 25
        base_value = 20000000
    return {"minimum": 10000, "value": value, "base_value": base_value}


def leverage_125(position_size, m_rate=0.4,**kwargs):
    value = {"m_rate": m_rate, "m_a": 0}
    base_value = 0
    if 50000 < position_size <= 250000:
        value["m_rate"] = 0.5
        base_value = 50000
    elif 250000 < position_size <= 1000000:
        value["m_rate"] = 1
        base_value = 250000
    elif 1000000 < position_size <= 5000000:
        value["m_rate"] = 2.5
        base_value = 1000000
    elif 5000000 < position_size <= 20000000:
        value["m_rate"] = 5
        base_value = 5000000
    elif 20000000 < position_size <= 50000000:
        value["m_rate"] = 10
        base_value = 20000000
    elif 50000000 < position_size <= 100000000:
        value["m_rate"] = 12.5
        base_value = 50000000
    elif 100000000 < position_size <= 200000000:
        value["m_rate"] = 15
        base_value = 100000000
    elif position_size > 200000000:
        value["m_rate"] = 25
        base_value = 200000000
    return {"minimum": 50000, "base_value": base_value, "value": value}
