"""Module provides functions to export as csv by time of day
    (???)
"""

import datetime
from copy import deepcopy as copy
import sys

from tools import get_chat_list


OUTPUT = "timeofday.csv"

arguments = sys.argv[1:]

if len(arguments) != 1:  # (filename, name, shape)
    print(f"ERROR: 3 arguments expected, {len(arguments)} given!")
    sys.exit()

filename = arguments[0]

times = {}

chats = get_chat_list(filename)
names = {}

for chat in chats:
    name = chat["name"]
    if not name in names:
        if name:
            names[name] = 0

MINUTES = 10
for i in range((24*60)//MINUTES):
    t = (datetime.datetime(2000, 1, 1, 0, 0) +
         ((datetime.timedelta(minutes=MINUTES) * i))).time()
    times[t] = copy(names)

total_per_name = copy(names)

for chat in chats:
    for message in chat["messages"]:
        if message["type"] == "message":
            dt = datetime.datetime.fromtimestamp(int(message["date_unixtime"]))
            if dt > datetime.datetime(2022, 1, 1):
                for t in times:
                    if dt.time() < t:
                        break
                    time = t

                name = chat["name"]
                if name:
                    TEXT = ""
                    for entiy in message["text_entities"]:
                        if entiy["type"] == "plain":
                            TEXT += " " + entiy["text"]
                    words = len(TEXT.split())
                    times[time][name] += words
                    total_per_name[name] += words

print(times)
print(total_per_name)

to_remove = []
for name, n in total_per_name.items():
    if n < 10000:
        to_remove.append(name)

for time, nam in times.items():
    for name in to_remove:
        nam.pop(name)

for name in to_remove:
    names.pop(name)

CSV_STR = "time," + ",".join(names.keys())
for time in sorted(times):
    CSV_STR += f"\n{time},"
    CSV_STR += ",".join(map(str, times[time].values()))

# print(CSV_STR)
with open(OUTPUT, "w", encoding='utf-8') as f:
    f.write(CSV_STR)
