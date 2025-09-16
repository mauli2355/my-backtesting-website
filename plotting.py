import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_name, strategy_params):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{stock_name} Chart', 'Volume'), 
                        row_heights=[0.8, 0.2])

    fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], 
                                 low=data_df['Low'], close=data_df['Close'], name='Price'), 
                  row=1, col=1)

    fig.add_trace(go.Bar(x=data_df.index, y=data_df['Volume'], name='Volume', marker_color='rgba(90, 100, 150, 0.5)'), row=2, col=1)
    
    # स्ट्रॅटेजीनुसार इंडिकेटर्स काढणे
    if 'ema_cross' in strategy_name.lower():
        data_df['ema_fast'] = data_df['Close'].ewm(span=strategy_params.get('fast_ema', 9), adjust=False).mean()
        data_df['ema_slow'] = data_df['Close'].ewm(span=strategy_params.get('slow_ema', 20), adjust=False).mean()
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['ema_fast'], mode='lines', name='Fast EMA', line=dict(color='cyan', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['ema_slow'], mode='lines', name='Slow EMA', line=dict(color='orange', width=1.5)), row=1, col=1)
    elif 'golden_cross' in strategy_name.lower():
        data_df['sma_fast'] = data_df['Close'].rolling(window=strategy_params.get('fast_sma', 50)).mean()
        data_df['sma_slow'] = data_df['Close'].rolling(window=strategy_params.get('slow_sma', 200)).mean()
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['sma_fast'], mode='lines', name='Fast SMA', line=dict(color='cyan', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['sma_slow'], mode='lines', name='Slow SMA', line=dict(color='orange', width=1.5)), row=1, col=1)

    buy_dates_in_df = [d for d in buy_signals if d in data_df.index]
    sell_dates_in_df = [d for d in sell_signals if d in data_df.index]

    if buy_dates_in_df:
        fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, 
                                 mode='markers', marker=dict(color='#2ecc71', size=12, symbol='triangle-up', line=dict(width=1, color='DarkSlateGrey')), 
                                 name='Buy Signal'), row=1, col=1)
    if sell_dates_in_df:
        fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, 
                                 mode='markers', marker=dict(color='#e74c3c', size=12, symbol='triangle-down', 
                                 name='Sell Signal'), row=1, col=1)
    
    fig.update_layout(title_text=f'{stock_name} - {strategy_name}', template='plotly_dark',
                      xaxis_rangeslider_visible=True,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig.to_html(full_html=False, config={'scrollZoom': True})