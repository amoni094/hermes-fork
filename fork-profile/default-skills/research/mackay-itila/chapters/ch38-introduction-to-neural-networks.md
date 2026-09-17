# Chapter 38: Introduction to Neural Networks

## Core Idea
Neural nets are networks of simple units studied for biology, engineering (learnable pattern recognition), and as complex systems. This chapter is a short orientation: conventional RAM is address-based, brittle, and not associative; brains are content-addressable, error-tolerant, and distributed. Later chapters specify architecture, activity rule, and learning rule for each model.

## Key Concepts
- **Three motivations**: (1) hints about brains, (2) machines that learn, (3) complex adaptive systems. Models here are *not* faithful biology.
- **Address-based memory**: data live at an address unrelated to content. Recall needs the address; a flipped address bit fetches the wrong record; only a few devices participate.
- **Biological / associative memory**: cues can be partial or noisy; hardware faults are tolerated; many neurons store many memories (distributed, with some specialization).
- **Content-addressable memory**: complete a pattern from a fragment (name ↔ face).
- **Architecture**: which variables exist and how they connect (weights, activities).
- **Activity rule**: short-timescale dynamics — how neurons update given inputs/weights.
- **Learning rule**: long-timescale dynamics — how weights change given data (and possibly activities).

## Frameworks and Methods
- **Specify three things** for every net in the book: architecture, activity rule, learning rule. If terminology is foggy, skip to Ch 39.
- **Feedforward vs feedback**: directed acyclic graphs vs nets with cycles (Hopfield, Boltzmann). Introduced properly in Ch 42.
- **Supervised vs unsupervised**: later chapters split classifiers / regression (39–41, 44–45) from associative nets (42–43).
- **Error-correcting codes as analogy**: RAM *adds* ECC; neural associative memory *is* an error-correcting dynamical system (developed in Hopfield capacity, Ch 42).

## Key Equations
This chapter is conceptual; no numbered laws. The template for later chapters:

- y = f(W, x)                 (activity)
- W ← W + ΔW(data, y, W)     (learning)
- Energy / posterior appear once the model is probabilistic (Ch 41+)

## Algorithms and Techniques
**How MacKay wants you to read a neural-net paper**
1. Draw the architecture (who talks to whom).
2. Write the activity rule (deterministic sigmoid, threshold, or stochastic).
3. Write the learning rule (gradient on an error, Hebb, wake-sleep, …).
4. Ask whether the net is being used as memory, classifier, density model, or optimizer.

**Contrast with digital memory (checklist)**
- Associative? Robust to cue noise? Robust to hardware faults? Distributed?

## Anti-patterns
- **Treating these chapters as neuroscience**.
- **Expecting a survey of the field** — MacKay gives a taste and points to papers for real applications.
- **Confusing “parallel computers” with “distributed neural computation”** — extra CPUs still fetch by address.
- **Skipping the three-rule template** and drowning in diagrams.

## Key Takeaways
1. Neural nets in this book are idealized computational models, not cortical simulations.
2. Brains look like associative, robust, distributed memories; RAM does not.
3. Always pin down architecture, activity, learning.
4. Supervised point-neurons, Hopfield nets, Boltzmann machines, MLPs, and GPs are the sequence.
5. Memory-as-error-correction is the bridge back to Parts I–II.

## Connects To
- **Ch 1, 13**: codes and distance — associative recall as decoding.
- **Ch 39–41**: one neuron, capacity, learning as inference.
- **Ch 42–43**: Hopfield and Boltzmann — the associative models promised here.
- **Ch 44–45**: multilayer supervised maps and Gaussian processes.
