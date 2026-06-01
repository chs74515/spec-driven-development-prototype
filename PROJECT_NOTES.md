# Project Notes

## Why Two Versions Exist

This repository intentionally keeps two versions of the prototype side by side.

## v1: `mock_itential_sdd.py`

The first version demonstrates the happy-path idea:

Prompt -> Intent -> Spec -> Mock Payload

It proves the basic concept of converting natural language into a structured infrastructure automation artifact.

## v2: `mock_itential_sdd_safety.py`

The second version introduces a hard safety boundary before the Spec Agent:

Prompt -> Safety Gate -> Intent -> Spec -> Mock Payload

The safety gate blocks unsafe inputs before downstream automation logic runs.

## Architectural Lesson

The most important design decision is not the Python implementation.

The most important design decision is the boundary:

> Unsafe natural-language intent should not become a buildable automation plan.

That is the difference between a demo and an enterprise delivery architecture.

## Delivery Perspective

In Professional Services, customers often begin with ambiguous requests.

A strong delivery engineer must translate that ambiguity into:

- Validated inputs
- Clear assumptions
- Known risks
- Defined rollback behavior
- Reviewable designs
- Evidence-ready outputs

This prototype demonstrates that mindset in code.
