import backtrader as bt

class TrendAnalyzer(bt.Analyzer):
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data, period=200)
        self.results = {'uptrend': {'pnl': 0, 'trades': 0}, 'downtrend': {'pnl': 0, 'trades': 0}}
    def notify_trade(self, trade):
        if trade.isclosed:
            price_at_close = self.data.close[0]; sma_at_close = self.sma[0]
            if price_at_close > sma_at_close:
                self.results['uptrend']['pnl'] += trade.pnlcomm; self.results['uptrend']['trades'] += 1
            else:
                self.results['downtrend']['pnl'] += trade.pnlcomm; self.results['downtrend']['trades'] += 1
    def get_analysis(self): return self.results

def run_backtest(data, strategy_class, initial_capital):
    cerebro = bt.Cerebro(runonce=False)
    cerebro.broker.setcash(initial_capital)
    cerebro.adddata(data)
    
    # --- ✅ हा आहे अंतिम आणि अचूक उपाय ---
    # cerebro.addstrategy() फक्त स्ट्रॅटेजी जोडते, तिचा इंस्टन्स परत करत नाही.
    # खरा इंस्टन्स आपल्याला cerebro.run() नंतर मिळतो.
    cerebro.addstrategy(strategy_class)
    
    cerebro.broker.setcommission(commission=0.002)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(TrendAnalyzer, _name='trend_analyzer')
    
    # results मध्ये आता आपल्या चालवलेल्या स्ट्रॅटेजीचा इंस्टन्स आहे.
    results = cerebro.run()
    strategy_instance = results[0] # हा आहे खरा कर्मचारी!
    
    final_capital = cerebro.broker.getvalue()
    trade_analysis = strategy_instance.analyzers.trade_analyzer.get_analysis()
    drawdown_analysis = strategy_instance.analyzers.drawdown.get_analysis()
    trend_analysis = strategy_instance.analyzers.trend_analyzer.get_analysis()
    
    # आपण आता खरा स्ट्रॅटेजी इंस्टन्स परत पाठवत आहोत.
    return final_capital, trade_analysis, drawdown_analysis, trend_analysis, strategy_instance