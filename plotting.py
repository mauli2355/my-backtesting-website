import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Matplotlib backend setting Agg for headless servers
import matplotlib
matplotlib.use('Agg')

def create_plot(data_df, trade_analysis, stock_name, strategy_name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, subplot_titles=(f'{stock_name} Chart', 'Volume'), 
                        row_width=[0.2, 0.7])

    fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], 
                                 low=data_df['Low'], close=data_df['Close'], name='Price'), 
                  row=1, col=1)

    fig.add_trace(go.Bar(x=data_df.index, y=data_df['Volume'], name='Volume'), row=2, col=1)

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
        fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, 
                                 mode='markers', marker=dict(color='green', size=10, symbol='triangle-up'), 
                                 name='Buy'), row=1, col=1)
    if sell_dates_in_df:
        fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, 
                                 mode='markers', marker=dict(color='red', size=10, symbol='triangle-down'), 
                                 name='Sell'), row=1, col=1)
    
    fig.update_layout(title_text=f'{stock_name} - {strategy_name}', template='plotly_dark',
                      xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig.to_html(full_html=False)