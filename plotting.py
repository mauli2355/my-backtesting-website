import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_plot(data_df, trade_analysis, stock_name, strategy_name):
    # दोन भागांचा चार्ट तयार करणे (वर किंमत, खाली व्हॉल्यूम)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{stock_name} Chart', 'Volume'), 
                        row_heights=[0.8, 0.2])

    # १. Candlestick चार्ट
    fig.add_trace(go.Candlestick(x=data_df.index, open=data_df['Open'], high=data_df['High'], 
                                 low=data_df['Low'], close=data_df['Close'], name='Price'), 
                  row=1, col=1)

    # २. व्हॉल्यूम बार
    fig.add_trace(go.Bar(x=data_df.index, y=data_df['Volume'], name='Volume', marker_color='rgba(255,255,255,0.3)'), row=2, col=1)

    # --- ✅ हा आहे अंतिम आणि अचूक उपाय ---
    # ३. EMA लाईन्स चार्टवर काढणे
    # आपण EMA व्हॅल्यूज DataFrame मध्ये तयार करूया
    data_df['ema_fast'] = data_df['Close'].ewm(span=9, adjust=False).mean()
    data_df['ema_slow'] = data_df['Close'].ewm(span=20, adjust=False).mean()

    fig.add_trace(go.Scatter(x=data_df.index, y=data_df['ema_fast'], mode='lines', 
                             name='Fast EMA (9)', line=dict(color='cyan', width=1.5)), 
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=data_df.index, y=data_df['ema_slow'], mode='lines', 
                             name='Slow EMA (20)', line=dict(color='orange', width=1.5)), 
                  row=1, col=1)

    # ४. खरेदी/विक्रीचे सिग्नल (Buy/Sell Markers) चार्टवर दाखवणे
    buy_dates, sell_dates = [], []
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
                                 mode='markers', marker=dict(color='#2ecc71', size=12, symbol='triangle-up', line=dict(width=1, color='DarkSlateGrey')), 
                                 name='Buy Signal'), row=1, col=1)
    if sell_dates_in_df:
        fig.add_trace(go.Scatter(x=sell_dates_in_df, y=data_df.loc[sell_dates_in_df]['High'] * 1.02, 
                                 mode='markers', marker=dict(color='#e74c3c', size=12, symbol='triangle-down', line=dict(width=1, color='DarkSlateGrey')), 
                                 name='Sell Signal'), row=1, col=1)
    
    # ५. चार्टला सुंदर बनवणे (TradingView सारखे)
    fig.update_layout(
        title_text=f'{stock_name} - {strategy_name}', 
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig.to_html(full_html=False)