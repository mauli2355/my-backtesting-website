# app.py

from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

app = Flask(__name__)

# --- सर्व Strategy Classes येथे आहेत (यात कोणताही बदल नाही) ---
class EmaCrossWithCandleStop(bt.Strategy):
    params = (('fast_ema', 9), ('slow_ema', 20))
    def __init__(self):
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.params.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.params.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
        self.stop_loss_order = None; self.signal_candle_low = None
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.exectype == bt.Order.Stop: self.stop_loss_order = None
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy(); self.signal_candle_low = self.data.low[0]
        else:
            if self.stop_loss_order is None:
                self.stop_loss_order = self.sell(exectype=bt.Order.Stop, price=self.signal_candle_low)
            if self.crossover < 0:
                if self.stop_loss_order: self.cancel(self.stop_loss_order)
                self.close()

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
# --- स्ट्रॅटेजीचा कोड समाप्त ---

STRATEGIES = {
    'ema_cross': (EmaCrossWithCandleStop, "EMA Crossover (9/20)"),
    'rsi_strategy': (RSIStrategy, "RSI Strategy (Oversold/Overbought)"),
    'golden_cross': (GoldenCrossStrategy, "Golden Cross (50/200 SMA)")
}

TIMEFRAMES = {
    '1d': "Daily",
    '1wk': "Weekly",
    '1mo': "Monthly"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        # --- माहिती मिळवण्याचा सुरक्षित मार्ग ---
        stock_name = request.form.get('stock_name')
        selected_strategy_key = request.form.get('strategy')
        timeframe = request.form.get('timeframe')

        # --- माहिती तपासणे ---
        if not all([stock_name, selected_strategy_key, timeframe]):
            return "<h1>Error</h1><p>सर्व माहिती (स्टॉक, स्ट्रॅटेजी, टाइमफ्रेम) भरणे आवश्यक आहे.</p><a href='/'>परत जा</a>"

        StrategyClass, strategy_display_name = STRATEGIES.get(selected_strategy_key)
        timeframe_display_name = TIMEFRAMES.get(timeframe)
        if not StrategyClass:
            return "<h1>Error</h1><p>अवैध स्ट्रॅटेजी निवडली.</p><a href='/'>परत जा</a>"
        
        # --- बॅकटेस्टिंग प्रक्रिया ---
        initial_capital = 100000.0
        from_date = datetime(2021, 1, 1)
        to_date = datetime.now()
        
        data_df = yf.Ticker(stock_name).history(start=from_date, end=to_date, interval=timeframe)
        if data_df.empty: 
            return f"<h1>Error</h1><p>'{stock_name}' साठी डेटा सापडला नाही. कृपया स्टॉकचे नाव (उदा. RELIANCE.NS) तपासा.</p><a href='/'>परत जा</a>"
        
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(initial_capital)
        cerebro.adddata(data)
        cerebro.addstrategy(StrategyClass)
        cerebro.broker.setcommission(commission=0.002)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        results = cerebro.run()
        
        final_capital = cerebro.broker.getvalue()
        pnl = final_capital - initial_capital

        # --- Plotly वापरून इंटरॅक्टिव्ह चार्ट तयार करणे ---
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], low=data_df['Low'], close=data_df['Close'], name='Price'))
        
        trade_analysis = results[0].analyzers.trade_analyzer.get_analysis()
        buy_dates = [trade.open_datetime() for trade in trade_analysis.values()]
        sell_dates = [trade.close_datetime() for trade in trade_analysis.values() if not trade.is_open]
        
        # Ensure dates are in dataframe index before trying to access them
        buy_dates_in_df = [d for d in buy_dates if d in data_df.index]
        sell_dates_in_df = [d for d in sell_dates if d in data_df.index]

        if buy_dates_in_df:
            fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, mode='markers', marker=dict(color='green', size=10, symbol='triangle-up'), name='Buy'))
        if sell_dates_in_df:
            fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, mode='markers', marker=dict(color='red', size=10, symbol='triangle-down'), name='Sell'))
        
        fig.update_layout(title=f'{stock_name} - {strategy_display_name}', xaxis_title='Date', yaxis_title='Price', xaxis_rangeslider_visible=True)
        chart_html = fig.to_html(full_html=False)
        # --- चार्ट तयार करणे समाप्त ---

        return render_template('result.html', 
                               stock=stock_name,
                               strategy_name=strategy_display_name,
                               timeframe=timeframe_display_name,
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}',
                               pnl=f'{pnl:,.2f}',
                               chart_html=chart_html)
    except Exception as e:
        print(f"एक अनपेक्षित एरर आला: {e}")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे: {e}</p>"
```

### **पायरी २: तुमचा कोड GitHub वर अपडेट करा**

आता हा अंतिम बदल तुमच्या GitHub पेजवर पाठवा.

1.  तुमच्या `MyWebApp` फोल्डरमध्ये **टर्मिनल (PowerShell)** उघडा.
2.  आता खालील **तीनही कमांड्स याच क्रमाने** चालवा:

    ```bash
    git add .
    ```
    ```bash
    git commit -m "अंतिम उपाय: 400 Bad Request एरर दुरुस्त केला"
    ```
    ```bash
    git push
    

