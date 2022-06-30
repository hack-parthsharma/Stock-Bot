import sys
from stock import Stock_bot

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: ./Stock_bot TOKEN alpaca_api_key alpaca_secret_key openexchangerate_key")
        exit(0)

    bot = Stock_bot(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
