from flask import Flask, render_template, request, session, redirect, url_for
import yfinance as yf
from datetime import datetime
import backtrader as bt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback

# Matplotlib backend setting Agg for headless servers
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_12345'

# ======================================================================
# 1. सर्व STRATEGIES आता याच फाईलमध्ये आहेत
# ======================================================================
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

# ======================================================================
# 2. सर्व BACKTESTING ENGINE आता याच फाईलमध्ये आहे
# ======================================================================
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
    strategy_instance = cerebro.addstrategy(strategy_class)
    
    cerebro.broker.setcommission(commission=0.002)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(TrendAnalyzer, _name='trend_analyzer')
    
    results = cerebro.run()
    
    final_capital = cerebro.broker.getvalue()
    trade_analysis = results[0].analyzers.trade_analyzer.get_analysis()
    drawdown_analysis = results[0].analyzers.drawdown.get_analysis()
    trend_analysis = results[0].analyzers.trend_analyzer.get_analysis()
    
    return final_capital, trade_analysis, drawdown_analysis, trend_analysis, strategy_instance

# ======================================================================
# 3. सर्व PLOTTING आता याच फाईलमध्ये आहे
# ======================================================================
def create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{stock_name} Chart', 'Volume'), 
                        row_heights=[0.8, 0.2])

    fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], 
                                 low=data_df['Low'], close=data_df['Close'], name='Price'), 
                  row=1, col=1)

    fig.add_trace(go.Bar(x=data_df.index, y=data_df['Volume'], name='Volume', marker_color='rgba(90, 100, 150, 0.5)'), row=2, col=1)
    
    buy_dates_in_df = [d for d in buy_signals if d in data_df.index]
    sell_dates_in_df = [d for d in sell_signals if d in data_df.index]

    if buy_dates_in_df:
        fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, mode='markers', marker=dict(color='#2ecc71', size=12, symbol='triangle-up'), name='Buy Signal'), row=1, col=1)
    if sell_dates_in_df:
        fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, mode='markers', marker=dict(color='#e74c3c', size=12, symbol='triangle-down'), name='Sell Signal'), row=1, col=1)
    
    fig.update_layout(title_text=f'{stock_name} - {strategy_name}', template='plotly_dark', xaxis_rangeslider_visible=True,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig.to_html(full_html=False, config={'scrollZoom': True})

# ======================================================================
# 4. मुख्य FLASK APP
# ======================================================================
TIMEFRAMES = {
    '5m': "5 Minutes", '15m': "15 Minutes", '30m': "30 Minutes",
    '1h': "1 Hour", '1d': "Daily", '1wk': "Weekly", '1mo': "Monthly"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        stock_name = request.form.get('stock_name')
        selected_strategy_key = request.form.get('strategy')
        timeframe = request.form.get('timeframe')

        if not all([stock_name, selected_strategy_key, timeframe]):
            return "<h1>Error</h1><p>सर्व माहिती भरणे आवश्यक आहे.</p>"
        
        # हा कोड आता क्रॅश होणार नाही, कारण STRATEGIES याच फाईलमध्ये आहे
        StrategyClass, strategy_display_name = STRATEGIES.get(selected_strategy_key)
        
        initial_capital = 100000.0
        from_date = datetime(1996, 1, 1)
        to_date = datetime.now()

        if timeframe in ['5m', '15m', '30m', '1h']:
            data_df = yf.Ticker(stock_name).history(period="60d", interval=timeframe)
        else:
            data_df = yf.Ticker(stock_name).history(start=from_date, end=to_date, interval=timeframe)
        
        min_required_data = 200
        if data_df.empty or len(data_df) < min_required_data: 
            return f"<h1>Error</h1><p>'{stock_name}' साठी पुरेसा डेटा सापडला नाही.</p>"
        
        data = bt.feeds.PandasData(dataname=data_df)
        
        final_capital, trade_analysis, drawdown_analysis, trend_analysis, strategy_instance = run_backtest(data, StrategyClass, initial_capital)
        pnl = final_capital - initial_capital
        
        buy_signals = strategy_instance.buy_signals
        sell_signals = strategy_instance.sell_signals
        
        chart_html = create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_display_name)
        
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        win_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)

        session['result_data'] = {
            'stock': stock_name, 'strategy_name': strategy_display_name,
            'timeframe': TIMEFRAMES.get(timeframe), 'initial_cap': f'{initial_capital:,.2f}',
            'final_cap': f'{final_capital:,.2f}', 'pnl': f'{pnl:,.2f}', 'pnl_numeric': pnl,
            'total_trades': total_trades, 'win_rate': f'{win_rate:.2f}', 'max_drawdown': f'{max_drawdown:.2f}',
            'trend_analysis': trend_analysis, 'chart_html': chart_html
        }
        return redirect(url_for('show_chart'))

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"----------- DETAILED ERROR -----------\n{error_details}------------------------------------")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे: {e}</p>"

@app.route('/chart')
def show_chart():
    result_data = session.get('result_data')
    if not result_data: return redirect(url_for('index'))
    return render_template('chart_page.html', **result_data)

@app.route('/summary')
def show_summary():
    result_data = session.get('result_data')
    if not result_data: return redirect(url_for('index'))
    return render_template('results_summary_page.html', **result_data)