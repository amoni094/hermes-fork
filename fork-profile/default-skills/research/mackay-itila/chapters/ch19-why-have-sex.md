# Chapter 19: Why have Sex? Information Acquisition and Evolution

## Core Idea
Sex (genetic mixing) is an information-acquisition and error-correction strategy: it lets a population combine independently discovered beneficial mutations and purge deleterious ones, analogous to coding and to Bayesian model combination. Evolution is an inference algorithm about what genomes work in an environment.

## Frameworks Introduced
- **Genome as a codeword / hypothesis** about the environment; fitness is a noisy likelihood.
- **Mixing vs cloning**: asexual reproduction copies the whole hypothesis; sex recombines parts (crossover), like mixing codes or bagging features.
- **Muller’s ratchet / Kondrashov**: asexual populations accumulate irreversible deleterious mutations; sex plus selection is an error-correcting decoder.
- **Information rate of selection**: each generation, differential reproduction can convey at most a few bits per individual about the environment (MacKay / related “fitness flux” intuitions). Selection is a narrow communications channel.

## Key Concepts
- **Beneficial mutation combination**: if two loci have rare good alleles p and q, sex produces pq offspring in one generation; asexuals need a double mutant.
- **Epistasis**: if fitness is not multiplicative, recombination can help or hurt (breaking co-adapted gene complexes).
- **Learning vs evolution**: both are search with information gain; evolution’s “dataset” is deaths and differential fertility.
- **Quasispecies / typical genomes**: at high mutation rate, the population is a cloud; there is an error threshold beyond which information about the fitness peak is lost (channel capacity of copying).

## Key Equations
- Copying channel: DNA replication ≈ BSC or more structured noise; C_copy = 1−H2(f_mut) per base (crude)
- Time to combine two mutations asexually ~ 1/(N p q) vs sexually ~ 1/(N p)+1/(N q)
- Selection information: KL between offspring distribution and parental, bounded by generation’s fitness variance
- Error threshold: mutation rate × genome length ≲ O(1) without coding/redundancy

## Algorithms and Techniques
**Compare mixing strategies as search algorithms**
1. Represent hypotheses as bit-strings (genomes).
2. Asexual: clone + mutate; sexual: crossover + mutate; evaluate fitness.
3. Measure time to discover concatenated good blocks.
4. Add deleterious noise to see Muller’s ratchet (fitness declines without recombination).

## Mental Models
- Think of sex as a *code* that makes the population decoder able to combine independent syndrome information from different lineages.
- Think of death as a measurement; a species that never dies learns nothing.
- Error threshold = channel capacity of the copying channel; sex and diploidy are coding tricks.

## Worked Example
Two loci, beneficial alleles each at frequency 1% in a population of 10^6.
- Expected double mutants asexually: N p q = 0.01 if mutations must co-occur in one lineage; waiting time can be huge if they arise in different individuals who never meet.
- Sexually, recombination produces ~ N p q = 100 double-good offspring per generation from existing singles. That is the information-combination argument for sex.

## Anti-patterns
- **Treating evolution as “just mutation”** without selection as a channel and sex as a code.
- **Ignoring population size**: information gain per generation scales with N, but only logarithmically in some bounds.
- **Assuming sex always helps**: strong negative epistasis / local peaks can make recombination destructive.
- **Mapping this chapter one-to-one onto human sociology** — it is a toy information-theoretic argument.

## Key Takeaways
1. Reproduction strategy = inference/coding strategy.
2. Sex combines independently found bits of information.
3. Copying fidelity × genome length is capacity-limited.
4. Selection’s information rate is modest; clever representation (modularity, sex) matters more than raw mutation.
5. Optional on a first reading of the book; conceptually ties IT to biology.

## Connects To
- **Ch 1**: DNA replication as a noisy channel.
- **Ch 10**: error thresholds as converse theorems.
- **Ch 28**: Occam / which genome complexity is justified by data (environment).
- **Ch 36**: fitness as expected utility.
