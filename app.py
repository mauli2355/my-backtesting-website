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

# आपल्या इतर Python फाईल्समधून आवश्यक गोष्टी इम्पोर्ट करणे
from strategies import STRATEGIES
from backtesting_engine import run_backtest
from plotting import create_plot

app = Flask(__name__)

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
        
        # ✅ येथे आपण backtesting_engine.py मधील आपले फंक्शन वापरत आहोत
        final_capital, trade_analysis, trend_analysis = run_backtest(data, StrategyClass, initial_capital)
        pnl = final_capital - initial_capital
        
        # ✅ येथे आपण plotting.py मधील आपले फंक्शन वापरत आहोत
        chart_html = create_plot(data_df, trade_analysis, stock_name, strategy_display_name)

        # --- ✅ हा आहे अंतिम आणि अचूक उपाय ---
        # येथे आपण 'trend_analysis' ची माहिती result.html कडे पाठवत आहोत
        return render_template('result.html', 
                               stock=stock_name, 
                               strategy_name=strategy_display_name,
                               timeframe=timeframe_display_name, 
                               initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}', 
                               pnl=f'{pnl:,.2f}',
                               chart_html=chart_html,
                               trend_analysis=trend_analysis  # <-- ही ओळ महत्त्वाची आहे
                               )
    except Exception:
        error_details = traceback.format_exc()
        print("----------- DETAILED ERROR -----------")
        print(error_details)
        print("------------------------------------")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे. कृपया काही वेळाने पुन्हा प्रयत्न करा.</p>"