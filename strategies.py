import backtrader as bt

class EmaCrossWithCandleStop(bt.Strategy):
    params = (('fast_ema', 9), ('slow_ema', 20))
    def __init__(self):
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.params.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.params.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0: self.close()

class RSIStrategy(bt.Strategy):
    params = (('rsi_period', 14), ('oversold', 30), ('overbought', 70))
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
    def next(self):
        if not self.position:
            if self.rsi < self.params.oversold: self.buy()
        else:
            if self.rsi > self.params.overbought: self.close()

class GoldenCrossStrategy(bt.Strategy):
    params = (('fast_sma', 50), ('slow_sma', 200))
    def __init__(self):
        fast_sma = bt.indicators.SMA(self.data.close, period=self.params.fast_sma)
        slow_sma = bt.indicators.SMA(self.data.close, period=self.params.slow_sma)
        self.crossover = bt.indicators.CrossOver(fast_sma, slow_sma)
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0: self.close()

STRATEGIES = {
    'ema_cross': (EmaCrossWithCandleStop, "EMA Crossover (9/20)"),
    'rsi_strategy': (RSIStrategy, "RSI Strategy (Oversold/Overbought)"),
    'golden_cross': (GoldenCrossStrategy, "Golden Cross (50/200 SMA)")
}