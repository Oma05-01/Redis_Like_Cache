import time
from collections import OrderedDict
import threading
from locks import ReaderWriterLock
import json

SNAPSHOT_FILE = "snapshot.rdb"

# ----------------------------
# 1️⃣ CacheEntry — Individual item with TTL
# ----------------------------

class CacheEntry:
    def __init__(self, value, ttl=None):
        self.value = value

        # If a Time-To-Live (ttl) is provided, calculate the exact expiration timestamp
        if ttl is not None:
            self.expiry = time.time() + float(ttl)
        else:
            # If no ttl is provided, it never expires
            self.expiry = None

    def is_expired(self):
        # If expiry is None, it lives forever
        if self.expiry is None:
            return False

        # True if the current time has passed the expiration timestamp
        return time.time() > self.expiry


# ----------------------------
# 2️⃣ Cache — Core in-memory engine
# ----------------------------
class Cache:

    def __init__(self, max_size=None, eviction_policy="LRU"):
        """
        max_size: Optional limit for number of items
        eviction_policy: Currently only "LRU" supported
        """
        self.store = OrderedDict()
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self.lock = ReaderWriterLock()
        self.eviction_count = 0
        self.expired_count = 0

        self.load_snapshot()

    def _active_expire(self):

        self.lock.acquire_write()

        try:
            for key in list(self.store.keys()):
                entry = self.store[key]

                if entry.is_expired():
                    del self.store[key]
                    self.expired_count += 1

        finally:
            self.lock.release_write()

    def _expiration_loop(self):
        while True:
            time.sleep(1)
            self._active_expire()

    def start_expiration_worker(self):
        thread = threading.Thread(target=self._expiration_loop, daemon=True)
        thread.start()

    def set(self, key, value, ttl=None):

        self.lock.acquire_write()

        try:
            if key in self.store:
                self.store.pop(key)

            if self.max_size and len(self.store) >= self.max_size:
                evicted_key, _ = self.store.popitem(last=False)
                self.eviction_count += 1
                print(f"[EVICT] {evicted_key}")

            self.store[key] = CacheEntry(value, ttl)
            self.store.move_to_end(key)

        finally:
            self.lock.release_write()

    def get(self, key):

        self.lock.acquire_read()

        try:
            entry = self.store.get(key)
            if entry is None or entry.is_expired():
                self.store.pop(key, None)
                print(f"[MISS] {key}")
                return None

            # Update LRU order
            self.store.move_to_end(key)
            print(f"[HIT] {key} = {entry.value}")
            return entry.value
        finally:
            self.lock.release_read()

    def delete(self, key):

        self.lock.acquire_write()

        try:
            self.store.pop(key, None)

        finally:
            self.lock.release_write()

    def purge_expired(self):
        """Remove all expired entries."""
        keys_to_remove = [k for k, v in self.store.items() if v.is_expired()]
        for key in keys_to_remove:
            del self.store[key]
            print(f"[PURGE] {key} expired")

    def stats(self):
        return {
            "keys": len(self.store),
            "max_size": self.max_size,
            "eviction_policy": self.eviction_policy,
            "expired": self.expired_count
        }

    def save_snapshot(self):

        self.lock.acquire_read()

        try:
            snapshot = {}

            for key, entry in self.store.items():
                snapshot[key] = {
                    "value": entry.value,
                    "expiry": entry.expiry
                }

            with open(SNAPSHOT_FILE, "w") as f:
                json.dump(snapshot, f)

            print("[INFO] Snapshot saved.")

        finally:
            self.lock.release_read()

    def load_snapshot(self):
        try:
            with open(SNAPSHOT_FILE, "r") as f:
                snapshot = json.load(f)

            for key, data in snapshot.items():
                entry = CacheEntry(data["value"])
                entry.expiry = data["expiry"]

                if not entry.is_expired():
                    self.store[key] = entry

            print("[INFO] Snapshot loaded.")

        except FileNotFoundError:
            # File doesn't exist yet, completely normal on first run
            pass
        except json.JSONDecodeError:
            # File exists but is empty or corrupted
            print("[WARNING] Snapshot file is empty or corrupted. Starting fresh.")
            pass

# ----------------------------
# 3️⃣ CacheCLI — Command-line interface
# ----------------------------
class CacheCLI:
    def __init__(self, cache):
        self.cache = cache

    def run(self):
        print("Cache CLI. Commands: SET key value [ttl], GET key, DEL key, EXIT")
        while True:
            line = input("cache > ").strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "SET" and len(parts) >= 3:
                key = parts[1]
                value = parts[2]
                ttl = None

                # support: SET key value EX 10
                if len(parts) == 5 and parts[3].upper() == "EX":
                    ttl = int(parts[4])

                self.cache.set(key, value, ttl)

            elif cmd == "GET" and len(parts) == 2:
                self.cache.get(parts[1])

            elif cmd in ("DEL", "DELETE") and len(parts) == 2:
                self.cache.delete(parts[1])

            elif cmd == "PURGE":
                self.cache.purge_expired()

            elif cmd == "STATS":
                stats = self.cache.stats()
                for k, v in stats.items():
                    print(f"{k}: {v}")

            elif cmd == "EXIT":
                print("Shutting down cache.")
                break

            elif cmd == "SAVE":
                self.cache.save_snapshot()

            else:
                print("[ERROR] Invalid command")


