# ----------------------------
# 4️⃣ main.py — Entry point
# ----------------------------
from cache import Cache, CacheCLI

if __name__ == "__main__":
    # Optional: set max_size for eviction testing
    cache = Cache(max_size=5)
    cache.start_expiration_worker()
    cli = CacheCLI(cache)
    cli.run()