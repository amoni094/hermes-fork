# **Analogical Reasoning, Generalization, and Rule Learning for**
## **Common Law Reasoning**
### Northwestern University Evanston, Illinois, USA forbus@northwestern.edu
Research in AI & Law has sought to model common-law case- based reasoning by creating analogies from cases, extracting and applying rules from cases, or both.
This paper presents a new approach to extracting legal information from cases and several methods to apply that information to new cases, including by analogy and by converting what the system has learned into logical rules.
It evaluates these approaches on a recently introduced legal dataset and compares results to off-the-shelf machine-learning techniques.

...

**KEYWORDS**
Analogy, Precedential Reasoning, Rule Learning, Legal Schemas
**1** **Introduction and Background**
In Common Law legal systems, cases are resolved by reference to and consistent with prior decisions settling similar claims.

...

prior case in a jurisdiction concerns the same legal issues as some case at bar, the prior reasoning and decision governs the latter.
As one of the central pillars of the Western legal tradition, common law legal reasoning has been a focus of the AI & Law research community. This paper introduces a new approach to computational
precedential reasoning, inspired by and adapting tools from

...

from precedents, it also provides a method to determine what the content of rules actually are, as opposed to what a judge has said a rule is in any given case.

...

MAC/FAC first efficiently computes dot products between content vectors of the probe and each case in the library (a coarse measure of similarity). Up to three cases are then passed to SME, which returns up to three mappings between them and the probe.