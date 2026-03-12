import threading

from cache import Cache as cache


def reader():
    for _ in range(1000):
        cache.get("a")

def writer():
    for i in range(1000):
        cache.set("a", i)

threads = []

for _ in range(5):
    threads.append(threading.Thread(target=reader))

threads.append(threading.Thread(target=writer))

for t in threads:
    t.start()

for t in threads:
    t.join()