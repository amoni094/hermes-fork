# Computer Science
## Artificial Intelligence
**arXiv:2608.21690** (cs)
[Submitted on 21 Aug 2026]

# Title: Context as an Environment: Programmatic Context Management for Long-Horizon Agents
Authors: [Yin Lin](https://arxiv.org/search/cs?searchtype=author&query=Lin,+Y) , [Elaine Ang](https://arxiv.org/search/cs?searchtype=author&query=Ang,+E) , [Erkang Zhu](https://arxiv.org/search/cs?searchtype=author&query=Zhu,+E) , [Bolin
Ding](https://arxiv.org/search/cs?searchtype=author&query=Ding,+B) , [Jingren Zhou](https://arxiv.org/search/cs?searchtype=author&query=Zhou,+J)
View PDF [HTML (experimental)](https://arxiv.org/html/2608.21690v1)
> Abstract: LLM agents increasingly take on long-running tasks whose history grows far beyond a single model context window.
Existing approaches compress earlier interactions or extract selected information into fixed memory representations, committing to what to preserve before future needs are known.
We present Scroll, a context manager that treats each agent session as an executable Session Environment. The environment is backed by an append-only Event Log and a sandboxed, persistent Python kernel.
The kernel maintains a typed namespace across model calls, allowing tool outputs, retrieved history, and derived state to be bound to variables rather than serialized into the prompt at each call.
Model-written code searches, materializes, and transforms session state through exec; only explicitly printed projections enter the model's working view for the next call.
Context management thus becomes a programming task that inherits the improving coding abilities of LLMs, while the Event Log preserves lossless historical ground truth.

...

full log. With Qwen3.8-Max as the backbone, Scroll achieves 94.8% on LongMemEval_S; 73.1% on BEAM_10M, surpassing the best published memory system by 5.1 points; and 86.7% on LOCA_256K, exceeding the best published long-horizon agent by 37.4 points.
| Subjects: | Artificial Intelligence (cs.AI) |
| Cite as: | [arXiv:2608.21690](https://arxiv.org/abs/2608.21690) [cs.AI] |
|  | https://doi.org/10.48550/arXiv.2608.21690 |

...

## Submission history
From: Yin Lin  [view email ]
**[v1]** Fri, 21 Aug 2026 23:39:19 UTC (402 KB)
Full-text links: