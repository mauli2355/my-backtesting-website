import backtrader as bt

class EmaCross(bt.Strategy):
    params = (('fast_ema', 9), ('slow_ema', 20))
    def __init__(self):
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.params.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.params.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
        self.buy_signals = []
        self.sell_signals = []
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy(); self.buy_signals.append(self.data.datetime.date(0))
        elif self.crossover < 0: self.close(); self.sell_signals.append(self.data.datetime.date(0))

class RSIStrategy(bt.Strategy):
    params = (('rsi_period', 14), ('oversold', 30), ('overbought', 70))
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.buy_signals = []
        self.sell_signals = []
    def next(self):
        if not self.position:
            if self.rsi < self.params.oversold: self.buy(); self.buy_signals.append(self.data.datetime.date(0))
        else:
            if self.rsi > self.params.overbought: self.close(); self.sell_signals.append(self.data.datetime.date(0))

class GoldenCross(bt.Strategy):
    params = (('fast_sma', 50), ('slow_sma', 200))
    def __init__(self):
        fast_sma = bt.indicators.SMA(self.data.close, period=self.params.fast_sma)
        slow_sma = bt.indicators.SMA(self.data.close, period=self.params.slow_sma)
        self.crossover = bt.indicators.CrossOver(fast_sma, slow_sma)
        self.buy_signals = []
        self.sell_signals = []
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy(); self.buy_signals.append(self.data.datetime.date(0))
        elif self.crossover < 0: self.close(); self.sell_signals.append(self.data.datetime.date(0))

STRATEGIES = {
    'ema_cross': (EmaCross, "EMA Crossover (9/20)"),
    'rsi_strategy': (RSIStrategy, "RSI Strategy"),
    'golden_cross': (GoldenCross, "Golden Cross (50/200 SMA)")
}