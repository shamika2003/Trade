import datetime

def log_event(text):

    with open("bot_log.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} | {text}\n")