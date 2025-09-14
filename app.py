# app.py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
from datetime import datetime
import random

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        stock_name = request.form['stock_name']
        initial_capital = 100000.0
        from_date = datetime(2021, 1, 1)
        to_date = datetime.now()
        
        data_df = yf.Ticker(stock_name).history(start=from_date, end=to_date)
        
        if data_df.empty:
            return f"<h1>Error</h1><p>'{stock_name}' साठी कोणताही डेटा सापडला नाही. कृपया स्टॉकचे नाव तपासा.</p><a href='/'>परत जा</a>"
            
        data = bt.feeds.PandasData(dataname=data_df)

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(initial_capital)
        cerebro.adddata(data)
        cerebro.addstrategy(EmaCrossWithCandleStop)
        cerebro.broker.setcommission(commission=0.002)
        cerebro.run()
        
        final_capital = cerebro.broker.getvalue()
        pnl = final_capital - initial_capital

        plot_path = 'static/plot.png'
        figs = cerebro.plot(style='candlestick', barup='green', bardown='red', iplot=False)
        figs[0][0].savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close('all')

        return render_template('result.html', 
                               stock=stock_name,
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}',
                               pnl=f'{pnl:,.2f}',
                               random_int=random.randint(1,1000)
                               )
    except Exception as e:
        print(f"एक अनपेक्षित एरर आला: {e}")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे: {e}</p>"