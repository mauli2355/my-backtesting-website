from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import traceback

# Matplotlib backend setting Agg for headless servers
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# --- सर्व Strategy Classes येथे आहेत (यात कोणताही बदल नाही) ---
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
    def __init__(self): self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
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
            return "<h1>Error</h1><p>सर्व माहिती भरणे आवश्यक आहे.</p><a href='/'>परत जा</a>"

        StrategyClass, strategy_display_name = STRATEGIES.get(selected_strategy_key)
        timeframe_display_name = TIMEFRAMES.get(timeframe)
        
        initial_capital = 100000.0
        
        if timeframe in ['5m', '15m', '30m', '1h']:
            data_df = yf.Ticker(stock_name).history(period="60d", interval=timeframe)
        else:
            data_df = yf.Ticker(stock_name).history(period="5y", interval=timeframe)

        if data_df.empty: 
            return f"<h1>Error</h1><p>'{stock_name}' ({timeframe_display_name}) साठी डेटा सापडला नाही.</p><a href='/'>परत जा</a>"
        
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(initial_capital)
        cerebro.adddata(data)
        cerebro.addstrategy(StrategyClass)
        cerebro.broker.setcommission(commission=0.002)
        
        # नवीन Analyzers जोडणे
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        results = cerebro.run()
        
        final_capital = cerebro.broker.getvalue()
        pnl = final_capital - initial_capital

        # नवीन माहिती काढणे
        trade_analysis = results[0].analyzers.trade_analyzer.get_analysis()
        drawdown_analysis = results[0].analyzers.drawdown.get_analysis()
        
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        win_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], low=data_df['Low'], close=data_df['Close'], name='Price'))
        
        # --- ✅ हा आहे अंतिम आणि अचूक उपाय ---
        buy_dates, sell_dates = [], []
        
        # आपण आता फक्त 'trades' नावाच्या ड्रॉवरमध्येच शोधणार आहोत
        if trade_analysis and 'trades' in trade_analysis:
            for trade_id, trade_data in trade_analysis['trades'].items():
                if trade_data and 'dtopen' in trade_data:
                    buy_dates.append(trade_data['dtopen'])
                if trade_data and trade_data.get('status') == 'Closed' and 'dtclose' in trade_data:
                    sell_dates.append(trade_data['dtclose'])
        
        buy_dates_in_df = [d for d in buy_dates if d in data_df.index]
        sell_dates_in_df = [d for d in sell_dates if d in data_df.index]

        if buy_dates_in_df:
            fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, mode='markers', marker=dict(color='#2ecc71', size=10, symbol='triangle-up'), name='Buy'))
        if sell_dates_in_df:
            fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, mode='markers', marker=dict(color='#e74c3c', size=10, symbol='triangle-down'), name='Sell'))
        
        fig.update_layout(
            title_text=f'{stock_name} - {strategy_display_name}', 
            xaxis_title='Date', yaxis_title='Price', 
            xaxis_rangeslider_visible=True,
            template='plotly_dark'
        )
        chart_html = fig.to_html(full_html=False)

        return render_template('result.html', 
                               stock=stock_name, 
                               strategy_name=strategy_display_name,
                               timeframe=timeframe_display_name, 
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}', 
                               pnl=f'{pnl:,.2f}',
                               pnl_numeric=pnl,
                               win_rate=f'{win_rate:.2f}',
                               max_drawdown=f'{max_drawdown:.2f}',
                               total_trades=total_trades,
                               chart_html=chart_html)
    except Exception:
        error_details = traceback.format_exc()
        print("----------- DETAILED ERROR -----------")
        print(error_details)
        print("------------------------------------")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे. कृपया काही वेळाने पुन्हा प्रयत्न करा.</p>"