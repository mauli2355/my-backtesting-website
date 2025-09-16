from flask import Flask, render_template, request, session, redirect, url_for
import yfinance as yf
from datetime import datetime
import backtrader as bt
import traceback
import os
import pandas as pd

from strategies import STRATEGIES
from backtesting_engine import run_backtest
from plotting import create_plot

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# स्टॉकची लिस्ट लोड करणे
try:
    nse_stocks_df = pd.read_csv('nse_stocks.csv')
except FileNotFoundError:
    nse_stocks_df = pd.DataFrame(columns=['SYMBOL', 'NAME OF COMPANY'])

TIMEFRAMES = {
    '5m': "5 Minutes", '15m': "15 Minutes", '30m': "30 Minutes",
    '1h': "1 Hour", '1d': "Daily", '1wk': "Weekly", '1mo': "Monthly"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/strategies')
def strategies_page():
    return render_template('strategies_page.html')

@app.route('/screener')
def screener_page():
    return render_template('screener_page.html')
    
@app.route('/search')
def search():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify([])
    matches = nse_stocks_df[nse_stocks_df['SYMBOL'].str.contains(query, na=False)].head(10)
    return jsonify(matches.to_dict(orient='records'))

@app.route('/backtest', methods=['POST'])
def backtest():
    try:
        stock_name = request.form.get('stock_name')
        if not (stock_name.endswith('.NS') or stock_name.endswith('.BO')):
            stock_name += '.NS'
        
        selected_strategy_key = request.form.get('strategy')
        timeframe = request.form.get('timeframe')
        indicators_to_plot = request.form.getlist('indicators')

        # येथे कोणताही बदल नाही, हा कोड बरोबर आहे
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
        
        chart_html = create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_display_name, StrategyClass.params)

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