
def to_f(double value, char* places=".1f") -> double:
    cdef double v
    v = value
    if isinstance(v, str):
        v = float(value)
    return float(places % v)

def determine_stop_and_size(double entry, double pnl, double take_profit, kind="long"):
    cdef double difference, quantity
    if kind == "long":
        difference = take_profit - entry
    else:
        difference = entry - take_profit
    quantity = pnl / difference
    return abs(quantity)