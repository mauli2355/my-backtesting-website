# app.py

import matplotlib
matplotlib.use('Agg') # महत्वाचा बदल

from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
from datetime import datetime
import random # To prevent image caching

# Flask ॲप सुरू करणे
app = Flask(__name__)

# --- तुमचा बॅकटेस्टिंगचा कोड (स्ट्रॅटेजी) ---
class EmaCrossWithCandleStop(bt.Strategy):
    params = (('fast_ema', 9), ('slow_ema', 20))
    def __init__(self):
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.params.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.params.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
        self.stop_loss_order = None
        self.signal_candle_low = None
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.exectype == bt.Order.Stop: self.stop_loss_order = None
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
                self.signal_candle_low = self.data.low[0]
        else:
            if self.stop_loss_order is None:
                stop_price = self.signal_candle_low
                self.stop_loss_order = self.sell(exectype=bt.Order.Stop, price=stop_price)
            if self.crossover < 0:
                if self.stop_loss_order: self.cancel(self.stop_loss_order)
                self.close()
# --- स्ट्रॅटेजीचा कोड समाप्त ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/backtest', methods=['POST'])
def backtest():
    stock_name = request.form['stock_name']
    
    initial_capital = 100000.0
    from_date = datetime(2021, 1, 1)
    to_date = datetime.now()
    
    # --- नवीन आणि सुधारित कोड (Error Handling) ---
    try:
        # डेटा डाउनलोड करण्याचा प्रयत्न करणे
        data_df = yf.Ticker(stock_name).history(start=from_date, end=to_date)
        
        # जर डेटा मिळाला नाही, तर एरर देणे
        if data_df.empty:
            return f"<h1>Error</h1><p>'{stock_name}' साठी कोणताही डेटा सापडला नाही. कृपया स्टॉकचे नाव (उदा. RELIANCE.NS) तपासा आणि पुन्हा प्रयत्न करा.</p><a href='/'>परत जा</a>"
            
        data = bt.feeds.PandasData(dataname=data_df)
    except Exception as e:
        # इतर कोणताही एरर आल्यास, तो दाखवणे
        return f"<h1>Error</h1><p>डेटा मिळवताना एरर आला: {e}</p><a href='/'>परत जा</a>"
    # --- एरर हँडलिंग समाप्त ---

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_capital)
    cerebro.adddata(data)
    cerebro.addstrategy(EmaCrossWithCandleStop)
    cerebro.broker.setcommission(commission=0.002)
    cerebro.run()
    
    final_capital = cerebro.broker.getvalue()
    pnl = final_capital - initial_capital

    plot_path = 'static/plot.png'
    cerebro.plot(style='candlestick', barup='green', bardown='red', iplot=False, savefig=True, figpath=plot_path)

    return render_template('result.html', 
                           stock=stock_name,
                           initial_cap=f'{initial_capital:,.2f}',
                           final_cap=f'{final_capital:,.2f}',
                           pnl=f'{pnl:,.2f}',
                           random_int=random.randint(1,1000)
                           )