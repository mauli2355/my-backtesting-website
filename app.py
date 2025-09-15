from flask import Flask, render_template, request
import backtrader as bt
import yfinance as yf
from datetime import datetime
import plotly.graph_objs as go

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
        stock_name = request.form['stock_name']
        timeframe = request.form['timeframe']

        # TradingView-style interval → yfinance mapping
        tf_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "60m",
            "4h": "4h",   # Yahoo supports directly
            "1d": "1d",
            "1w": "1wk",
            "1mo": "1mo"
        }
        interval = tf_map.get(timeframe, "1d")

        initial_capital = 100000.0

        # 📌 Download data with proper period
        if interval == "1m":
            data_df = yf.download(stock_name, period="7d", interval=interval)
        elif interval in ["5m", "15m", "30m", "60m", "90m", "1h", "4h"]:
            data_df = yf.download(stock_name, period="60d", interval=interval)
            # fallback if 4h empty
            if data_df.empty and interval == "4h":
                data_df = yf.download(stock_name, period="60d", interval="60m")
                timeframe = "1h (fallback from 4h)"
        else:
            data_df = yf.download(stock_name, start="2023-01-01", interval=interval)

        # 📌 Check if enough candles
        if data_df.empty or len(data_df) < 50:
            return f"<h1>Error</h1><p>'{stock_name}' ({timeframe}) साठी पुरेसा डेटा सापडला नाही. कृपया timeframe बदलून पाहा.</p><a href='/'>परत जा</a>"

        # Backtrader setup
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(initial_capital)
        cerebro.addstrategy(EmaCross)
        strategies = cerebro.run()

        if not strategies:
            return "<h1>Error</h1><p>Strategy run करता आला नाही, डेटा खूप कमी आहे.</p><a href='/'>परत जा</a>"

        signals = strategies[0].signals
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

        # EMA जोडणे
        data_df['EMA9'] = data_df['Close'].ewm(span=9, adjust=False).mean()
        data_df['EMA20'] = data_df['Close'].ewm(span=20, adjust=False).mean()

        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA9'], mode='lines',
                                 name='EMA 9', line=dict(color='cyan')))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA20'], mode='lines',
                                 name='EMA 20', line=dict(color='orange')))

        # Buy/Sell markers
        buy_signals = [s for s in signals if s[0] == "BUY"]
        sell_signals = [s for s in signals if s[0] == "SELL"]

        fig.add_trace(go.Scatter(
            x=[s[1] for s in buy_signals],
            y=[s[2] for s in buy_signals],
            mode="markers",
            marker=dict(symbol="triangle-up", color="lime", size=12),
            name="BUY Signal"
        ))

        fig.add_trace(go.Scatter(
            x=[s[1] for s in sell_signals],
            y=[s[2] for s in sell_signals],
            mode="markers",
            marker=dict(symbol="triangle-down", color="red", size=12),
            name="SELL Signal"
        ))

        # Layout
        fig.update_layout(
            title=f"{stock_name} ({timeframe}) EMA Crossover Backtest",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=700,
            plot_bgcolor="#0d1117",
            paper_bgcolor="#0d1117",
            font=dict(color="white")
        )

        chart_html = fig.to_html(full_html=False)

        return render_template('result.html',
                               stock=stock_name,
                               timeframe=timeframe,
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}',
                               pnl=f'{pnl:,.2f}',
                               chart_html=chart_html
                               )

    except Exception as e:
        print(f"Error: {e}")
        return f"<h1>Application Error</h1><p>{e}</p>"


if __name__ == "__main__":
    app.run(debug=True)
