from teleg_cmd import ActionAddToWatchList, chooseConflictSym
import requests
import json
import virtual_currency
from datetime import datetime, timedelta
from pytz import timezone

STOCK = 0
VIRTUAL_CURRENCY = 1

def getDetail(symbol, update, type=-1):
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v2/get-analysis"
    querystring = {"symbol": symbol}
    headers = {
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
        'x-rapidapi-key': "7e6fdc6e15msh194a1f2f00930e8p1a3e73jsn3594fd04b213"
    }

    count = 0
    while(count < 3):
        count += 1
        response = requests.request("GET", url, headers=headers, params=querystring)
        if response.status_code == 200:
            res_json = json.loads(response.text)
            if len(res_json) == 0:
                return None
            price = res_json["price"]
            if type == -1 and validStockAndVirtual(symbol, price):
                chooseConflictSym(update, symbol, ActionAddToWatchList)
                return None

            if price["longName"] == None or type == VIRTUAL_CURRENCY:
                [percentage, nowPrice] = virtual_currency.getDailyChange(symbol)
                isExist = False
                if nowPrice != -1:
                    isExist = True
                    detail = {
                        "name":symbol,
                        "symbol":symbol,
                        "currentPrice":nowPrice,
                        "DailyChange":0,
                        "isExist":isExist,
                        "type": VIRTUAL_CURRENCY
                    }
                    return detail
            else:
                isExist = True
                nowPrice = res_json["summaryDetail"]["ask"]["raw"]

            detail = {
                "name":price["longName"],
                "symbol":price["symbol"],
                "currentPrice":nowPrice,
                "DailyChange":0,
                "isExist":isExist,
                "type": STOCK
            }
            return detail

    return {"isExist": False}

def validStockAndVirtual(sym, price):
    [percentage, nowPrice] = virtual_currency.getDailyChange(sym)
    return nowPrice != -1 and price["longName"] != None

def getPrice(symbol):
    res_json = {}
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v2/get-analysis"
    querystring = {"symbol": symbol}
    headers = {
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
        'x-rapidapi-key': "7e6fdc6e15msh194a1f2f00930e8p1a3e73jsn3594fd04b213"
    }

    count = 1
    while(count<3):
        count+=1
        response = requests.request("GET", url, headers=headers, params=querystring)
        if response.status_code == 200:
            res_json = json.loads(response.text)
            break

    if "summaryDetail" in res_json:
        price = res_json["summaryDetail"]["ask"]["raw"]
    else:
        price = -1
    #if "financialData" in res_json:
    #    price = res_json["financialData"]["currentPrice"]["raw"]
    #else:
    #    price = -1
    return price

def getValidation(detail):
    return detail["isExist"]