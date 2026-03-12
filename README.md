## Cache System

A from-scratch implementation of a Redis-like in-memory cache to understand memory pressure, eviction policies, and expiration tradeoffs, not a production replacement for Redis.

## Why This Project Exists

Modern systems rely heavily on caching to reduce database load and improve latency. Systems like Redis and Memcached are often placed between applications and databases to serve frequently accessed data quickly.

This project was built to understand the internal mechanics behind caching systems, particularly:

- How caches manage limited memory
- How expiration policies work
- How eviction strategies impact performance
- How concurrency affects in-memory data structures

The goal was to close the gap between using caches in applications and understanding how caching systems are implemented internally.

## Scope & Constraints
**Included**

- In-memory key-value storage
- SET, GET, and DEL operations
- TTL (time-to-live) support for key expiration
- Lazy expiration during reads
- Background expiration cleanup worker
- LRU (Least Recently Used) eviction policy
- Configurable maximum cache size
- Reader-writer concurrency model
- Snapshot persistence to disk
- CLI interface for interacting with the cache
- Basic runtime statistics (keys, evictions, expirations)

## Explicitly Excluded

These features were intentionally not implemented to keep the project focused:

- Distributed caching across multiple nodes
- Replication or clustering
- Network server protocol (e.g. Redis RESP protocol)
- Advanced eviction strategies (LFU, ARC)
- Incremental snapshotting or WAL logging
- Copy-on-write persistence

These omissions simplify the system while still demonstrating core cache architecture concepts.

## Architecture Overview

The cache is composed of several core components:
```
            CLI Interface
                  │
                  ▼
            Cache Engine
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
  In-Memory    Expiration   Eviction
   Store        System       Policy
 (OrderedDict)   (TTL)        (LRU)
      │
      ▼
 Snapshot Persistence
       (Disk)
```
## Core Components

**Cache Engine**
- Central coordinator for all operations
- Manages memory limits and eviction

**In-Memory Store**
- Implemented using OrderedDict
- Maintains key ordering for LRU eviction

**Expiration System**
- Keys can be stored with expiration timestamps
- Lazy expiration occurs during reads
- Background worker periodically cleans expired keys

**Eviction Policy**
- LRU eviction removes the least recently used key when capacity is exceeded

**Snapshot Persistence**
- Allows manual saving of the cache state to disk
- Snapshot loaded on startup

## Key Design Decisions
**1 — OrderedDict for LRU Tracking**

OrderedDict was chosen to maintain insertion and access ordering.

**Tradeoff:**
- Simplifies implementation
- Not as optimized as custom LRU implementations used in production systems

**2 — Lazy Expiration**

Keys are checked for expiration during GET operations.

**Tradeoff:**
- Simpler logic
- Expired keys may remain in memory until accessed

Real systems combine lazy expiration with background cleanup.

**3 — Reader-Writer Lock for Concurrency**
The cache allows:

- Multiple concurrent reads
- Single writer access

**Tradeoff:**
- Simpler concurrency model
- Writers block readers during updates

**4 — Snapshot Persistence Instead of WAL
**
Persistence uses full snapshots rather than write-ahead logging.

**Tradeoff:**
- Simpler to implement
- Recent writes may be lost if a crash occurs before snapshot

## Performance Characteristics

This cache prioritizes simplicity and predictable behavior rather than absolute performance.

### Read Performance

GET operations are typically **O(1)**.

This is achieved through:

- direct key lookup in a dictionary
- constant-time access to entries
- minimal locking through a reader-writer model

Reads can occur concurrently across multiple threads.

---

### Write Performance

SET operations are **O(1)** under normal conditions.

However, when the cache reaches capacity, eviction occurs:

- LRU eviction removes the least recently used key
- eviction is also **O(1)** using `OrderedDict`

---

### Expiration Behavior

Expiration is handled through two mechanisms:

1. **Lazy expiration**
   - checked during GET operations

2. **Active cleanup worker**
   - periodically scans for expired keys

This hybrid approach balances:

- CPU usage
- memory efficiency

---

### Eviction Behavior

Eviction is triggered when the cache exceeds its configured maximum size.

The system removes:

Least Recently Used (LRU) key.

Frequent access patterns therefore naturally keep hot keys in memory.

---

### Persistence Cost

Snapshot persistence requires serializing the entire cache to disk.

Cost characteristics:

- **O(n)** write time
- blocks readers briefly during snapshot

This is acceptable for small caches but not suitable for large datasets.


## Failure Modes & Limitations
**Memory Pressure**

Under heavy writes, eviction frequency increases and performance may degrade due to constant key removal.

**Expired Key Storms**
If many keys share identical TTL values, large numbers may expire simultaneously, causing temporary CPU spikes during cleanup.

**Snapshot Data Loss**
Snapshots are point-in-time saves. Any writes after the last snapshot will be lost on crash.

**Lock Contention**
Under high write loads, the reader-writer lock may introduce contention, limiting concurrency.

## System Experiments

Several experiments were run to observe cache behavior under different conditions.

---

### Memory Pressure

**Test:**

Cache configured with small capacity.

```
SET a 1
SET b 2
SET c 3
SET d 4
SET e 5
SET f 6
```

**Observation:**

The least recently used key was evicted when capacity was exceeded.

**Result:**

LRU eviction behaved as expected.

---

### Hot Key Scenario

**Test:**

One key accessed significantly more often than others.

```
SET popular data
GET popular
GET popular
GET popular
```

**Observation:**

The frequently accessed key remained in memory while less-used keys were evicted.

**Insight:**
LRU strongly favors hot keys.

---

### Expired Key Storm

**Test:**

Multiple keys assigned identical TTL values.
```
SET a 1 EX 3
SET b 2 EX 3
SET c 3 EX 3
SET d 4 EX 3
```

**Observation:**

When the TTL expired simultaneously, the expiration worker removed several keys at once.

**Impact:**

- Short bursts of CPU activity occurred during cleanup.
- Real systems often randomize TTL values to reduce expiration spikes.

---

### High Write Rate

**Test:**
Large numbers of write operations executed rapidly.

```
for i in range(10000):
cache.set(f"key{i}", i)
```

**Observation:**
Evictions increased significantly once capacity was reached.

**Insight:**
Caches under sustained writes spend a large portion of time performing eviction operations.

## What I Learned

Building this system revealed several non-obvious insights about caching systems:

**Caching is disposable storage**
Caches intentionally trade durability for performance. Losing data is acceptable as long as the system can rebuild it from the primary data source.

**Eviction policies shape system behavior**
LRU eviction strongly favors frequently accessed data, allowing “hot keys” to remain in memory while rarely accessed keys are evicted.

**Expiration is more complex than it appears**
Managing TTL correctly requires balancing:
- memory usage
- CPU overhead
- cleanup strategies

Large systems must avoid expiration storms where thousands of keys expire simultaneously.

**Concurrency becomes complicated quickly**
Even a simple cache requires careful coordination between:
- reads
- writes
- eviction
- background expiration workers

## How Production Systems Do This Differently
Systems like Redis introduce significant complexity to improve performance and reliability.

**Production caches typically include:**
- advanced eviction policies (LFU, adaptive algorithms)
- copy-on-write snapshotting
- append-only persistence logs
- distributed clustering
- replication for fault tolerance
- network protocols for client communication
- These features dramatically increase complexity but allow the system to operate reliably at scale.

## How to Run
python main.py

Example usage:
```
cache > SET name oma
cache > GET name
oma

cache > SET session abc EX 10
cache > GET session

cache > STATS

cache > SAVE

cache > EXIT
