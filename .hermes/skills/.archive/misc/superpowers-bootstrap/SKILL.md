---
name: superpowers-bootstrap
description: Use when starting a coding session in Hermes and you want Superpowers workflow enforcement loaded before implementation begins.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bootstrap, superpowers, session-start, workflow]
    related_skills: [using-superpowers]
---

# Superpowers Bootstrap

This is the Hermes-friendly bootstrap wrapper for the Superpowers port.

## Purpose

Load this skill at the start of a coding session to force the question:
"Which skill should be used before I act?"

In Hermes, this does not install an automatic hidden session-start injector by itself. Instead, it is the explicit bootstrap entrypoint you can preload or invoke first.

## How to use

Preferred:
- start Hermes with `-s superpowers-bootstrap`
- or load `/skill superpowers-bootstrap` at the top of the session

After this skill is loaded:
1. immediately load `using-superpowers`
2. check whether another process skill applies before doing anything else
3. only then begin clarification, planning, coding, or verification

## Coding-session rule

If the user asks to build, fix, refactor, review, plan, or investigate code, treat `using-superpowers` as the default process layer unless the user or repo instructions clearly require a different workflow.

## Limitation

A true upstream-style automatic bootstrap would require harness-level session-start injection. This skill is the Hermes-session equivalent and should be preloaded explicitly when that behavior is desired.
