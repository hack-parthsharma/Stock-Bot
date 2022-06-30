import os.path
import json

def readFromSymsCache(path):
    sym = {}
    if os.path.exists(path):
        f = open(path, 'r')
        sym_text = f.readline()
        if len(sym_text) > 0:
            sym = json.loads(sym_text)
        f.close()
    else:
        f = open(path, 'w')
        f.close()
    return sym

def writeToSymsCache(path, symbols):
    f = open(path, "w")
    raw = json.dumps(symbols)
    f.write(raw)
    f.close()

def readFromChatIdCache(path):
    chat_id = []
    if os.path.exists(path):
        f = open(path, 'r')
        text = f.readlines()
        for line in text:
            line = line.strip('\n')
            if int(line) not in chat_id:
                chat_id.append(int(line))
        f.close()
    else:
        f = open(path, 'w')
        f.close()
    return chat_id

def writeToChatIdCache(path, chat_id):
    f = open(path, "a+")
    raw = str(chat_id)
    f.write(raw+"\n")
    f.close()

def overwriteToChatIdCache(path, Ids):
    f = open(path, "w")
    for each in Ids:
        raw = str(each)
        f.write(raw+"\n")
    f.close()