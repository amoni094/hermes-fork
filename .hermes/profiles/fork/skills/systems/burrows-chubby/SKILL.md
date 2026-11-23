---
name: burrows-chubby
description: "Use when distributed locks, leases, or Chubby sequencers."
tags: [distributed-systems, locking, leases, sequencers]
triggers:
  - distributed lock service
  - session lease KeepAlive
  - Chubby sequencer generation
  - lock lease coordination
  - NOT ZooKeeper watches (use hunt-zookeeper)
  - related: lynch-distributed-algorithms
---

# Burrows 2006 - The Chubby Lock Service

Mike Burrows, Google. OSDI 2006.

## Session Leases
- Time-bounded lease (default 12s); server guarantees session state
- Client renews via KeepAlive; on expiry enters grace period

## Sequencers (sec 2.9)
- Sequencer = (lock_name, mode, generation_number)
- Monotone generation: old holder writes rejected if gen < current_gen
- Prevents split-brain from delayed network messages

```python
def accept_write(gen, current_gen):
    if gen < current_gen:
        raise StaleError(f"{gen} < {current_gen}")
```

## Caching
- Master pushes invalidation before modifying; waits for all acks
- No stale reads during valid lease

## Hermes-Fork Applications
- executions.db generation column: monotone epoch per run; stale writes rejected
- execution-state-machine.py enforces generation check on audit
- jobs-config-watcher.py version token = (inode, mtime_ns, size)

## References
- Burrows, M. (2006). OSDI '06
