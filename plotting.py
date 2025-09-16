import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

def create_plot(data_df, buy_signals, sell_signals, stock_name, strategy_name, indicators_to_plot):
    
    # इंडिकेटर्सनुसार सब-प्लॉटची संख्या ठरवणे
    num_subplots = 1 + len([ind for ind in ['rsi', 'macd'] if ind in indicators_to_plot])
    row_heights = [0.7] + [0.3] * (num_subplots - 1)
    
    fig = make_subplots(rows=num_subplots, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=row_heights)

    # Candlestick Chart
    fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], 
                                 low=data_df['Low'], close=data_df['Close'], name='Price'), 
                  row=1, col=1)

    # निवडलेले इंडिकेटर्स काढणे
    subplot_num = 2
    if 'ema' in indicators_to_plot:
        data_df.ta.ema(length=9, append=True, col_names=('EMA_9',))
        data_df.ta.ema(length=20, append=True, col_names=('EMA_20',))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA_9'], mode='lines', name='EMA 9', line=dict(color='cyan', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['EMA_20'], mode='lines', name='EMA 20', line=dict(color='orange', width=1.5)), row=1, col=1)
    
    if 'bbands' in indicators_to_plot:
        data_df.ta.bbands(length=20, append=True, col_names=('BBL_20', 'BBM_20', 'BBU_20', 'BBB_20', 'BBP_20'))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['BBU_20'], mode='lines', name='Upper Band', line=dict(color='rgba(255,255,255,0.4)', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['BBL_20'], mode='lines', name='Lower Band', fill='tonexty', fillcolor='rgba(255,255,255,0.1)', line=dict(color='rgba(255,255,255,0.4)', width=1)), row=1, col=1)

    if 'supertrend' in indicators_to_plot:
        data_df.ta.supertrend(length=7, multiplier=3, append=True, col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['SUPERTl_7_3.0'], mode='lines', name='SuperTrend Long', line=dict(color='green', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['SUPERTs_7_3.0'], mode='lines', name='SuperTrend Short', line=dict(color='red', width=2)), row=1, col=1)
        
    if 'rsi' in indicators_to_plot:
        data_df.ta.rsi(length=14, append=True, col_names=('RSI_14',))
        fig.add_trace(go.Scatter(x=data_df.index, y=data_df['RSI_14'], mode='lines', name='RSI'), row=subplot_num, col=1)
        fig.update_yaxes(title_text="RSI", row=subplot_num, col=1)
        subplot_num += 1

    # Buy/Sell Signals
    buy_dates_in_df = [d for d in buy_signals if d in data_df.index]
    sell_dates_in_df = [d for d in sell_signals if d in data_df.index]

    if buy_dates_in_df:
        fig.add_trace(go.Scatter(x=buy_dates_in_df, y=data_df.loc[buy_dates_in_df]['Low'] * 0.98, mode='markers', marker=dict(color='#2ecc71', size=12, symbol='triangle-up'), name='Buy Signal'), row=1, col=1)
    if sell_dates_in_df:
        fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, mode='markers', marker=dict(color='#e74c3c', size=12, symbol='triangle-down'), name='Sell Signal'), row=1, col=1)
    
    fig.update_layout(title_text=f'{stock_name} - {strategy_name}', template='plotly_dark', xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig.to_html(full_html=False, config={'scrollZoom': True})