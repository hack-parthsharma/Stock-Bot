import req_cmd
import local_cache
import teleg_cmd
import alpaca
import virtual_currency

from telegram import Bot
from telegram.ext import Updater
from telegram import InlineQueryResultArticle, InputTextMessageContent
from datetime import datetime, timedelta
from pytz import timezone, utc

import logging
import time
import threading

posChange5Percent = 0
posChange10Percent = 1
posChange15Percent = 2
posChange20Percent = 3
posChange25Percent = 4
posChange30Percent = 5
posChange35Percent = 6
posChange40Percent = 7
posChange45Percent = 8
posChange50Percent = 9


class Stock_bot:
    STCOK = 0
    VIRTUAL_CURRENCY = 1

    def __init__(self, token, alpaca_api_key, alpaca_secrete_key, xcurrency_key):
        self.symCachePath = {}
        self.dailyReport = {}
        self.chatIdCachePath = "./chat_id"
        self.initTelegram(token)
        self.initAlpaca(alpaca_api_key, alpaca_secrete_key, xcurrency_key)
        self.initLogging()
        self.initCache()
        self.initTime()

    def initTelegram(self, token):
        teleg_cmd.updater = Updater(token=token, use_context=True)
        teleg_cmd.dispatcher = teleg_cmd.updater.dispatcher
        teleg_cmd.updater.start_polling()
        teleg_cmd.AddCommandHandler("add_to_watchlist", teleg_cmd.CommandAdd2WatchList)
        teleg_cmd.AddCommandHandler("remove_from_watchlist", teleg_cmd.CommandRemoveFromWatchList)
        teleg_cmd.AddCommandHandler("get_price", teleg_cmd.CommandGetPrice)
        teleg_cmd.AddCommandHandler("get_price_from_watchlist", teleg_cmd.CommandGetPriceFromWatchList)
        teleg_cmd.AddCommandHandler("show_the_watchlist", teleg_cmd.CommandShowWatchlist)
        teleg_cmd.AddInlineQueryHandler(teleg_cmd.InlineSearchForStock)
        teleg_cmd.AddCommandHandler("start", self.CommandStart)
        teleg_cmd.AddMessageHandler(self.MessageUnknowText)
        teleg_cmd.AddCallbackQueryHandler(self.CallbackStockPick)
        teleg_cmd.AddCommandHandler("enable_nofitication",
                                    self.CommandEnableNotification)
        teleg_cmd.AddCommandHandler("disable_nofitication_",
                                    self.CommandDisableNotification)
    def initAlpaca(self, alpaca_api_key, alpaca_secrete_key, xcurrency_key):
        alpaca.setAlpacaApi(alpaca_api_key, alpaca_secrete_key)
        virtual_currency.setVirtCurrenciesApi(xcurrency_key)

    def initCache(self):
        ids = self.__getLocalChatId()
        for id in ids:
            if id not in teleg_cmd.gChatId:
                teleg_cmd.gChatId.append(id)
            self.symCachePath[id] = "./sym-"+str(id)
            self.__getLocalSym(id)
            if id not in self.dailyReport:
                self.dailyReport[id] = {}
            for sym in teleg_cmd.gSym[id]:
                self.dailyReport[id][sym] = 0

    def initLogging(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        logging.Formatter.converter = self.__customTime
        self.logger = logging.getLogger("BotLogger")
        hdlr = logging.FileHandler("./log")
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)

    def initTime(self):
        th1 = threading.Thread(target=self.__dailyTimer)
        th1.start()

        sym2ChatId = {}
        for id in teleg_cmd.gSym:
            for sym in teleg_cmd.gSym[id]:
                if sym not in sym2ChatId:
                    sym2ChatId[sym] = []
                if id not in sym2ChatId[sym]:
                    sym2ChatId[sym].append(id)
        th2 = threading.Thread(target=self.watchVirtCurrenciesPriceTrend, args=(sym2ChatId,))
        th2.start()

    def watchStockPriceTrend(self, market_open, market_close, sym2ChatId):
        nyc = timezone('America/New_York')
        before_market_open = market_open - datetime.today().astimezone(nyc)
        self.logger.info("Serval hours before market open.")
        self.logger.info(before_market_open)
        while before_market_open.days >= 0 and before_market_open.seconds // 60 >= 60:
            time.sleep(60*60)
            before_market_open = market_open - datetime.today().astimezone(nyc)
        self.logger.info("Serval minutes before market open.")
        self.logger.info(before_market_open)
        while before_market_open.days >= 0 and before_market_open.seconds // 60 <= 60:
            time.sleep(1)
            before_market_open = market_open - datetime.today().astimezone(nyc)

        since_market_open = datetime.today().astimezone(nyc) - market_open
        self.logger.info("Market Opened")
        self.logger.info(since_market_open)
        if since_market_open.seconds // 60 <= 7:
            for sym in sym2ChatId:
                price = alpaca.getMarketOpenPrice(sym)
                for chat_id in sym2ChatId[sym]:
                    self.__updatePrice(chat_id, sym, price)
            for chat_id in teleg_cmd.gChatId:
                teleg_cmd.sendMessages(chat_id, "Market Opened!")
                teleg_cmd.mergeStocksPrint(chat_id, "Market Opened Price:\n")

        before_market_close = market_close - datetime.today().astimezone(nyc)
        while before_market_close.days >=0:
            time.sleep(300)
            self.print_price_change(sym2ChatId, Stock_bot.STCOK)
            before_market_close = market_close - datetime.today().astimezone(nyc)

        since_market_close = datetime.today().astimezone(nyc) - market_close
        self.logger.info("Market Closed")
        self.logger.info(since_market_close)
        if since_market_close.seconds // 60 <= 7:
            for sym in sym2ChatId:
                [change, price] = alpaca.getDailyChange(sym)
                for chat_id in sym2ChatId[sym]:
                    self.__updatePrice(chat_id, sym, price)
                    self.__updateChange(chat_id, sym, change)

            for chat_id in teleg_cmd.gChatId:
                message = "Market Closeed Price:\n"
                teleg_cmd.sendMessages(chat_id, "Market Closed!")
                #teleg_cmd.mergeStocksPrint(chat_id, "Market Closeed Price:\n")
                for each in teleg_cmd.gSym[chat_id]:
                    message += teleg_cmd.gSym[chat_id][each]["name"] + "(" + each + ") : $" + str(
                        teleg_cmd.gSym[chat_id][each]["currentPrice"]) + "  |  " + str(round(
                        teleg_cmd.gSym[chat_id][each]["DailyChange"], 3))
                    if teleg_cmd.gSym[chat_id][each]["DailyChange"] >= 0:
                        message += "% Up\n"
                    else:
                        message += "% Down\n"
                teleg_cmd.sendMessages(chat_id, message)
    
    def watchVirtCurrenciesPriceTrend(self, sym2ChatId):
        while True:
            time.sleep(300)
            self.print_price_change(sym2ChatId, Stock_bot.VIRTUAL_CURRENCY)

    def print_price_change(self, sym2ChatId, type):
        for sym in sym2ChatId:
            if teleg_cmd.gType[sym]["type"] != type:
                continue
            if teleg_cmd.gType[sym]["type"] ==  Stock_bot.STCOK:
                [change, price] = alpaca.getDailyChange(sym)
            else:
                [change, price] = virtual_currency.getDailyChange(teleg_cmd.gType[sym]["name"])
            if price == -1:
                continue
            for chat_id in sym2ChatId[sym]:
                self.__updatePrice(chat_id, sym, price)
                self.__updateChange(chat_id, sym, change)
                if abs(change) >= 50 and (self.dailyReport[chat_id][sym] ^ (1 << posChange50Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(？？？)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange50Percent)
                if abs(change) >= 45 and abs(change) < 50 and (self.dailyReport[chat_id][sym] ^ (1 << posChange45Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(？？)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange45Percent)
                if abs(change) >= 40 and abs(change) < 45 and (self.dailyReport[chat_id][sym] ^ (1 << posChange40Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(？)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange40Percent)
                elif abs(change) >= 35 and abs(change) < 40 and (self.dailyReport[chat_id][sym] ^ (1 << posChange35Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(炒你妈的股)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange35Percent)
                elif abs(change) >= 30 and abs(change) < 35 and (self.dailyReport[chat_id][sym] ^ (1 << posChange30Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(草)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange30Percent)
                elif abs(change) >= 25 and abs(change) < 30 and (self.dailyReport[chat_id][sym] ^ (1 << posChange25Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}(肯定是bug)'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange25Percent)
                elif abs(change) >= 20 and abs(change) < 25 and (self.dailyReport[chat_id][sym] ^ (1 << posChange20Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange20Percent)
                elif abs(change) >= 15 and abs(change) < 20 and (self.dailyReport[chat_id][sym] ^ (1 << posChange15Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange15Percent)
                elif abs(change) >= 10 and abs(change) < 15 and (self.dailyReport[chat_id][sym] ^ (1 << posChange10Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange10Percent)
                elif abs(change) >= 5 and abs(change) < 10 and (self.dailyReport[chat_id][sym] ^ (1 << posChange5Percent)) > self.dailyReport[chat_id][sym]:
                    message = 'Breaking: #{} moved {}% over the last day, current price is ${}'.format(sym, round(change,3), price)
                    teleg_cmd.sendMessages(chat_id, message)
                    self.dailyReport[chat_id][sym] ^= (1 << posChange5Percent)

    def showThePrice(self, update, sym):
        [stock_percentage, stock_price] = alpaca.getDailyChange(sym)
        [xcurrency_percentage, xcurrency_price] = virtual_currency.getDailyChange(sym)
        if stock_price != -1:
            if xcurrency_price != -1:
                teleg_cmd.chooseConflictSym(update, sym, teleg_cmd.ActionPrint)
                return
            else:
                price = stock_price
                percentage = stock_percentage
        else:
            if xcurrency_price != -1:
                price = xcurrency_price
                percentage = xcurrency_percentage
            else:
                teleg_cmd.sendMessages(update.effective_chat.id, "No such symbol {}".format(sym))
                return
        if sym in teleg_cmd.gSym[update.effective_chat.id]:
            teleg_cmd.sendMessages(update.effective_chat.id, "Current price of {} is ${}, moving {}%".format(sym, str(price), round(percentage,3)))
        else:
            teleg_cmd.sendMessages(update.effective_chat.id, "Current price of {} is ${}".format(sym, str(price)))
        self.__updatePrice(update.effective_chat.id, sym, price)

    def Add2WatchList(self, update, cur_sym, type=-1):
        chat_id = update.effective_chat.id
        print(teleg_cmd.gSym)
        sym, _ = self.get_real_symbol(cur_sym)
        detail = req_cmd.getDetail(sym, update, type)
        if detail == None:
            return False
        if cur_sym not in teleg_cmd.gSym[chat_id] or \
            (cur_sym in teleg_cmd.gSym[chat_id] and teleg_cmd.gSym[chat_id][cur_sym]["type"] != detail["type"]):
            if cur_sym not in self.dailyReport[chat_id]:
                self.dailyReport[chat_id][cur_sym] = 0
            if self.__validSym(detail):
                teleg_cmd.gSym[chat_id][cur_sym] = detail
                self.__write2LocalSym(chat_id, teleg_cmd.gSym)
                return True
            else:
                return False

    def RemoveFromWatchList(self, chat_id, sym):
        res = False
        if sym in teleg_cmd.gSym[chat_id]:
            res = True
            teleg_cmd.gSym[chat_id].pop(sym)
        self.__write2LocalSym(chat_id, teleg_cmd.gSym)
        return res

    def CommandStart(self, update, context):
        chat_id = update.effective_chat.id
        print(chat_id)
        self.symCachePath[chat_id] = "./sym-"+str(chat_id)
        self.__getLocalSym(chat_id)
        if chat_id not in teleg_cmd.gChatId:
            teleg_cmd.gChatId.append(chat_id)
            local_cache.writeToChatIdCache(self.chatIdCachePath, chat_id)
        teleg_cmd.sendMessages(update.effective_chat.id, "I'm ready!")

    def MessageUnknowText(self, update, context):
        chat_id = update.effective_chat.id
        if update.effective_user == None:
            return
        user_id = update.effective_user.id
        if user_id not in teleg_cmd.userStatus:
            teleg_cmd.sendMessages(chat_id, "You shouldn't reply other's query", reply_to_message_id=chat_id)
            return
        if not self.__isChatRegistered(chat_id):
            return
        if teleg_cmd.userStatus[user_id] == teleg_cmd.StatusAddToWatchList:
            if self.Add2WatchList(update, update.message.text):
                teleg_cmd.sendMessages(chat_id, update.message.text + " has been added to the watchlist.\n"
                                       + "The current price is $" + str(teleg_cmd.gSym[chat_id][update.message.text]["currentPrice"]))
            else:
                teleg_cmd.sendMessages(chat_id, update.message.text + " is in the watchlist or it's not a valid stock symbol.")
        elif teleg_cmd.userStatus[user_id] == teleg_cmd.StatusRemoveFromWatchList:
            if self.RemoveFromWatchList(chat_id, update.message.text):
                teleg_cmd.sendMessages(chat_id, update.message.text + " has been removed from the watchlist.")
            else:
                teleg_cmd.sendMessages(chat_id, "There is no " + update.message.text + " in the watchlist.")
        elif teleg_cmd.userStatus[user_id] == teleg_cmd.StatusGetPrice:
            self.showThePrice(update, update.message.text)

        teleg_cmd.userStatus[user_id] = teleg_cmd.StatusNone

    def CallbackStockPick(self, update, context):
        type = req_cmd.STOCK
        query = update.callback_query
        query_type, cur_sym, action = query.data.split(" ")
        query.edit_message_text(text="Selected symbol: {}".format(cur_sym))
        sym, type = self.get_real_symbol(cur_sym)

        if int(action) == teleg_cmd.ActionPrint:
            if int(query_type) == Stock_bot.STCOK:
                [percentage, price] = alpaca.getDailyChange(sym)
            else:
                [percentage, price] = virtual_currency.getDailyChange(sym)
            teleg_cmd.sendMessages(update.effective_chat.id, "Current price of {} is ${}, moving {}%".format(sym, str(price), round(percentage,3)))
            self.__updatePrice(update.effective_chat.id, sym, price)
        if int(action) == teleg_cmd.ActionAddToWatchList:
            self.Add2WatchList(update, cur_sym, type)

    def get_real_symbol(self, cur_sym):
        type = req_cmd.STOCK
        if "_" in cur_sym:
            sym, sym_type = cur_sym.split("_")
            if sym_type == "Stock":
                type = req_cmd.STOCK
            if sym_type == "Virtual":
                type = req_cmd.VIRTUAL_CURRENCY
        else:
            sym = cur_sym
        return sym, type

    def CommandEnableNotification(self, update, context):
        pass
        #chat_id = update.effective_chat.id
        #if chat_id not in teleg_cmd.gChatId:
        #    teleg_cmd.gChatId.append(chat_id)
        #    local_cache.writeToChatIdCache(self.chatIdCachePath, teleg_cmd.gChatId)

    def CommandDisableNotification(self, update, context):
        pass
        #chat_id = update.effective_chat.id
        #if chat_id in teleg_cmd.gChatId:
        #    teleg_cmd.gChatId.remove(chat_id)
        #    local_cache.overwriteToChatIdCache(self.chatIdCachePath, teleg_cmd.gChatId)

    def GetOpenStockInfo(self):
        t = time.time()

    def __validSym(self, detail):
        return req_cmd.getValidation(detail)

    def __getPrice(self, sym):
        return alpaca.getCurrentPrice(sym)

    def __getLocalSym(self, chat_id):
        sym = local_cache.readFromSymsCache(self.symCachePath[chat_id])
        if str(chat_id) in sym:
            teleg_cmd.gSym[chat_id] = sym[str(chat_id)]
            rewrite = 0
            for each_sym in teleg_cmd.gSym[chat_id]:
                if "type" not in teleg_cmd.gSym[chat_id][each_sym]:
                    teleg_cmd.gSym[chat_id][each_sym]["type"] = Stock_bot.STCOK
                    rewrite = 1
                if each_sym not in teleg_cmd.gType:
                    teleg_cmd.gType[each_sym] = teleg_cmd.gSym[chat_id][each_sym]
            if rewrite:
                self.__write2LocalSym(chat_id, teleg_cmd.gSym)
        else:
            teleg_cmd.gSym[chat_id] = {}

    def __getLocalChatId(self):
        ids = local_cache.readFromChatIdCache(self.chatIdCachePath)
        return ids

    def __write2LocalSym(self, chat_id, syms):
        local_cache.writeToSymsCache(self.symCachePath[chat_id], {chat_id:syms[chat_id]})

    def __isChatRegistered(self, chat_id):
        if chat_id not in teleg_cmd.gChatId:
            teleg_cmd.sendMessages(chat_id, "/start first.")
            return False
        return True

    def __updatePrice(self, chat_id, sym, price):
        if sym in teleg_cmd.gSym[chat_id]:
            teleg_cmd.gSym[chat_id][sym]["currentPrice"] = price

    def __updateChange(self, chat_id, sym, change):
        if sym in teleg_cmd.gSym[chat_id]:
            teleg_cmd.gSym[chat_id][sym]["DailyChange"] = change

    def __customTime(*args):
        utc_dt = utc.localize(datetime.utcnow())
        my_tz = timezone("America/New_York")
        converted = utc_dt.astimezone(my_tz)
        return converted.timetuple()

    def __prepareWatcher(self, market_open, market_close):
        sym2ChatId = {}
        for id in teleg_cmd.gSym:
            for sym in teleg_cmd.gSym[id]:
                if sym not in sym2ChatId:
                    sym2ChatId[sym] = []
                if id not in sym2ChatId[sym]:
                    sym2ChatId[sym].append(id)
        th = threading.Thread(target=self.watchStockPriceTrend, args=(market_open, market_close, sym2ChatId))
        th.run()

    def __dailyTimer(self):
        nyc = timezone('America/New_York')
        while True:
            today = datetime.today().astimezone(nyc)
            today_str = datetime.today().astimezone(nyc).strftime('%Y-%m-%d')
            calendar = alpaca.getMarketCalendar(today_str)
            market_open = today.replace(
                day=calendar.date.day,
                hour=0,
                minute=0,
                second=0
            )
            today = today.replace(
                hour=0,
                minute=0,
                second=0
            )
            after = today - market_open
            if after.days == 0:
                self.logger.info("Happy tomorrow")
                self.logger.info(after)
                market_open = today.replace(
                    hour=calendar.open.hour,
                    minute=calendar.open.minute,
                    second=0
                )
                market_open = market_open.astimezone(nyc)
                market_close = today.replace(
                    hour=calendar.close.hour,
                    minute=calendar.close.minute,
                    second=0
                )
                market_close = market_close.astimezone(nyc)

                self.__prepareWatcher(market_open, market_close)
            tomorrow = datetime.now().astimezone(nyc) + timedelta(days=1)
            tomorrow = today.replace(hour=7, minute=0, second=0)
            delta = tomorrow - datetime.now().astimezone(nyc)
            self.logger.info("Going to sleep to tomorrow")
            self.logger.info(delta)
            time.sleep(delta.seconds)
