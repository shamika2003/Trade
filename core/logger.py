import datetime

def log(text):
    with open("bot_log.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} | {text}\n")