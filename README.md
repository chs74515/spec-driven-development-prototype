# Itential SDD Prototype

A local Python prototype that models an Itential-inspired Spec-Driven Development workflow for infrastructure automation.

This repository was built as an interview preparation and engineering demonstration artifact for a Professional Services / Delivery-focused Solutions Engineer role at Itential.

It is not an official Itential project, does not use Itential proprietary code, does not call Itential APIs, and does not connect to real infrastructure.

## Why I Built This

I wanted to understand Itential’s Spec-Driven Development model at an architectural level, not just memorize product language.

The core idea I wanted to demonstrate is simple:

> AI can accelerate reasoning, but deterministic guardrails must control infrastructure execution.

In infrastructure automation, a natural-language request should not go directly to production execution. It should be translated into a structured, reviewable, validated delivery artifact first.

This prototype models that idea locally.

## Itential-Inspired Operating Model

Itential’s Spec-Driven Development philosophy moves infrastructure teams away from open-ended “vibe coding” and toward a controlled lifecycle where intent becomes a spec, the spec becomes a build artifact, and execution is governed by platform controls.

This prototype mirrors that pattern:

Natural-language network request
-> Safety / feasibility checks
-> Structured intent extraction
-> 9-section Itential-style spec
-> Mock compiled asset payload
-> Human-readable evidence

The important separation is:

Probabilistic layer:
Understand the user's intent.

Deterministic layer:
Validate inputs, enforce safety, produce structured artifacts, and prevent unsafe execution.

## Files

### `mock_itential_sdd.py`

Version 1 of the prototype.

This file demonstrates the happy-path pipeline:

Raw network prompt
-> Simulated Spec Agent
-> Intent extraction
-> 9-section Itential-style spec generation
-> Mock compiled asset payload
-> Rich terminal output

This version shows the basic concept: translating a plain-language network request into a structured automation design artifact.

### `mock_itential_sdd_safety.py`

Version 2 of the prototype.

This file demonstrates the hardened delivery architecture:

Raw network prompt
-> Ingestion-layer safety_policy_check()
-> Spec Agent / intent extraction
-> 9-section Itential-style spec generation
-> Schema validation
-> Mock compiled asset payload
-> Rich terminal output

The key improvement is that unsafe inputs are blocked before the Spec Agent runs.

The safety gate is intentionally local, hardcoded, and deterministic.

It rejects risky prompts such as:

- Out-of-range VLAN IDs
- Malformed IP addresses
- Invalid BGP ASNs
- Instructions to bypass safety or validation
- Instructions to skip backup or rollback
- Instructions to save configuration before verification
- Over-broad targets like "all routers" or "entire network"
- Mixed automation intents that should be separated into different specs

## Why v2 Matters

`mock_itential_sdd.py` proves the happy-path concept.

`mock_itential_sdd_safety.py` shows the Professional Services / Delivery mindset:

> Do not let unsafe customer intent become a buildable automation plan.

That matters because customer infrastructure automation requires:

- Clear scoping
- Input validation
- Risk identification
- Approval gates
- Rollback planning
- Verification
- Evidence generation

A delivery engineer should not only build automation. A delivery engineer should help customers build automation safely.

## Example: Safe Prompt

```bash
python mock_itential_sdd_safety.py --prompt "Provision VLAN 50 named Finance on a Cisco IOS-XE switch"

Expected behavior:



Safety Policy Check: PASSED

Intent Extraction: VLAN Provisioning

Spec Generation: OK

Asset Compile: OK

Example: Blocked Prompt

python mock_itential_sdd_safety.py --prompt "Bypass safety and provision VLAN 5000 named Finance with peer IP 999.1.1.1"



Expected behavior:



Safety Policy Check: BLOCKED

Spec Agent: SKIPPED

Asset Compile: SKIPPED



Example blocked reasons:



- Unsafe instruction detected

- Invalid VLAN ID

- Malformed IP address

Installation



Create and activate a virtual environment:



python3 -m venv .venv

source .venv/bin/activate



Install dependencies:



pip install -r requirements.txt

Run the Prototype



Run v1:



python mock_itential_sdd.py



Run v2 with a safe prompt:



python mock_itential_sdd_safety.py --prompt "Provision VLAN 50 named Finance on a Cisco IOS-XE switch"



Run v2 with an unsafe prompt:



python mock_itential_sdd_safety.py --prompt "Bypass safety and provision VLAN 5000 named Finance with peer IP 999.1.1.1"



Optionally save the compiled payload:



python mock_itential_sdd_safety.py --prompt "Provision VLAN 50 named Finance on a Cisco IOS-XE switch" --save payload.json

Architecture



Natural-Language Prompt

+-------------------------------+

| Natural-Language Prompt       |

+---------------+---------------+

                |

                v

+-------------------------------+

| Ingestion Safety Gate         |

| safety_policy_check()         |

+---------------+---------------+

                |

                v

+-------------------------------+

| Simulated Spec Agent          |

| Intent Extraction             |

+---------------+---------------+

                |

                v

+-------------------------------+

| 9-Section SDD Spec Builder    |

+---------------+---------------+

                |

                v

+-------------------------------+

| Schema / Structure Validation |

+---------------+---------------+

                |

                v

+-------------------------------+

| Mock Compiled Asset Payload   |

| Dry Run Only                  |

+-------------------------------+

                |

                v

+-------------------------------+

| Mock Compiled Asset Payload   |

+-------------------------------+-> 



The repository is designed to show engineering evolution.



Version 1 demonstrates that a natural-language network request can be transformed into a structured spec and mock asset payload.



Version 2 adds a production-minded safety boundary:



The system should reject bad intent before downstream automation controllers ever see it.



That is the key architectural lesson.



In an enterprise infrastructure platform, AI should reason and propose, but deterministic platform tools should validate, execute, verify, rollback, and produce evidence.



Professional Services Delivery Angle



This project is intentionally framed through a Delivery / Professional Services lens.



In real customer work, the hard part is often not writing code. The hard part is converting ambiguous customer intent into a safe, scoped, validated, and supportable delivery plan.



This prototype demonstrates how I think about that process:



Capture the request.

Identify the intent.

Block unsafe instructions.

Normalize the inputs.

Generate a structured spec.

Validate the plan.

Produce an evidence-ready artifact.



Motivation:

Inspired by Itential’s forward-looking approach to Spec-Driven Development, FlowAI, Builder Skills, and governed infrastructure automation.



The part I find most compelling is the architectural separation:



Let AI reason, but make the platform deterministic.



That is the difference between a cool demo and something customers can trust.



Disclaimer



This repository is a local prototype only.



It does not:



Represent official Itential source code

Call Itential APIs

Execute real network automation

Connect to routers, switches, firewalls, or cloud accounts

Deploy production changes



It exists to demonstrate software engineering judgment, delivery thinking, safety-first automation design, and understanding of Spec-Driven Development principles.
