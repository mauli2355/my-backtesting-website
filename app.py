from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# =====================
# STRATEGY
# =====================
class EmaCross(bt.Strategy):
    params = (('fast_ema', 9), ('slow_ema', 20),)

    def __init__(self):
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.params.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.params.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
        self.signals = []

    def next(self):
        dt = self.data.datetime.datetime(0)
        price = self.data.close[0]
        if not self.position:
            if self.crossover > 0:  # BUY
                self.buy()
                self.signals.append(("BUY", dt, price))
        else:
            if self.crossover < 0:  # SELL
                self.sell()
                self.signals.append(("SELL", dt, price))

# =====================
# ROUTES
# =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        stock_name = request.form.get('stock_name')
        # ✅ आपण HTML मधून multiple strategies आणि timeframe काढून टाकले आहेत,
        # त्यामुळे हा कोड सध्या फक्त एका स्ट्रॅटेजीसाठी काम करेल.
        timeframe = "1d" # सध्या फक्त डेली टाइमफ्रेम

        initial_capital = 100000.0

        # 📌 Safe data download
        try:
            # ✅ जास्त डेटा मिळवण्यासाठी आपण start date वापरू
            data_df = yf.download(stock_name, start="2021-01-01", interval=timeframe, progress=False, threads=False)
        except Exception as yf_err:
            return f"<h1>Yahoo Finance Error</h1><p>डेटा मिळाला नाही: {yf_err}</p><a href='/'>परत जा</a>"

        # 📌 Check if enough candles
        if data_df.empty or len(data_df) < 50:
            return f"<h1>Error</h1><p>'{stock_name}' ({timeframe}) साठी पुरेसा डेटा सापडला नाही. कृपया timeframe बदलून पाहा.</p><a href='/'>परत जा</a>"

        # Backtrader setup
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(initial_capital)
        
        # ✅ Cerebro मध्ये डेटा जोडला (सर्वात महत्त्वाची दुरुस्ती)
        cerebro.adddata(data)
        
        cerebro.addstrategy(EmaCross)
        
        # ✅ cerebro.run() एका लिस्टमध्ये स्ट्रॅटेजी परत करते
        results = cerebro.run()
        strategy_instance = results[0] # पहिली स्ट्रॅटेजी मिळवणे

        signals = strategy_instance.signals
        final_capital = cerebro.broker.getvalue()
        pnl = final_capital - initial_capital

        # =====================
        # Plotly चार्ट
        # =====================
        fig = go.Figure(data=[go.Candlestick(
            x=data_df.index,
            open=data_df['Open'],
            high=data_df['High'],
            low=data_df['Low'],
            close=data_df['Close'],
            name="Candles"
        )])

        data_df['EMA9'] = data_df['Close'].ewm(span=9, adjust=False).mean()
        data_df['EMA20'] = data_df['Close'].ewm(span=20, adjust=False).mean()
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA9'], mode='lines', name='EMA 9', line=dict(color='cyan')))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA20'], mode='lines', name='EMA 20', line=dict(color='orange')))

        buy_signals = [s for s in signals if s[0] == "BUY"]
        sell_signals = [s for s in signals if s[0] == "SELL"]

        fig.add_trace(go.Scatter(x=[s[1] for s in buy_signals], y=[s[2] for s in buy_signals], mode="markers", marker=dict(symbol="triangle-up", color="lime", size=12), name="BUY Signal"))
        fig.add_trace(go.Scatter(x=[s[1] for s in sell_signals], y=[s[2] for s in sell_signals], mode="markers", marker=dict(symbol="triangle-down", color="red", size=12), name="SELL Signal"))

        fig.update_layout(title=f"{stock_name} ({timeframe}) EMA Crossover Backtest", xaxis_rangeslider_visible=False, template="plotly_dark", height=700)
        chart_html = fig.to_html(full_html=False)

        return render_template('result.html',
                               stock=stock_name,
                               timeframe=timeframe,
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}',
                               pnl=f'{pnl:,.2f}',
                               chart_html=chart_html)

    except Exception as e:
        print(f"Error: {e}")
        return f"<h1>Application Error</h1><p>{e}</p>"

# टीप: हा कोड तुमच्या जुन्या index.html आणि result.html सोबत काम करेल.
# फक्त खात्री करा की index.html मध्ये 'timeframe' आणि 'strategy' चे ड्रॉप-डाउन नाहीत.
```

### **पायरी २: तुमचा कोड GitHub वर अपडेट करा**

आता हा अंतिम बदल तुमच्या GitHub पेजवर पाठवा.

1.  तुमच्या `MyWebApp` फोल्डरमध्ये **टर्मिनल (PowerShell)** उघडा.
2.  आता खालील **तीनही कमांड्स याच क्रमाने** चालवा:

    ```bash
    git add .
    ```
    ```bash
    git commit -m "अंतिम उपाय: Backtrader डेटा एरर दुरुस्त केला"
    ```
    ```bash
    git push
    

