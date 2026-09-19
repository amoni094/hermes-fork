OXFORD

# Probability and Random Processes GEOFFREY GRIMMETT and DAVID STIRZAKER 

# Probability and <br> Random Processes 

GEOFFREY R. GRIMMETT
Statistical Laboratory, University of Cambridge and
DAVID R. STIRZAKER
Mathematical Institute, University of Oxford

## OXFORD

## UNIVERSITY PRESS

Great Clarendon Street, Oxford ox2 6dp
Oxford University Press is a department of the University of Oxford. It furthers the University's objective of excellence in research, scholarship, and education by publishing worldwide in

Oxford New York
Athens Auckland Bangkok Bogotá Buenos Aires Cape Town
Chennai Dar es Salaam Delhi Florence Hong Kong Istanbul Karachi Kolkata Kuala Lumpur Madrid Melbourne Mexico City Mumbai Nairobi Paris São Paulo Shanghai Singapore Taipei Tokyo Toronto Warsaw with associated companies in Berlin Ibadan

Oxford is a registered trade mark of Oxford University Press in the UK and in certain other countries

Published in the United States by Oxford University Press Inc., New York
© Geoffrey R. Grimmett and David R. Stirzaker 1982, 1992, 2001
The moral rights of the author have been asserted
Database right Oxford University Press (maker)
First edition 1982
Second edition 1992
Third edition 2001

All rights reserved. No part of this publication may be reproduced, stored in a retrieval system, or transmitted, in any form or by any means, without the prior permission in writing of Oxford University Press, or as expressly permitted by law, or under terms agreed with the appropriate reprographics rights organization. Enquiries concerning reproduction outside the scope of the above should be sent to the Rights Department, Oxford University Press, at the address above

You must not circulate this book in any other binding or cover and you must impose this same condition on any acquirer

A catalogue record for this title is available from the British Library
Library of Congress Cataloging in Publication Data
Data available
ISBN 0198572239 [hardback]
ISBN 0198572220 [paperback]
10987654321

Typeset by the authors
Printed in Great Britain on acid-free paper by Biddles Ltd, Guildford \& King's Lynn

Lastly, numbers are applicable even to such things as seem to be governed by no rule, I mean such as depend on chance: the quantity of probability and proportion of it in any two proposed cases being subject to calculation as much as anything else. Upon this depend the principles of game. We find sharpers know enough of this to cheat some men that would take it very ill to be thought bubbles; and one gamester exceeds another, as he has a greater sagacity and readiness in calculating his probability to win or lose in any particular case. To understand the theory of chance thoroughly, requires a great knowledge of numbers, and a pretty competent one of Algebra.

> John Arbuthnot
> An essay on the usefulness of mathematical learning

25 November 1700

To this may be added, that some of the problems about chance having a great appearance of simplicity, the mind is easily drawn into a belief, that their solution may be attained by the mere strength of natural good sense; which generally proving otherwise, and the mistakes occasioned thereby being not infrequent, it is presumed that a book of this kind, which teaches to distinguish truth from what seems so nearly to resemble it, will be looked on as a help to good reasoning.

Abraham de Moivre<br>The Doctrine of Chances

1717

## Preface to the Third Edition

This book provides an extensive introduction to probability and random processes. It is intended for those working in the many and varied applications of the subject as well as for those studying more theoretical aspects. We hope it will be found suitable for mathematics undergraduates at all levels, as well as for graduate students and others with interests in these fields.

In particular, we aim:

- to give a rigorous introduction to probability theory while limiting the amount of measure theory in the early chapters;
- to discuss the most important random processes in some depth, with many examples;
- to include various topics which are suitable for undergraduate courses, but are not routinely taught;
- to impart to the beginner the flavour of more advanced work, thereby whetting the appetite for more.

The ordering and numbering of material in this third edition has for the most part been preserved from the second. However, a good many minor alterations and additions have been made in the pursuit of clearer exposition. Furthermore, we have included new sections on sampling and Markov chain Monte Carlo, coupling and its applications, geometrical probability, spatial Poisson processes, stochastic calculus and the Itô integral, Itô's formula and applications, including the Black-Scholes formula, networks of queues, and renewal-reward theorems and applications. In a mild manifestation of millennial mania, the number of exercises and problems has been increased to exceed 1000 . These are not merely drill exercises, but complement and illustrate the text, or are entertaining, or (usually, we hope) both. In a companion volume One Thousand Exercises in Probability (Oxford University Press, 2001), we give worked solutions to almost all exercises and problems.

The basic layout of the book remains unchanged. Chapter 1-5 begin with the foundations of probability theory, move through the elementary properties of random variables, and finish with the weak law of large numbers and the central limit theorem; on route, the reader meets random walks, branching processes, and characteristic functions. This material is suitable for about two lecture courses at a moderately elementary level. The rest of the book is largely concerned with random processes. Chapter 6 deals with Markov chains, treating discretetime chains in some detail (and including an easy proof of the ergodic theorem for chains with countably infinite state spaces) and treating continuous-time chains largely by example. Chapter 7 contains a general discussion of convergence, together with simple but rigorous accounts of the strong law of large numbers, and martingale convergence. Each of these two chapters could be used as a basis for a lecture course. Chapters 8-13 are more fragmented and provide suitable material for about five shorter lecture courses on: stationary processes and ergodic theory; renewal processes; queues; martingales; diffusions and stochastic integration with applications to finance.

We thank those who have read and commented upon sections of this and earlier editions, and we make special mention of Dominic Welsh, Brian Davies, Tim Brown, Sean Collins, Stephen Suen, Geoff Eagleson, Harry Reuter, David Green, and Bernard Silverman for their contributions to the first edition.

Of great value in the preparation of the second and third editions were the detailed criticisms of Michel Dekking, Frank den Hollander, Torgny Lindvall, and the suggestions of Alan Bain, Erwin Bolthausen, Peter Clifford, Frank Kelly, Doug Kennedy, Colin McDiarmid, and Volker Priebe. Richard Buxton has helped us with classical matters, and Andy Burbanks with the design of the front cover, which depicts a favourite confluence of the authors.

This edition having been reset in its entirety, we would welcome help in thinning the errors should any remain after the excellent TEX-ing of Sarah Shea-Simonds and Julia Blackwell.

Cambridge and Oxford
G. R. G.

April 2001
D. R. S.

## Contents

1 Events and their probabilities
1.1 Introduction ..... 1
1.2 Events as sets ..... 1
1.3 Probability 4
1.4 Conditional probability 8
1.5 Independence ..... 13
1.6 Completeness and product spaces ..... 14
1.7 Worked examples ..... 16
1.8 Problems ..... 21
2 Random variables and their distributions
2.1 Random variables ..... 26
2.2 The law of averages ..... 30
2.3 Discrete and continuous variables ..... 33
2.4 Worked examples ..... 35
2.5 Random vectors ..... 38
2.6 Monte Carlo simulation ..... 41
2.7 Problems ..... 43
3 Discrete random variables
3.1 Probability mass functions ..... 46
3.2 Independence ..... 48
3.3 Expectation ..... 50
3.4 Indicators and matching ..... 56
3.5 Examples of discrete variables ..... 60
3.6 Dependence ..... 62
3.7 Conditional distributions and conditional expectation ..... 67
3.8 Sums of random variables ..... 70
3.9 Simple random walk ..... 71
3.10 Random walk: counting sample paths ..... 75
3.11 Problems ..... 83
4 Continuous random variables
4.1 Probability density functions ..... 89
4.2 Independence ..... 91
4.3 Expectation ..... 93
4.4 Examples of continuous variables ..... 95
4.5 Dependence ..... 98
4.6 Conditional distributions and conditional expectation ..... 104
4.7 Functions of random variables ..... 107
4.8 Sums of random variables ..... 113
4.9 Multivariate normal distribution ..... 115
4.10 Distributions arising from the normal distribution ..... 119
4.11 Sampling from a distribution ..... 122
4.12 Coupling and Poisson approximation ..... 127
4.13 Geometrical probability ..... 133
4.14 Problems ..... 140
5 Generating functions and their applications
5.1 Generating functions ..... 148
5.2 Some applications ..... 156
5.3 Random walk ..... 162
5.4 Branching processes ..... 171
5.5 Age-dependent branching processes ..... 175
5.6 Expectation revisited ..... 178
5.7 Characteristic functions ..... 181
5.8 Examples of characteristic functions ..... 186
5.9 Inversion and continuity theorems ..... 189
5.10 Two limit theorems ..... 193
5.11 Large deviations ..... 201
5.12 Problems ..... 206
6 Markov chains
6.1 Markov processes ..... 213
6.2 Classification of states ..... 220
6.3 Classification of chains ..... 223
6.4 Stationary distributions and the limit theorem ..... 227
6.5 Reversibility ..... 237
6.6 Chains with finitely many states ..... 240
6.7 Branching processes revisited ..... 243
6.8 Birth processes and the Poisson process ..... 246
6.9 Continuous-time Markov chains ..... 256
6.10 Uniform semigroups ..... 266
6.11 Birth-death processes and imbedding ..... 268
6.12 Special processes ..... 274
6.13 Spatial Poisson processes ..... 281
6.14 Markov chain Monte Carlo ..... 291
6.15 Problems ..... 296
7 Convergence of random variables
7.1 Introduction ..... 305
7.2 Modes of convergence ..... 308
7.3 Some ancillary results ..... 318
7.4 Laws of large numbers ..... 325
7.5 The strong law ..... 329
7.6 The law of the iterated logarithm ..... 332
7.7 Martingales ..... 333
7.8 Martingale convergence theorem ..... 338
7.9 Prediction and conditional expectation ..... 343
7.10 Uniform integrability ..... 350
7.11 Problems ..... 354
8 Random processes
8.1 Introduction ..... 360
8.2 Stationary processes ..... 361
8.3 Renewal processes ..... 365
8.4 Queues ..... 367
8.5 The Wiener process ..... 370
8.6 Existence of processes ..... 371
8.7 Problems ..... 373
9 Stationary processes
9.1 Introduction ..... 375
9.2 Linear prediction ..... 377
9.3 Autocovariances and spectra ..... 380
9.4 Stochastic integration and the spectral representation ..... 387
9.5 The ergodic theorem ..... 393
9.6 Gaussian processes ..... 405
9.7 Problems ..... 409
10 Renewals
10.1 The renewal equation ..... 412
10.2 Limit theorems ..... 417
10.3 Excess life ..... 421
10.4 Applications ..... 423
10.5 Renewal-reward processes ..... 431
10.6 Problems ..... 437
11 Queues
11.1 Single-server queues ..... 440
11.2 M/M/1 ..... 442
11.3 M/G/1 ..... 445
11.4 G/M/1 ..... 451
11.5 G/G/1 ..... 455
11.6 Heavy traffic ..... 462
11.7 Networks of queues ..... 462
11.8 Problems ..... 468
12 Martingales
12.1 Introduction ..... 471
12.2 Martingale differences and Hoeffding's inequality ..... 476
12.3 Crossings and convergence ..... 481
12.4 Stopping times ..... 487
12.5 Optional stopping ..... 491
12.6 The maximal inequality ..... 496
12.7 Backward martingales and continuous-time martingales ..... 499
12.8 Some examples ..... 503
12.9 Problems ..... 508
13 Diffusion processes
13.1 Introduction ..... 513
13.2 Brownian motion ..... 514
13.3 Diffusion processes ..... 516
13.4 First passage times ..... 525
13.5 Barriers ..... 530
13.6 Excursions and the Brownian bridge ..... 534
13.7 Stochastic calculus ..... 537
13.8 The Itô integral ..... 539
13.9 Itô's formula ..... 544
13.10 Option pricing ..... 547
13.11 Passage probabilities and potentials ..... 554
13.12 Problems ..... 561
Appendix I. Foundations and notation ..... 564
Appendix II. Further reading ..... 569
Appendix III. History and varieties of probability ..... 571
Appendix IV. John Arbuthnot's Preface to Of the laws of chance (1692) 573
Appendix V. Table of distributions ..... 576
Appendix VI. Chronology ..... 578
Bibliography ..... 580
Notation ..... 583
Index ..... 585

## 1

## Events and their probabilities

> Summary. Any experiment involving randomness can be modelled as a probability space. Such a space comprises a set $\Omega$ of possible outcomes of the experiment, a set $F$ of events, and a probability measure $P$. The definition and basic properties of a probability space are explored, and the concepts of conditional probability and independence are introduced. Many examples involving modelling and calculation are included.

### Introduction

Much of our life is based on the belief that the future is largely unpredictable. For example, games of chance such as dice or roulette would have few adherents if their outcomes were known in advance. We express this belief in chance behaviour by the use of words such as 'random' or 'probability', and we seek, by way of gaming and other experience, to assign quantitative as well as qualitative meanings to such usages. Our main acquaintance with statements about probability relies on a wealth of concepts, some more reasonable than others. A mathematical theory of probability will incorporate those concepts of chance which are expressed and implicit in common rational understanding. Such a theory will formalize these concepts as a collection of axioms, which should lead directly to conclusions in agreement with practical experimentation. This chapter contains the essential ingredients of this construction.

### Events as sets

Many everyday statements take the form 'the chance (or probability) of $A$ is $p$ ', where $A$ is some event (such as 'the sun shining tomorrow', 'Cambridge winning the Boat Race', ...) and $p$ is a number or adjective describing quantity (such as 'one-eighth', 'low', ...). The occurrence or non-occurrence of $A$ depends upon the chain of circumstances involved. This chain is called an experiment or trial; the result of an experiment is called its outcome. In general, we cannot predict with certainty the outcome of an experiment in advance of its completion; we can only list the collection of possible outcomes.
(1) Definition. The set of all possible outcomes of an experiment is called the sample space and is denoted by $\Omega$.
(2) Example. A coin is tossed. There are two possible outcomes, heads (denoted by H ) and tails (denoted by T ), so that $\Omega=\{ H , T \}$. We may be interested in the possible occurrences of the following events:
(a) the outcome is a head;
(b) the outcome is either a head or a tail;
(c) the outcome is both a head and a tail (this seems very unlikely to occur);
(d) the outcome is not a head.
(3) Example. A die is thrown once. There are six possible outcomes depending on which of the numbers 1,2,3,4,5, or 6 is uppermost. Thus $\Omega=\{1,2,3,4,5,6\}$. We may be interested in the following events:
(a) the outcome is the number 1;
(b) the outcome is an even number;
(c) the outcome is even but does not exceed 3;
(d) the outcome is not even.

We see immediately that each of the events of these examples can be specified as a subset $A$ of the appropriate sample space $\Omega$. In the first example they can be rewritten as
(a) $A=\{ H \}$,
(b) $A=\{ H \} \cup\{ T \}$,
(c) $A=\{ H \} \cap\{ T \}$,
(d) $A=\{ H \}^{ c }$,
whilst those of the second example become
(a) $A=\{1\}$,
(b) $A=\{2,4,6\}$,
(c) $A=\{2,4,6\} \cap\{1,2,3\}$,
(d) $A=\{2,4,6\}^{ c }$.

The complement of a subset $A$ of $\Omega$ is denoted here and subsequently by $A^{ c }$; from now on, subsets of $\Omega$ containing a single member, such as $\{ H \}$, will usually be written without the containing braces.

Henceforth we think of events as subsets of the sample space $\Omega$. Whenever $A$ and $B$ are events in which we are interested, then we can reasonably concern ourselves also with the events $A \cup B, A \cap B$, and $A^{ c }$, representing ' $A$ or $B^{\prime}$, ' $A$ and $B^{\prime}$, and 'not $A^{\prime}$ respectively. Events $A$ and $B$ are called disjoint if their intersection is the empty set $\varnothing ; \varnothing$ is called the impossible event. The set $\Omega$ is called the certain event, since some member of $\Omega$ will certainly occur.

Thus events are subsets of $\Omega$, but need all the subsets of $\Omega$ be events? The answer is no, but some of the reasons for this are too difficult to be discussed here. It suffices for us to think of the collection of events as a subcollection $F$ of the set of all subsets of $\Omega$. This subcollection should have certain properties in accordance with the earlier discussion:
(a) if $A, B \in F$ then $A \cup B \in F$ and $A \cap B \in F$;
(b) if $A \in F$ then $A^{ c } \in F$;
(c) the empty set $\varnothing$ belongs to $F$.

Any collection $F$ of subsets of $\Omega$ which satisfies these three conditions is called a field. It follows from the properties of a field $F$ that

$$
\text { if } \quad A_{1}, A_{2}, \ldots, A_{n} \in F \quad \text { then } \bigcup_{i=1}^{n} A_{i} \in F ;
$$
| Typical notation | Set jargon | Probability jargon |
| :--- | :--- | :--- |
| $\Omega$ | Collection of objects | Sample space |
| $\omega$ | Member of $\Omega$ | Elementary event, outcome |
| A | Subset of $\Omega$ | Event that some outcome in $A$ occurs |
| $A^{ c }$ | Complement of $A$ | Event that no outcome in $A$ occurs |
| $A \cap B$ | Intersection | Both $A$ and $B$ |
| $A \cup B$ | Union | Either $A$ or $B$ or both |
| $A \backslash B$ | Difference | $A$, but not $B$ |
| $A \triangle B$ | Symmetric difference | Either $A$ or $B$, but not both |
| $A \subseteq B$ | Inclusion | If $A$, then $B$ |
| $\varnothing$ | Empty set | Impossible event |
| $\Omega$ | Whole space | Certain event |

Table 1.1. The jargon of set theory and probability theory.

that is to say, $F$ is closed under finite unions and hence under finite intersections also (see Problem (1.8.3)). This is fine when $\Omega$ is a finite set, but we require slightly more to deal with the common situation when $\Omega$ is infinite, as the following example indicates.
(4) Example. A coin is tossed repeatedly until the first head turns up; we are concerned with the number of tosses before this happens. The set of all possible outcomes is the set $\Omega=\left\{\omega_{1}, \omega_{2}, \omega_{3}, \ldots\right\}$, where $\omega_{i}$ denotes the outcome when the first $i-1$ tosses are tails and the $i$ th toss is a head. We may seek to assign a probability to the event $A$, that the first head occurs after an even number of tosses, that is, $A=\left\{\omega_{2}, \omega_{4}, \omega_{6}, \ldots\right\}$. This is an infinite countable union of members of $\Omega$ and we require that such a set belong to $F$ in order that we can discuss its probability. $\square$

Thus we also require that the collection of events be closed under the operation of taking countable unions. Any collection of subsets of $\Omega$ with these properties is called a $\sigma$-field.
(5) Definition. A collection $F$ of subsets of $\Omega$ is called a $\sigma$-field if it satisfies the following conditions:
(a) $\varnothing \in F$;
(b) if $A_{1}, A_{2}, \ldots \in F$ then $\bigcup_{i=1}^{\infty} A_{i} \in F$;
(c) if $A \in F$ then $A^{ c } \in F$.

It follows from Problem (1.8.3) that $\sigma$-fields are closed under the operation of taking countable intersections. Here are some examples of $\sigma$-fields.
(6) Example. The smallest $\sigma$-field associated with $\Omega$ is the collection $F =\{\varnothing, \Omega\}$. $\square$
(7) Example. If $A$ is any subset of $\Omega$ then $F =\left\{\varnothing, A, A^{ c }, \Omega\right\}$ is a $\sigma$-field. $\square$
(8) Example. The power set of $\Omega$, which is written $\{0,1\}^{\Omega}$ and contains all subsets of $\Omega$, is obviously a $\sigma$-field. For reasons beyond the scope of this book, when $\Omega$ is infinite, its power set is too large a collection for probabilities to be assigned reasonably to all its members. $\square$

To recapitulate, with any experiment we may associate a pair ( $\Omega, F$ ), where $\Omega$ is the set of all possible outcomes or elementary events and $F$ is a $\sigma$-field of subsets of $\Omega$ which contains all the events in whose occurrences we may be interested; henceforth, to call a set $A$ an event is equivalent to asserting that $A$ belongs to the $\sigma$-field in question. We usually translate statements about combinations of events into set-theoretic jargon; for example, the event that both $A$ and $B$ occur is written as $A \cap B$. Table 1.1 is a translation chart.

## Exercises for Section 1.2

1. Let $\left\{A_{i}: i \in I\right\}$ be a collection of sets. Prove 'De Morgan's Laws' † :

$$
\left(\bigcup_{i} A_{i}\right)^{c}=\bigcap_{i} A_{i}^{c}, \quad\left(\bigcap_{i} A_{i}\right)^{c}=\bigcup_{i} A_{i}^{c} .
$$

2. Let $A$ and $B$ belong to some $\sigma$-field $F$. Show that $F$ contains the sets $A \cap B, A \backslash B$, and $A \triangle B$.
3. A conventional knock-out tournament (such as that at Wimbledon) begins with $2^{n}$ competitors and has $n$ rounds. There are no play-offs for the positions $2,3, \ldots, 2^{n}-1$, and the initial table of draws is specified. Give a concise description of the sample space of all possible outcomes.
4. Let $F$ be a $\sigma$-field of subsets of $\Omega$ and suppose that $B \in F$. Show that $Q =\{A \cap B: A \in F \}$ is a $\sigma$-field of subsets of $B$.
5. Which of the following are identically true? For those that are not, say when they are true.
(a) $A \cup(B \cap C)=(A \cup B) \cap(A \cup C)$;
(b) $A \cap(B \cap C)=(A \cap B) \cap C$;
(c) $(A \cup B) \cap C=A \cup(B \cap C)$;
(d) $A \backslash(B \cap C)=(A \backslash B) \cup(A \backslash C)$.

### Probability

We wish to be able to discuss the likelihoods of the occurrences of events. Suppose that we repeat an experiment a large number $N$ of times, keeping the initial conditions as equal as possible, and suppose that $A$ is some event which may or may not occur on each repetition. Our experience of most scientific experimentation is that the proportion of times that $A$ occurs settles down to some value as $N$ becomes larger and larger; that is to say, writing $N(A)$ for the number of occurrences of $A$ in the $N$ trials, the ratio $N(A) / N$ appears to converge to a constant limit as $N$ increases. We can think of the ultimate value of this ratio as being the probability $P (A)$ that $A$ occurs on any particular trial ‡ ; it may happen that the empirical ratio does not behave in a coherent manner and our intuition fails us at this level, but we shall not discuss this here. In practice, $N$ may be taken to be large but finite, and the ratio $N(A) / N$ may be taken as an approximation to $P (A)$. Clearly, the ratio is a number between zero and one; if $A=\varnothing$ then $N(\varnothing)=0$ and the ratio is 0 , whilst if $A=\Omega$ then $N(\Omega)=N$ and the

[^0]ratio is 1 . Furthermore, suppose that $A$ and $B$ are two disjoint events, each of which may or may not occur at each trial. Then
$$
N(A \cup B)=N(A)+N(B)
$$
and so the ratio $N(A \cup B) / N$ is the sum of the two ratios $N(A) / N$ and $N(B) / N$. We now think of these ratios as representing the probabilities of the appropriate events. The above relations become
$$
P (A \cup B)= P (A)+ P (B), \quad P (\varnothing)=0, \quad P (\Omega)=1 .
$$

This discussion suggests that the probability function $P$ should be finitely additive, which is to say that

$$
\text { if } A_{1}, A_{2}, \ldots, A_{n} \text { are disjoint events, then } P \left(\bigcup_{i=1}^{n} A_{i}\right)=\sum_{i=1}^{n} P \left(A_{i}\right) \text {; }
$$

a glance at Example (1.2.4) suggests the more extensive property that $P$ be countably additive, in that the corresponding property should hold for countable collections $A_{1}, A_{2}, \ldots$ of disjoint events.

These relations are sufficient to specify the desirable properties of a probability function $P$ applied to the set of events. Any such assignment of likelihoods to the members of $F$ is called a probability measure. Some individuals refer informally to $P$ as a 'probability distribution', especially when the sample space is finite or countably infinite; this practice is best avoided since the term 'probability distribution' is reserved for another purpose to be encountered in Chapter 2.
(1) Definition, A probability measure $P$ on $(\Omega, F )$ is a function $P : F \rightarrow[0,1]$ satisfying
(a) $P (\varnothing)=0, \quad P (\Omega)=1$;
(b) if $A_{1}, A_{2}, \ldots$ is a collection of disjoint members of $F$, in that $A_{i} \cap A_{j}=\varnothing$ for all pairs $i, j$ satisfying $i \neq j$, then

$$
P \left(\bigcup_{i=1}^{\infty} A_{i}\right)=\sum_{i=1}^{\infty} P \left(A_{i}\right) .
$$

The triple ( $\Omega, F , P$ ), comprising a set $\Omega$, a $\sigma$-field $F$ of subsets of $\Omega$, and a probability measure $P$ on ( $\Omega, F$ ), is called a probability space.

A probability measure is a special example of what is called a measure on the pair ( $\Omega, F$ ). A measure is a function $\mu: F \rightarrow[0, \infty)$ satisfying $\mu(\varnothing)=0$ together with (b) above. A measure $\mu$ is a probability measure if $\mu(\Omega)=1$.

We can associate a probability space ( $\Omega, F , P$ ) with any experiment, and all questions associated with the experiment can be reformulated in terms of this space. It may seem natural to ask for the numerical value of the probability $P (A)$ of some event $A$. The answer to such a question must be contained in the description of the experiment in question. For example, the assertion that a fair coin is tossed once is equivalent to saying that heads and tails have an equal probability of occurring; actually, this is the definition of fairness.
(2) Example. A coin, possibly biased, is tossed once. We can take $\Omega=\{ H , T \}$ and $F = \{\varnothing, H , T , \Omega\}$, and a possible probability measure $P : F \rightarrow[0,1]$ is given by

$$
P (\varnothing)=0, \quad P (H)=p, \quad P (T)=1-p, \quad P (\Omega)=1,
$$

where $p$ is a fixed real number in the interval $[0,1]$. If $p=\frac{1}{2}$, then we say that the coin is fair, or unbiased.
(3) Example. A die is thrown once. We can take $\Omega=\{1,2,3,4,5,6\}, F =\{0,1\}^{\Omega}$, and the probability measure $P$ given by

$$
P (A)=\sum_{i \in A} p_{i} \quad \text { for any } A \subseteq \Omega,
$$

where $p_{1}, p_{2}, \ldots, p_{6}$ are specified numbers from the interval $[0,1]$ having unit sum. The probability that $i$ turns up is $p_{i}$. The die is fair if $p_{i}=\frac{1}{6}$ for each $i$, in which case

$$
P (A)=\frac{1}{6}|A| \quad \text { for any } A \subseteq \Omega
$$

where $|A|$ denotes the cardinality of $A$.
The triple $(\Omega, F , P )$ denotes a typical probability space. We now give some of its simple but important properties.

## (4) Lemma.

(a) $P \left(A^{ c }\right)=1- P (A)$,
(b) if $B \supseteq A$ then $P (B)= P (A)+ P (B \backslash A) \geq P (A)$,
(c) $P (A \cup B)= P (A)+ P (B)- P (A \cap B)$,
(d) more generally, if $A_{1}, A_{2}, \ldots, A_{n}$ are events, then

$$
\begin{aligned}
P \left(\bigcup_{i=1}^{n} A_{i}\right)= & \sum_{i} P \left(A_{i}\right)-\sum_{i<j} P \left(A_{i} \cap A_{j}\right)+\sum_{i<j<k} P \left(A_{i} \cap A_{j} \cap A_{k}\right)-\cdots \\
& +(-1)^{n+1} P \left(A_{1} \cap A_{2} \cap \cdots \cap A_{n}\right)
\end{aligned}
$$

where, for example, $\sum_{i<j}$ sums over all unordered pairs $(i, j)$ with $i \neq j$.

## Proof.

(a) $A \cup A^{ c }=\Omega$ and $A \cap A^{ c }=\varnothing$, so $P \left(A \cup A^{ c }\right)= P (A)+ P \left(A^{ c }\right)=1$.
(b) $B=A \cup(B \backslash A)$. This is the union of disjoint sets and therefore

$$
P (B)= P (A)+ P (B \backslash A)
$$

(c) $A \cup B=A \cup(B \backslash A)$, which is a disjoint union. Therefore, by (b),

$$
\begin{aligned}
P (A \cup B) & = P (A)+ P (B \backslash A)= P (A)+ P (B \backslash(A \cap B)) \\
& = P (A)+ P (B)- P (A \cap B)
\end{aligned}
$$

(d) The proof is by induction on $n$, and is left as an exercise (see Exercise (1.3.4)).

In Lemma (4b), $B \backslash A$ denotes the set of members of $B$ which are not in $A$. In order to write down the quantity $P (B \backslash A)$, we require that $B \backslash A$ belongs to $F$, the domain of $P$; this is always true when $A$ and $B$ belong to $F$, and to prove this was part of Exercise (1.2.2). Notice that each proof proceeded by expressing an event in terms of disjoint unions and then applying $P$. It is sometimes easier to calculate the probabilities of intersections of events rather than their unions; part (d) of the lemma is useful then, as we shall discover soon. The next property of $P$ is more technical, and says that $P$ is a continuous set function; this property is essentially equivalent to the condition that $P$ is countably additive rather than just finitely additive (see Problem (1.8.16) also).
(5) Lemma. Let $A_{1}, A_{2}, \ldots$ be an increasing sequence of events, so that $A_{1} \subseteq A_{2} \subseteq A_{3} \subseteq \cdots$, and write $A$ for their limit:

$$
A=\bigcup_{i=1}^{\infty} A_{i}=\lim _{i \rightarrow \infty} A_{i}
$$

Then $P (A)=\lim _{i \rightarrow \infty} P \left(A_{i}\right)$.
Similarly, if $B_{1}, B_{2}, \ldots$ is a decreasing sequence of events, so that $B_{1} \supseteq B_{2} \supseteq B_{3} \supseteq \cdots$, then

$$
B=\bigcap_{i=1}^{\infty} B_{i}=\lim _{i \rightarrow \infty} B_{i}
$$

satisfies $P (B)=\lim _{i \rightarrow \infty} P \left(B_{i}\right)$.
Proof. $A=A_{1} \cup\left(A_{2} \backslash A_{1}\right) \cup\left(A_{3} \backslash A_{2}\right) \cup \cdots$ is the union of a disjoint family of events. Thus, by Definition (1),

$$
\begin{aligned}
P (A) & = P \left(A_{1}\right)+\sum_{i=1}^{\infty} P \left(A_{i+1} \backslash A_{i}\right) \\
& = P \left(A_{1}\right)+\lim _{n \rightarrow \infty} \sum_{i=1}^{n-1}\left[ P \left(A_{i+1}\right)- P \left(A_{i}\right)\right] \\
& =\lim _{n \rightarrow \infty} P \left(A_{n}\right)
\end{aligned}
$$

To show the result for decreasing families of events, take complements and use the first part (exercise).

To recapitulate, statements concerning chance are implicitly related to experiments or trials, the outcomes of which are not entirely predictable. With any such experiment we can associate a probability space ( $\Omega, F , P$ ) the properties of which are consistent with our shared and reasonable conceptions of the notion of chance.

Here is some final jargon. An event $A$ is called null if $P (A)=0$. If $P (A)=1$, we say that $A$ occurs almost surely. Null events should not be confused with the impossible event $\varnothing$. Null events are happening all around us, even though they have zero probability; after all, what is the chance that a dart strikes any given point of the target at which it is thrown? That is, the impossible event is null, but null events need not be impossible.

## Exercises for Section 1.3

1. Let $A$ and $B$ be events with probabilities $P (A)=\frac{3}{4}$ and $P (B)=\frac{1}{3}$. Show that $\frac{1}{12} \leq P (A \cap B) \leq \frac{1}{3}$, and give examples to show that both extremes are possible. Find corresponding bounds for $P (A \cup B)$.
2. A fair coin is tossed repeatedly. Show that, with probability one, a head turns up sooner or later. Show similarly that any given finite sequence of heads and tails occurs eventually with probability one. Explain the connection with Murphy's Law.
3. Six cups and saucers come in pairs: there are two cups and saucers which are red, two white, and two with stars on. If the cups are placed randomly onto the saucers (one each), find the probability that no cup is upon a saucer of the same pattern.
4. Let $A_{1}, A_{2}, \ldots, A_{n}$ be events where $n \geq 2$, and prove that

$$
\begin{aligned}
& P \left(\bigcup_{i=1}^{n} A_{i}\right)=\sum_{i} P \left(A_{i}\right)-\sum_{i<j} P \left(A_{i} \cap A_{j}\right)+\sum_{i<j<k} P \left(A_{i} \cap A_{j} \cap A_{k}\right) \\
&-\cdots+(-1)^{n+1} P \left(A_{1} \cap A_{2} \cap \cdots \cap A_{n}\right) .
\end{aligned}
$$

In each packet of Corn Flakes may be found a plastic bust of one of the last five Vice-Chancellors of Cambridge University, the probability that any given packet contains any specific Vice-Chancellor being $\frac{1}{5}$, independently of all other packets. Show that the probability that each of the last three Vice-Chancellors is obtained in a bulk purchase of six packets is $1-3\left(\frac{4}{5}\right)^{6}+3\left(\frac{3}{5}\right)^{6}-\left(\frac{2}{5}\right)^{6}$.
5. Let $A_{r}, r \geq 1$, be events such that $P \left(A_{r}\right)=1$ for all $r$. Show that $P \left(\cap_{r=1}^{\infty} A_{r}\right)=1$.
6. You are given that at least one of the events $A_{r}, l \leq r \leq n$, is certain to occur, but certainly no more than two occur. If $P \left(A_{r}\right)=p$, and $P \left(A_{r} \cap A_{s}\right)=q, r \neq s$, show that $p \geq 1 / n$ and $q \leq 2 / n$.
7. You are given that at least one, but no more than three, of the events $A_{r}, 1 \leq r \leq n$, occur, where $n \geq 3$. The probability of at least two occurring is $\frac{1}{2}$. If $P \left(A_{r}\right)=p, P \left(A_{r} \cap A_{s}\right)=q, r \neq s$, and $P \left(A_{r} \cap A_{s} \cap A_{t}\right)=x, r<s<t$, show that $p \geq 3 /(2 n)$, and $q \leq 4 / n$.

### Conditional probability

Many statements about chance take the form 'if $B$ occurs, then the probability of $A$ is $p$ ', where $B$ and $A$ are events (such as 'it rains tomorrow' and 'the bus being on time' respectively) and $p$ is a likelihood as before. To include this in our theory, we return briefly to the discussion about proportions at the beginning of the previous section. An experiment is repeated $N$ times, and on each occasion we observe the occurrences or non-occurrences of two events $A$ and $B$. Now, suppose we only take an interest in those outcomes for which $B$ occurs; all other experiments are disregarded. In this smaller collection of trials the proportion of times that $A$ occurs is $N(A \cap B) / N(B)$, since $B$ occurs at each of them. However,

$$
\frac{N(A \cap B)}{N(B)}=\frac{N(A \cap B) / N}{N(B) / N} .
$$

If we now think of these ratios as probabilities, we see that the probability that $A$ occurs, given that $B$ occurs, should be reasonably defined as $P (A \cap B) / P (B)$.

Probabilistic intuition leads to the same conclusion. Given that an event $B$ occurs, it is the case that $A$ occurs if and only if $A \cap B$ occurs. Thus the conditional probability of $A$ given $B$
should be proportional to $P (A \cap B)$, which is to say that it equals $\alpha P (A \cap B)$ for some constant $\alpha=\alpha(B)$. The conditional probability of $\Omega$ given $B$ must equal 1 , and thus $\alpha P (\Omega \cap B)=1$, yielding $\alpha=1 / P (B)$.

We formalize these notions as follows.
(1) Definition. If $P (B)>0$ then the conditional probability that $A$ occurs given that $B$ occurs is defined to be

$$
P (A \mid B)=\frac{ P (A \cap B)}{ P (B)} .
$$

We denote this conditional probability by $P (A \mid B)$, pronounced 'the probability of $A$ given $B$ ', or sometimes 'the probability of $A$ conditioned (or conditional) on $B$ '.
(2) Example. Two fair dice are thrown. Given that the first shows 3, what is the probability that the total exceeds 6? The answer is obviously $\frac{1}{2}$, since the second must show 4, 5, or 6. However, let us labour the point. Clearly $\Omega=\{1,2,3,4,5,6\}^{2}$, the set $\dagger$ of all ordered pairs $(i, j)$ for $i, j \in\{1,2, \ldots, 6\}$, and we can take $F$ to be the set of all subsets of $\Omega$, with $P (A)=|A| / 36$ for any $A \subseteq \Omega$. Let $B$ be the event that the first die shows 3, and $A$ be the event that the total exceeds 6 . Then

$$
B=\{(3, b): 1 \leq b \leq 6\}, \quad A=\{(a, b): a+b>6\}, \quad A \cap B=\{(3,4),(3,5),(3,6)\},
$$

and

$$
P (A \mid B)=\frac{ P (A \cap B)}{ P (B)}=\frac{|A \cap B|}{|B|}=\frac{3}{6} .
$$

(3) Example. A family has two children. What is the probability that both are boys, given that at least one is a boy? The older and younger child may each be male or female, so there are four possible combinations of sexes, which we assume to be equally likely. Hence we can represent the sample space in the obvious way as

$$
\Omega=\{GG, GB, BG, BB\}
$$

where $P ( GG )= P ( BB )= P ( GB )= P ( BG )=\frac{1}{4}$. From the definition of conditional probability,

$$
\begin{aligned}
P (BB \mid \text { one boy at least }) & = P (BB \mid GB \cup BG \cup BB) \\
& =\frac{ P (BB \cap(GB \cup BG \cup BB))}{ P (GB \cup BG \cup BB)} \\
& =\frac{ P (BB)}{ P (GB \cup BG \cup BB)}=\frac{1}{3}
\end{aligned}
$$

A popular but incorrect answer to the question is $\frac{1}{2}$. This is the correct answer to another question: for a family with two children, what is the probability that both are boys given that the younger is a boy? In this case,

$$
\begin{aligned}
P (BB \mid \text { younger is a boy }) & = P (BB \mid GB \cup BB) \\
& =\frac{ P (BB \cap(GB \cup BB))}{ P (GB \cup BB)}=\frac{ P (BB)}{ P (GB \cup BB)}=\frac{1}{2}
\end{aligned}
$$

[^1]The usual dangerous argument contains the assertion

$$
P (BB \mid \text { one child is a boy })= P (\text { other child is a boy }) .
$$

Why is this meaningless? [Hint: Consider the sample space.] $\square$

The next lemma is crucially important in probability theory. A family $B_{1}, B_{2}, \ldots, B_{n}$ of events is called a partition of the set $\Omega$ if

$$
B_{i} \cap B_{j}=\varnothing \quad \text { when } \quad i \neq j, \quad \text { and } \quad \bigcup_{i=1}^{n} B_{i}=\Omega .
$$

Each elementary event $\omega \in \Omega$ belongs to exactly one set in a partition of $\Omega$.
(4) Lemma. For any events $A$ and $B$ such that $0< P (B)<1$,

$$
P (A)= P (A \mid B) P (B)+ P \left(A \mid B^{ C }\right) P \left(B^{ C }\right) .
$$

More generally, let $B_{1}, B_{2}, \ldots, B_{n}$ be a partition of $\Omega$ such that $P \left(B_{i}\right)>0$ for all $i$. Then

$$
P (A)=\sum_{i=1}^{n} P \left(A \mid B_{i}\right) P \left(B_{i}\right) .
$$

Proof. $A=(A \cap B) \cup\left(A \cap B^{ c }\right)$. This is a disjoint union and so

$$
\begin{aligned}
P (A) & = P (A \cap B)+ P \left(A \cap B^{c}\right) \\
& = P (A \mid B) P (B)+ P \left(A \mid B^{c}\right) P \left(B^{c}\right) .
\end{aligned}
$$

The second part is similar (see Problem (1.8.10)). $\square$
(5) Example. We are given two urns, each containing a collection of coloured balls. Urn I contains two white and three blue balls, whilst urn II contains three white and four blue balls. A ball is drawn at random from urn I and put into urn II, and then a ball is picked at random from urn II and examined. What is the probability that it is blue? We assume unless otherwise specified that a ball picked randomly from any urn is equally likely to be any of those present. The reader will be relieved to know that we no longer need to describe ( $\Omega, F , P$ ) in detail; we are confident that we could do so if necessary. Clearly, the colour of the final ball depends on the colour of the ball picked from urn I. So let us 'condition' on this. Let $A$ be the event that the final ball is blue, and let $B$ be the event that the first one picked was blue. Then, by Lemma (4),

$$
P (A)= P (A \mid B) P (B)+ P \left(A \mid B^{c}\right) P \left(B^{c}\right) .
$$

We can easily find all these probabilities:

$$
\begin{gathered}
P (A \mid B)= P (A \mid \text { urn II contains three white and five blue balls })=\frac{5}{8}, \\
P \left(A \mid B^{c}\right)= P (A \mid \text { urn II contains four white and four blue balls })=\frac{1}{2}, \\
P (B)=\frac{3}{5}, \quad P \left(B^{c}\right)=\frac{2}{5} .
\end{gathered}
$$

Hence

$$
P (A)=\frac{5}{8} \cdot \frac{3}{5}+\frac{1}{2} \cdot \frac{2}{5}=\frac{23}{40} .
$$ $\square$

Unprepared readers may have been surprised by the sudden appearance of urns in this book. In the seventeenth and eighteenth centuries, lotteries often involved the drawing of slips from urns, and voting was often a matter of putting slips or balls into urns. In France today, aller aux urnes is synonymous with voting. It was therefore not unnatural for the numerous Bernoullis and others to model births, marriages, deaths, fluids, gases, and so on, using urns containing balls of varied hue.
(6) Example. Only two factories manufacture zoggles. 20 per cent of the zoggles from factory I and 5 per cent from factory II are defective. Factory I produces twice as many zoggles as factory II each week. What is the probability that a zoggle, randomly chosen from a week's production, is satisfactory? Clearly this satisfaction depends on the factory of origin. Let $A$ be the event that the chosen zoggle is satisfactory, and let $B$ be the event that it was made in factory I. Arguing as before,

$$
\begin{aligned}
P (A) & = P (A \mid B) P (B)+ P \left(A \mid B^{c}\right) P \left(B^{c}\right) \\
& =\frac{4}{5} \cdot \frac{2}{3}+\frac{19}{20} \cdot \frac{1}{3}=\frac{51}{60} .
\end{aligned}
$$

If the chosen zoggle is defective, what is the probability that it came from factory I? In our notation this is just $P \left(B \mid A^{ c }\right)$. However,

$$
P \left(B \mid A^{c}\right)=\frac{ P \left(B \cap A^{c}\right)}{ P \left(A^{c}\right)}=\frac{ P \left(A^{c} \mid B\right) P (B)}{ P \left(A^{c}\right)}=\frac{\frac{1}{5} \cdot \frac{2}{3}}{1-\frac{51}{60}}=\frac{8}{9} .
$$ $\square$

This section is terminated with a cautionary example. It is not untraditional to perpetuate errors of logic in calculating conditional probabilities. Lack of unambiguous definitions and notation has led astray many probabilists, including even Boole, who was credited by Russell with the discovery of pure mathematics and by others for some of the logical foundations of computing. The well-known 'prisoners' paradox' also illustrates some of the dangers here.
(7) Example. Prisoners' paradox. In a dark country, three prisoners have been incarcerated without trial. Their warder tells them that the country's dictator has decided arbitrarily to free one of them and to shoot the other two, but he is not permitted to reveal to any prisoner the fate of that prisoner. Prisoner A knows therefore that his chance of survival is $\frac{1}{3}$. In order to gain information, he asks the warder to tell him in secret the name of some prisoner (but not himself) who will be killed, and the warder names prisoner B. What now is prisoner A's assessment of the chance that he will survive? Could it be $\frac{1}{2}$ : after all, he knows now that the survivor will be either A or C , and he has no information about which? Could it be $\frac{1}{3}$ : after all, according to the rules, at least one of B and C has to be killed, and thus the extra information cannot reasonably affect A's earlier calculation of the odds? What does the reader think about this? The resolution of the paradox lies in the situation when either response (B or C) is possible.

An alternative formulation of this paradox has become known as the Monty Hall problem, the controversy associated with which has been provoked by Marilyn vos Savant (and many others) in Parade magazine in 1990; see Exercise (1.4.5). $\square$

## Exercises for Section 1.4

1. Prove that $P (A \mid B)= P (B \mid A) P (A) / P (B)$ whenever $P (A) P (B) \neq 0$. Show that, if $P (A \mid B)> P (A)$, then $P (B \mid A)> P (B)$.
2. For events $A_{1}, A_{2}, \ldots, A_{n}$ satisfying $P \left(A_{1} \cap A_{2} \cap \cdots \cap A_{n-1}\right)>0$, prove that

$$
P \left(A_{1} \cap A_{2} \cap \cdots \cap A_{n}\right)= P \left(A_{1}\right) P \left(A_{2} \mid A_{1}\right) P \left(A_{3} \mid A_{1} \cap A_{2}\right) \cdots P \left(A_{n} \mid A_{1} \cap A_{2} \cap \cdots \cap A_{n-1}\right) .
$$

3. A man possesses five coins, two of which are double-headed, one is double-tailed, and two are normal. He shuts his eyes, picks a coin at random, and tosses it. What is the probability that the lower face of the coin is a head?

He opens his eyes and sees that the coin is showing heads; what is the probability that the lower face is a head?

He shuts his eyes again, and tosses the coin again. What is the probability that the lower face is a head?

He opens his eyes and sees that the coin is showing heads; what is the probability that the lower face is a head?

He discards this coin, picks another at random, and tosses it. What is the probability that it shows heads?
4. What do you think of the following 'proof' by Lewis Carroll that an urn cannot contain two balls of the same colour? Suppose that the urn contains two balls, each of which is either black or white; thus, in the obvious notation, $P ( BB )= P ( BW )= P ( WB )= P ( WW )=\frac{1}{4}$. We add a black ball, so that $P ( BBB )= P ( BBW )= P ( BWB )= P ( BW )=\frac{1}{4}$. Next we pick a ball at random; the chance that the ball is black is (using conditional probabilities) $1 \cdot \frac{1}{4}+\frac{2}{3} \cdot \frac{1}{4}+\frac{2}{3} \cdot \frac{1}{4}+\frac{1}{3} \cdot \frac{1}{4}=\frac{2}{3}$. However, if there is probability $\frac{2}{3}$ that a ball, chosen randomly from three, is black, then there must be two black and one white, which is to say that originally there was one black and one white ball in the urn.
5. The Monty Hall problem: goats and cars. (a) Cruel fate has made you a contestant in a game show; you have to choose one of three doors. One conceals a new car, two conceal old goats. You choose, but your chosen door is not opened immediately. Instead, the presenter opens another door to reveal a goat, and he offers you the opportunity to change your choice to the third door (unopened and so far unchosen). Let $p$ be the (conditional) probability that the third door conceals the car. The value of $p$ depends on the presenter's protocol. Devise protocols to yield the values $p=\frac{1}{2}, p=\frac{2}{3}$. Show that, for $\alpha \in\left[\frac{1}{2}, \frac{2}{3}\right]$, there exists a protocol such that $p=\alpha$. Are you well advised to change your choice to the third door?
(b) In a variant of this question, the presenter is permitted to open the first door chosen, and to reward you with whatever lies behind. If he chooses to open another door, then this door invariably conceals a goat. Let $p$ be the probability that the unopened door conceals the car, conditional on the presenter having chosen to open a second door. Devise protocols to yield the values $p=0, p=1$, and deduce that, for any $\alpha \in[0,1]$, there exists a protocol with $p=\alpha$.
6. The prosecutor's fallacy †. Let $G$ be the event that an accused is guilty, and $T$ the event that some testimony is true. Some lawyers have argued on the assumption that $P (G \mid T)= P (T \mid G)$. Show that this holds if and only if $P (G)= P (T)$.
7. Urns. There are $n$ urns of which the $r$ th contains $r-1$ red balls and $n-r$ magenta balls. You pick an urn at random and remove two balls at random without replacement. Find the probability that:
(a) the second ball is magenta;
(b) the second ball is magenta, given that the first is magenta.

[^2]
### Independence

In general, the occurrence of some event $B$ changes the probability that another event $A$ occurs, the original probability $P (A)$ being replaced by $P (A \mid B)$. If the probability remains unchanged, that is to say $P (A \mid B)= P (A)$, then we call $A$ and $B$ 'independent'. This is well defined only if $P (B)>0$. Definition (1.4.1) of conditional probability leads us to the following.
(1) Definition. Events $A$ and $B$ are called independent if

$$
P (A \cap B)= P (A) P (B) .
$$

More generally, a family $\left\{A_{i}: i \in I\right\}$ is called independent if

$$
P \left(\bigcap_{i \in J} A_{i}\right)=\prod_{i \in J} P \left(A_{i}\right)
$$

for all finite subsets $J$ of $I$.
Remark. A common student error is to make the fallacious statement that $A$ and $B$ are independent if $A \cap B=\varnothing$.

If the family $\left\{A_{i}: i \in I\right\}$ has the property that

$$
P \left(A_{i} \cap A_{j}\right)= P \left(A_{i}\right) P \left(A_{j}\right) \quad \text { for all } i \neq j
$$

then it is called pairwise independent. Pairwise-independent families are not necessarily independent, as the following example shows.
(2) Example. Suppose $\Omega=\{a b c, a c b, c a b, c b a, b c a, b a c, a a a, b b b, c c c\}$, and each of the nine elementary events in $\Omega$ occurs with equal probability $\frac{1}{9}$. Let $A_{k}$ be the event that the $k$ th letter is $a$. It is left as an exercise to show that the family $\left\{A_{1}, A_{2}, A_{3}\right\}$ is pairwise independent but not independent. $\square$
(3) Example (1.4.6) revisited. The events $A$ and $B$ of this example are clearly dependent because $P (A \mid B)=\frac{4}{5}$ and $P (A)=\frac{51}{60}$. $\square$
(4) Example. Choose a card at random from a pack of 52 playing cards, each being picked with equal probability $\frac{1}{52}$. We claim that the suit of the chosen card is independent of its rank. For example,

$$
P (\text { king })=\frac{4}{52}, \quad P (\text { king } \mid \text { spade })=\frac{1}{13} .
$$

Alternatively,

$$
P (\text { spade king })=\frac{1}{52}=\frac{1}{4} \cdot \frac{1}{13}= P (\text { spade }) P (\text { king }) .
$$ $\square$

Let $C$ be an event with $P (C)>0$. To the conditional probability measure $P (\cdot \mid C)$ corresponds the idea of conditional independence. Two events $A$ and $B$ are called conditionally i

..._This content has been truncated to stay below 50000 characters_...