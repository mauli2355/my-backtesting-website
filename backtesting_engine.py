import backtrader as bt

class TrendAnalyzer(bt.Analyzer):
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data, period=200)
        self.results = {'uptrend': {'pnl': 0, 'trades': 0}, 'downtrend': {'pnl': 0, 'trades': 0}}

    def notify_trade(self, trade):
        if trade.isclosed:
            price_at_close = self.data.close[0]
            sma_at_close = self.sma[0]
            if price_at_close > sma_at_close:
                self.results['uptrend']['pnl'] += trade.pnlcomm
                self.results['uptrend']['trades'] += 1
            else:
                self.results['downtrend']['pnl'] += trade.pnlcomm
                self.results['downtrend']['trades'] += 1

    def get_analysis(self):
        return self.results

def run_backtest(data, strategy_class, initial_capital):
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_capital)
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_class)
    cerebro.broker.setcommission(commission=0.002)
    
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(TrendAnalyzer, _name='trend_analyzer')
    
    results = cerebro.run()
    
    final_capital = cerebro.broker.getvalue()
    trade_analysis = results[0].analyzers.trade_analyzer.get_analysis()
    trend_analysis = results[0].analyzers.trend_analyzer.get_analysis()
    
    return final_capital, trade_analysis, trend_analysis