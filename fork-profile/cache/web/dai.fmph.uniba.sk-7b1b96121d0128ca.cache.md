# PII: 0004-3702(94)00041-X
URL: https://dai.fmph.uniba.sk/~sefranek/kri/dung.pdf

ELSEVIER Artificial Intelligence 77 (1995) 321-357

## Artificial Intelligence

### On the acceptability of arguments and its fundamental role in nonmonotonic reasoning, logic programming and n-person games*

Phan Minh Dung*

Division of Computer Science, Asian Institute of Technology, GPO Box 2754, Bangkok 10501, Thailand Received June 1993; revised April 1994

Abstract

The purpose of this paper is to study the fundamental mechanism, humans use in argumentation, and to explore ways to implement this mechanism on computers. We do so by first developing a theory for argumentation whose central notion is the acceptability of arguments. Then we argue for the âcorrectnessâ or âappropriatenessâ of our theory with two strong arguments. The first one shows that most of the major approaches to nonmonotonic reasoning in AI and logic programming are special forms of our theory of argumentation. The second argument illustrates how our theory can be used to investigate the logical structure of many practical problems. This argument is based on a result showing that our theory captures naturally the solutions of the theory of n-person games and of the well-known stable marriage problem. By showing that argumentation can be viewed as a special form of logic programming with negation as failure, we introduce a general logic-programming-based method for generating meta-interpreters for argumentation systems, a method very much similar to the compiler-compiler idea in conventional programming.

Keyword: Argumentation; Nonmonotonic reasoning; Logic programming; n-person games; The stable marriage problem

âThe true basis of the logic of existence and universality lies in the human activities of seeking and findingâ Jaakko Hintikka [24, p. 331

*The results in this paper (except those of Sections 3 and 4.3.2) have been published in condensed 
form in [15]. 
* E-mail: dung@cs.ait.ac.th. 

0004-3702/95/$09.50 0 1995 Elsevier Science B.V. All rights reserved SSDZ 0004-3702(94)00041-7

1. Introduction

Argumentation constitutes a major component of human intelligence. The ability to engage in arguments is essential for humans to understand new problems, to perform scientific reasoning, to express, clarify and defend their opinions in their daily lives. The way humans argue is based on a very simple principle which is summarized succinctly by an old saying: âThe one who has the last word laughs bestâ. To illustrate this principle, let us take a look at an example, a mock argument between two persons I and A, whose countries are at war, about who is responsible for blocking negotiation in their region.

Example 1.â 
I: My government cannot negotiate with your government because your 
government doesnât even recognize my government. 
A: Your government doesnât recognize my government either. 
The explicit content of Iâs utterance is that the failure of Aâs government to 
recognize Iâs government blocks the negotiation. This establishes the responsibili 
ty of Aâs governm