from flask import Flask, render_template, request
import yfinance as yf
from datetime import datetime
import backtrader as bt
import traceback

from strategies import STRATEGIES
from backtesting_engine import run_backtest # यात कोणताही बदल नाही
from plotting import create_plot

app = Flask(__name__)
# ... (बाकीचा कोड जसाच्या तसा आहे) ...
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

        StrategyClass, strategy_display_name = STRATEGIES.get(selected_strategy_key)
        timeframe_display_name = TIMEFRAMES.get(timeframe)
        
        initial_capital = 100000.0
        from_date = datetime(1996, 1, 1)
        to_date = datetime.now()

        if timeframe in ['5m', '15m', '30m', '1h']:
            data_df = yf.Ticker(stock_name).history(period="60d", interval=timeframe)
        else:
            data_df = yf.Ticker(stock_name).history(start=from_date, end=to_date, interval=timeframe)
        
        min_required_data = 200 # Golden Cross साठी
        if data_df.empty or len(data_df) < min_required_data: 
            return f"<h1>Error</h1><p>'{stock_name}' ({timeframe_display_name}) साठी पुरेसा डेटा सापडला नाही.</p>"
        
        data = bt.feeds.PandasData(dataname=data_df)
        
        # run_backtest आता स्ट्रॅटेजीचा इंस्टन्स परत करेल
        final_capital, trade_analysis, trend_analysis, strategy_instance = run_backtest(data, StrategyClass, initial_capital)
        pnl = final_capital - initial_capital
        
        # आपण आता स्ट्रॅटेजीमधून थेट सिग्नल घेत आहोत
        buy_signals = strategy_instance.buy_signals
        sell_signals = strategy_instance.sell_signals
        
        chart_html = create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_display_name)

        return render_template('result.html', 
                               stock=stock_name, strategy_name=strategy_display_name,
                               timeframe=timeframe_display_name, initial_cap=f'{initial_capital:,.2f}',
                               final_cap=f'{final_capital:,.2f}', pnl=f'{pnl:,.2f}',
                               chart_html=chart_html, trend_analysis=trend_analysis)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"----------- DETAILED ERROR -----------\n{error_details}------------------------------------")
        return f"<h1>Application Error</h1><p>एक अनपेक्षित एरर आला आहे: {e}</p>"