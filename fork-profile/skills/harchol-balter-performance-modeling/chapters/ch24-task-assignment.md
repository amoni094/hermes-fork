# Ch 24 — Task Assignment for Server Farms

**Use when**: dispatching jobs to several servers (FCFS farm vs PS farm).

## FCFS farms (high C² is poison)
Random / Round-Robin send elephants and mice to the same FCFS queue ⇒ P-K explosion on every replica.

**Size-interval task assignment (SITA / JSQ-size):** bin jobs by size class onto dedicated servers (short-job boxes vs long-job boxes). Cuts C² *per queue*. This is the right design when servers are FCFS and sizes are known.

Least-work-left (LWL) / join-shortest-queue: better than random but still suffers HT.

## PS farms
Because PS is insensitive to C², **random/JSQ to PS servers is fine** — you do not need size-interval isolation for the mean. (Tails/slowdown of large jobs still differ.)

## Optimal design
If you can choose server speeds and policy: one fast PS or SRPT box beats many slow FCFS boxes for the same total capacity. If you must shard FCFS, isolate size classes.

Hermes: don't round-robin mixed 2s and 30min jobs onto the same FCFS worker. Tag size class or use one PS/SRPT worker pool.
