import alpaca_trade_api as tradeapi
import pandas as pd

from datetime import timedelta, datetime
from alpaca_trade_api.rest import TimeFrame

def setAlpacaApi(api_key, secret_key):
    global api
    api = tradeapi.REST(
        key_id=api_key,
        secret_key=secret_key,
        base_url='https://paper-api.alpaca.markets',
        api_version='v2'
    )

def getAccountInfo():

    # Get our account information.
    account = api.get_account()

    # Check if our account is restricted from trading.
    if account.trading_blocked:
        print('Account is currently restricted from trading.')

    # Check how much money we can use to open new positions.
    print('${} is available as buying power.'.format(account.buying_power))

def getGainAndLoss():
    account = api.get_account()

    # Check our current balance vs. our balance at the last market close
    balance_change = float(account.equity) - float(account.last_equity)
    print(f'Today\'s portfolio balance change: ${balance_change}')

def getHistoricalPrice(sym, time, limit):
    try:
        start = pd.Timestamp('now').date()
        end = pd.Timestamp('now').date()
        bars = api.get_bars(sym, time,
            limit=limit, adjustment='raw')
        if len(bars) == 0:
            bars = api.get_bars(sym, time, start=start, end=end,
                limit=limit, adjustment='raw')
        return bars
    except Exception as e:
        print("getHistoricalPrice error {}".format(e))
        return []

def getCurrentPrice(sym):
    bars = getHistoricalPrice(sym, TimeFrame.Minute, 1)
    if len(bars) == 0:
        return -1
    return bars[-1].c

def getMarketOpenPrice(sym):
    bars = getHistoricalPrice(sym, TimeFrame.Day, 1)
    if len(bars) == 0:
        return -1
    openPrice = bars[0].o
    return openPrice


def getListOfAssets():
    active_assets = api.list_assets(status='active')

    # Filter the assets down to just those on NASDAQ.
    nasdaq_assets = [a for a in active_assets if a.exchange == 'NASDAQ']
    print(nasdaq_assets)

def place_new_market_order(sym, qty, side):
    api.submit_order(
        symbol=sym,
        qty=qty,
        side=side,
        type='market',
        time_in_force='gtc'
    )


def getMarketCalendar(date):
    clock = api.get_clock()

    # Check when the market was open on Dec. 1, 2018
    calendar = api.get_calendar(start=date, end=date)[0]
    return calendar

def getPercentChange(sym, time, limit):
    bars = getHistoricalPrice(sym, time, limit)
    if len(bars) == 0:
        return [0, -1]
    open_price = bars[0].o
    close_price = bars[-1].c
    percent_change = (close_price - open_price) / open_price * 100
    return [percent_change, close_price]

def getWeeklyChange(sym):
    return getPercentChange(sym, TimeFrame.Day, 5)

def getDailyChange(sym):
    return getPercentChange(sym, TimeFrame.Hour, 24)