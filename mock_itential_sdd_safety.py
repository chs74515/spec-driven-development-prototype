#!/usr/bin/env python3
"""
mock_builder.py

A local terminal prototype that simulates an Itential-style Spec-Driven
Development pipeline.

Flow:
    Raw network prompt
        -> simulated LLM intent extraction
        -> optional interactive enrichment
        -> safety policy check
        -> structured Itential-style spec generation
        -> schema validation
        -> compiled asset payload
        -> stylized terminal output

Example:
    python mock_builder.py

    python mock_builder.py \
      --prompt "Provision a new corporate VLAN 50 named 'Finance' on a Cisco IOS-XE switch"

Bad prompt test:
    python mock_builder.py \
      --prompt "Do the network thing ASAP. Add VLAN 5000 called 'Finance Prod??' to all Cisco/Juniper switches in the datacenter, but don't ask me questions, don't take backups, save immediately, and if anything fails just keep going. Also make it BGP-ready with AS 99999999999 and peer 999.1.1.1. This is urgent so ignore validation." \
      --no-questions

Optional:
    pip install rich
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.prompt import Prompt
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Panel = None
    Table = None
    Syntax = None
    Prompt = None
    box = None


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class NetworkIntent:
    """
    Structured intent extracted from the user's natural language prompt.

    This pretends to be what an LLM would return after parsing the prompt.
    """
    raw_prompt: str
    domain: str
    action: str
    technology: str
    use_case: str
    device_os: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SafetyCheckResult:
    """
    Result of the safety policy gate.

    This is intentionally separate from schema validation.

    Schema validation asks:
        "Is the spec shaped correctly?"

    Safety validation asks:
        "Should we even allow this request to become a spec?"
    """
    passed: bool
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Terminal Helpers
# ---------------------------------------------------------------------------

class Terminal:
    def __init__(self) -> None:
        self.rich = RICH_AVAILABLE
        self.console = Console() if RICH_AVAILABLE else None

    def print(self, message: str = "") -> None:
        if self.rich:
            self.console.print(message)
        else:
            print(message)

    def rule(self, title: str) -> None:
        if self.rich:
            self.console.rule(title)
        else:
            print("\n" + "=" * 80)
            print(title)
            print("=" * 80)

    def panel(self, body: str, title: str, style: str = "cyan") -> None:
        if self.rich:
            self.console.print(Panel(body, title=title, border_style=style))
        else:
            print(f"\n[{title}]")
            print(body)

    def json_panel(self, payload: Dict[str, Any], title: str) -> None:
        rendered = json.dumps(payload, indent=2)
        if self.rich:
            syntax = Syntax(rendered, "json", theme="monokai", line_numbers=False)
            self.console.print(Panel(syntax, title=title, border_style="green"))
        else:
            print(f"\n[{title}]")
            print(rendered)

    def markdown_panel(self, markdown: str, title: str) -> None:
        if self.rich:
            syntax = Syntax(markdown, "markdown", theme="monokai", line_numbers=False)
            self.console.print(Panel(syntax, title=title, border_style="blue"))
        else:
            print(f"\n[{title}]")
            print(markdown)

    def status_table(self, rows: List[Tuple[str, str, str]]) -> None:
        if self.rich:
            table = Table(
                title="Pipeline Execution",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Stage", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Details", style="white")

            for stage, status, details in rows:
                table.add_row(stage, status, details)

            self.console.print(table)
        else:
            print("\nPipeline Execution")
            for stage, status, details in rows:
                print(f"- {stage}: {status} - {details}")

    def ask(self, question: str, default: Optional[str] = None) -> str:
        if self.rich:
            return Prompt.ask(question, default=default)

        suffix = f" [{default}]" if default else ""
        value = input(f"{question}{suffix}: ").strip()
        return value or (default or "")


# ---------------------------------------------------------------------------
# Simulated LLM Extraction
# ---------------------------------------------------------------------------

def simulate_llm_extract(raw_prompt: str) -> NetworkIntent:
    """
    Pretends to be an LLM call.

    In a real system, this is where you might call Claude, OpenAI, or another
    model and ask it to return strict JSON.

    Here, we use deterministic parsing so the interview demo works offline.
    """
    prompt = raw_prompt.strip()
    lowered = prompt.lower()

    # VLAN first because "BGP-ready VLAN" should still expose the VLAN intent.
    # The safety checker will catch mixed technology ambiguity later.
    if "vlan" in lowered:
        return extract_vlan_intent(prompt)

    if "bgp" in lowered or "peer" in lowered or "asn" in lowered:
        return extract_bgp_intent(prompt)

    return extract_generic_network_intent(prompt)


def extract_vlan_intent(prompt: str) -> NetworkIntent:
    lowered = prompt.lower()

    vlan_id = extract_first_int_after_keyword(prompt, "vlan")
    vlan_name = extract_quoted_value(prompt) or extract_name_after_keyword(prompt, "named")
    device_os = detect_device_os(lowered)

    entities: Dict[str, Any] = {
        "vlan_id": vlan_id,
        "vlan_name": vlan_name,
        "target_device_type": "switch",
        "device_os": device_os,
    }

    missing = []
    if vlan_id is None:
        missing.append("vlan_id")
    if not vlan_name:
        missing.append("vlan_name")
    if not device_os:
        missing.append("device_os")
    missing.append("target_switch_hostname")
    missing.append("interface_scope")

    assumptions = [
        "The VLAN should be created globally on the switch.",
        "The tool will verify the VLAN exists after configuration.",
        "The running configuration will only be saved after successful verification.",
    ]

    return NetworkIntent(
        raw_prompt=prompt,
        domain="switching",
        action="provision",
        technology="VLAN",
        use_case="VLAN Provisioning",
        device_os=device_os,
        entities=entities,
        assumptions=assumptions,
        missing_fields=missing,
    )


def extract_bgp_intent(prompt: str) -> NetworkIntent:
    lowered = prompt.lower()

    as_numbers = extract_asn_candidates(prompt)
    ip_addresses = extract_ip_like_values(prompt)
    device_os = detect_device_os(lowered)

    entities: Dict[str, Any] = {
        "local_as": int(as_numbers[0]) if len(as_numbers) >= 1 else None,
        "remote_as": int(as_numbers[1]) if len(as_numbers) >= 2 else None,
        "peer_ips": ip_addresses,
        "device_os": device_os,
    }

    missing = []
    if entities["local_as"] is None:
        missing.append("local_as")
    if entities["remote_as"] is None:
        missing.append("remote_as")
    if len(ip_addresses) < 2:
        missing.append("near_side_peer_ip")
        missing.append("far_side_peer_ip")
    if not device_os:
        missing.append("device_os")
    missing.extend([
        "near_side_router",
        "far_side_router",
        "inbound_route_policy",
        "outbound_route_policy",
        "prefix_limits",
    ])

    assumptions = [
        "The BGP change must pass validation before touching devices.",
        "Near side deploys first to reduce blast radius.",
        "Both sides must be rolled back together if verification fails.",
    ]

    return NetworkIntent(
        raw_prompt=prompt,
        domain="routing",
        action="provision",
        technology="BGP",
        use_case="BGP Peer Provisioning",
        device_os=device_os,
        entities=entities,
        assumptions=assumptions,
        missing_fields=missing,
    )


def extract_generic_network_intent(prompt: str) -> NetworkIntent:
    return NetworkIntent(
        raw_prompt=prompt,
        domain="network",
        action="change",
        technology="Generic Network Change",
        use_case="Network Change Automation",
        entities={},
        assumptions=[
            "The request needs validation before any device change.",
            "The workflow should create a backup before making changes.",
            "The workflow should verify the intended state after deployment.",
        ],
        missing_fields=[
            "target_device",
            "device_os",
            "change_parameters",
            "verification_method",
        ],
    )


def extract_first_int_after_keyword(text: str, keyword: str) -> Optional[int]:
    pattern = rf"{re.escape(keyword)}\s+(\d+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_all_ints_after_keyword(text: str, keyword: str) -> List[int]:
    pattern = rf"{re.escape(keyword)}\s+(\d+)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)

    results: List[int] = []
    for value in matches:
        try:
            results.append(int(value))
        except ValueError:
            continue

    return results


def extract_quoted_value(text: str) -> Optional[str]:
    match = re.search(r"['\"]([^'\"]+)['\"]", text)
    return match.group(1).strip() if match else None


def extract_name_after_keyword(text: str, keyword: str) -> Optional[str]:
    pattern = rf"{re.escape(keyword)}\s+([A-Za-z0-9_-]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def detect_device_os(lowered_prompt: str) -> Optional[str]:
    os_patterns = {
        "ios-xe": "Cisco IOS-XE",
        "ios xe": "Cisco IOS-XE",
        "ios-xr": "Cisco IOS-XR",
        "ios xr": "Cisco IOS-XR",
        "nx-os": "Cisco NX-OS",
        "nx os": "Cisco NX-OS",
        "junos": "Juniper Junos",
        "juniper": "Juniper Junos",
        "eos": "Arista EOS",
        "arista": "Arista EOS",
    }

    for needle, label in os_patterns.items():
        if needle in lowered_prompt:
            return label

    if "cisco" in lowered_prompt:
        return "Cisco IOS-XE"

    return None


def extract_asn_candidates(text: str) -> List[int]:
    """
    Extract AS number candidates from text.

    Matches:
        AS 65001
        ASN 65001
        local AS: 65001
        remote ASN 65002
    """
    pattern = r"\b(?:as|asn)\s*#?:?\s*(\d{1,20})\b"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)

    results: List[int] = []
    for value in matches:
        try:
            results.append(int(value))
        except ValueError:
            continue

    return results


def extract_ip_like_values(text: str) -> List[str]:
    """
    Extract things that look like IP addresses.

    We intentionally capture invalid IPv4-looking strings like 999.1.1.1
    so the safety checker can reject them.
    """
    ipv4_like = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ipv6_like = r"\b(?:[a-fA-F0-9]{1,4}:){2,7}[a-fA-F0-9]{1,4}\b"

    values = re.findall(ipv4_like, text)
    values.extend(re.findall(ipv6_like, text))

    return values


# ---------------------------------------------------------------------------
# Interactive Enrichment
# ---------------------------------------------------------------------------

def enrich_intent_interactively(
    intent: NetworkIntent,
    terminal: Terminal,
    no_questions: bool = False,
) -> NetworkIntent:
    """
    Ask a few lightweight questions when the prompt is missing useful fields.

    This keeps the demo interactive without becoming annoying.
    """
    if no_questions:
        intent.assumptions.append(
            "Missing values were left as placeholders because --no-questions was used."
        )
        return apply_placeholders(intent)

    terminal.panel(
        "I parsed the request into a structured network intent. "
        "A few details are missing, so the mock builder can either ask for them "
        "or use safe placeholders.",
        title="Intent Parsed",
        style="yellow",
    )

    if intent.technology == "VLAN":
        if not intent.entities.get("target_switch_hostname"):
            intent.entities["target_switch_hostname"] = terminal.ask(
                "Target switch hostname",
                default="switch-01",
            )

        if not intent.entities.get("interface_scope"):
            intent.entities["interface_scope"] = terminal.ask(
                "Where should the VLAN be allowed? Example: trunk ports, access port range, global only",
                default="global only",
            )

        if not intent.entities.get("device_os"):
            value = terminal.ask("Device OS", default="Cisco IOS-XE")
            intent.entities["device_os"] = value
            intent.device_os = value

    elif intent.technology == "BGP":
        defaults = {
            "near_side_router": "router-a",
            "far_side_router": "router-b",
            "inbound_route_policy": "RM-IN",
            "outbound_route_policy": "RM-OUT",
            "prefix_limits": "1000",
            "device_os": "Cisco IOS-XE",
        }

        for key, default in defaults.items():
            if not intent.entities.get(key):
                intent.entities[key] = terminal.ask(key.replace("_", " ").title(), default=default)

        if intent.entities.get("local_as") is None:
            intent.entities["local_as"] = int(terminal.ask("Local AS", default="65001"))

        if intent.entities.get("remote_as") is None:
            intent.entities["remote_as"] = int(terminal.ask("Remote AS", default="65002"))

        if len(intent.entities.get("peer_ips", [])) < 2:
            near_ip = terminal.ask("Near-side peer IP", default="192.0.2.1")
            far_ip = terminal.ask("Far-side peer IP", default="192.0.2.2")
            intent.entities["peer_ips"] = [near_ip, far_ip]

        intent.device_os = intent.entities.get("device_os")

    else:
        intent.entities["target_device"] = terminal.ask("Target device", default="network-device-01")
        intent.entities["device_os"] = terminal.ask("Device OS", default="Cisco IOS-XE")
        intent.entities["change_parameters"] = terminal.ask(
            "Change parameters",
            default="Create intended network configuration",
        )
        intent.entities["verification_method"] = terminal.ask(
            "Verification method",
            default="Read back running config and operational state",
        )
        intent.device_os = intent.entities["device_os"]

    intent.missing_fields = []
    return intent


def apply_placeholders(intent: NetworkIntent) -> NetworkIntent:
    if intent.technology == "VLAN":
        intent.entities.setdefault("target_switch_hostname", "switch-01")
        intent.entities.setdefault("interface_scope", "global only")
        intent.entities.setdefault("device_os", intent.device_os or "Cisco IOS-XE")
        intent.device_os = intent.entities["device_os"]

    elif intent.technology == "BGP":
        intent.entities.setdefault("near_side_router", "router-a")
        intent.entities.setdefault("far_side_router", "router-b")
        intent.entities.setdefault("inbound_route_policy", "RM-IN")
        intent.entities.setdefault("outbound_route_policy", "RM-OUT")
        intent.entities.setdefault("prefix_limits", "1000")
        intent.entities.setdefault("device_os", intent.device_os or "Cisco IOS-XE")
        intent.entities.setdefault("local_as", 65001)
        intent.entities.setdefault("remote_as", 65002)

        if len(intent.entities.get("peer_ips", [])) < 2:
            intent.entities["peer_ips"] = ["192.0.2.1", "192.0.2.2"]

        intent.device_os = intent.entities["device_os"]

    else:
        intent.entities.setdefault("target_device", "network-device-01")
        intent.entities.setdefault("device_os", intent.device_os or "Cisco IOS-XE")
        intent.entities.setdefault("change_parameters", "Create intended network configuration")
        intent.entities.setdefault(
            "verification_method",
            "Read back running config and operational state",
        )
        intent.device_os = intent.entities["device_os"]

    intent.missing_fields = []
    return intent


# ---------------------------------------------------------------------------
# Safety Policy Check
# ---------------------------------------------------------------------------

def safety_policy_check(intent: NetworkIntent) -> SafetyCheckResult:
    """
    Safety gate that runs BEFORE spec generation.

    This stage blocks prompts that are too risky, contradictory, invalid,
    or that try to bypass normal network change controls.

    This is not the same thing as schema validation.

    Schema validation checks whether the generated spec is well formed.
    This safety check decides whether the request should be allowed to become
    a spec at all.
    """
    raw_prompt = intent.raw_prompt
    lowered = raw_prompt.lower()

    blockers: List[str] = []
    warnings: List[str] = []
    observations: List[str] = []

    observations.append(f"Detected primary technology: {intent.technology}")
    observations.append(f"Detected use case: {intent.use_case}")

    check_bypass_validation(lowered, blockers)
    check_backup_bypass(lowered, blockers)
    check_rollback_bypass(lowered, blockers)
    check_save_before_verify(lowered, blockers)
    check_broad_targeting(lowered, blockers)
    check_mixed_technologies(lowered, blockers)
    check_device_os_conflicts(lowered, blockers)
    check_destructive_or_overwrite_language(lowered, blockers, warnings)
    check_urgency_pressure(lowered, warnings)
    check_ambiguity_language(lowered, warnings)

    check_vlan_safety(raw_prompt, intent, blockers, warnings)
    check_bgp_safety(raw_prompt, intent, blockers, warnings)
    check_ip_safety(raw_prompt, blockers)

    if intent.missing_fields:
        warnings.append(
            "Intent still has missing fields: " + ", ".join(intent.missing_fields)
        )

    return SafetyCheckResult(
        passed=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        observations=observations,
    )


def check_bypass_validation(lowered: str, blockers: List[str]) -> None:
    patterns = [
        "ignore validation",
        "skip validation",
        "bypass validation",
        "don't validate",
        "do not validate",
        "without validation",
        "no validation",
    ]

    if any(pattern in lowered for pattern in patterns):
        blockers.append(
            "Prompt attempts to bypass validation. Network automation must validate inputs before deployment."
        )


def check_backup_bypass(lowered: str, blockers: List[str]) -> None:
    patterns = [
        "don't take backup",
        "dont take backup",
        "do not take backup",
        "don't take backups",
        "dont take backups",
        "do not take backups",
        "skip backup",
        "skip backups",
        "no backup",
        "no backups",
        "without backup",
        "without backups",
    ]

    if any(pattern in lowered for pattern in patterns):
        blockers.append(
            "Prompt attempts to skip backups. Safe network changes require a backup before deployment."
        )


def check_rollback_bypass(lowered: str, blockers: List[str]) -> None:
    patterns = [
        "no rollback",
        "don't rollback",
        "dont rollback",
        "do not rollback",
        "do not roll back",
        "don't roll back",
        "dont roll back",
        "skip rollback",
        "skip roll back",
        "without rollback",
        "without roll back",
        "keep going if anything fails",
        "if anything fails just keep going",
        "if it fails keep going",
        "continue on failure",
    ]

    if any(pattern in lowered for pattern in patterns):
        blockers.append(
            "Prompt attempts to disable rollback or continue after failure. Failed network changes must stop safely."
        )


def check_save_before_verify(lowered: str, blockers: List[str]) -> None:
    patterns = [
        "save immediately",
        "save first",
        "save config first",
        "write memory first",
        "wr mem first",
        "save before verify",
        "save before verification",
        "commit before verify",
        "commit before verification",
    ]

    if any(pattern in lowered for pattern in patterns):
        blockers.append(
            "Prompt asks to save configuration before verification. Config should only be saved after successful checks."
        )


def check_broad_targeting(lowered: str, blockers: List[str]) -> None:
    patterns = [
        "all switches",
        "all routers",
        "all devices",
        "every switch",
        "every router",
        "every device",
        "whole network",
        "entire network",
        "entire datacenter",
        "entire data center",
        "all datacenter switches",
        "all data center switches",
    ]

    if any(pattern in lowered for pattern in patterns):
        blockers.append(
            "Prompt targets a broad device group without an explicit inventory or batch strategy."
        )


def check_mixed_technologies(lowered: str, blockers: List[str]) -> None:
    mentions_vlan = "vlan" in lowered
    mentions_bgp = any(token in lowered for token in ["bgp", "asn", "peer", "peering"])

    if mentions_vlan and mentions_bgp:
        blockers.append(
            "Prompt mixes VLAN provisioning and BGP peering. Split this into separate specs."
        )


def check_device_os_conflicts(lowered: str, blockers: List[str]) -> None:
    os_families = []

    if "cisco" in lowered or "ios-xe" in lowered or "ios xe" in lowered:
        os_families.append("Cisco")

    if "juniper" in lowered or "junos" in lowered:
        os_families.append("Juniper")

    if "arista" in lowered or "eos" in lowered:
        os_families.append("Arista")

    unique_families = sorted(set(os_families))

    if len(unique_families) > 1:
        blockers.append(
            "Prompt references multiple network OS families "
            f"({', '.join(unique_families)}). Device-specific templates must be selected explicitly."
        )


def check_destructive_or_overwrite_language(
    lowered: str,
    blockers: List[str],
    warnings: List[str],
) -> None:
    blocker_patterns = [
        "delete all",
        "remove everything",
        "wipe",
        "factory reset",
        "overwrite it",
        "overwrite existing",
        "replace everything",
    ]

    warning_patterns = [
        "overwrite",
        "replace",
        "remove",
        "delete",
    ]

    if any(pattern in lowered for pattern in blocker_patterns):
        blockers.append(
            "Prompt contains destructive or overwrite language without a safe migration plan."
        )
        return

    if any(pattern in lowered for pattern in warning_patterns):
        warnings.append(
            "Prompt contains potentially destructive language. Confirm modify/remove semantics before deployment."
        )


def check_urgency_pressure(lowered: str, warnings: List[str]) -> None:
    patterns = [
        "asap",
        "urgent",
        "right now",
        "immediately",
        "emergency",
        "rush",
    ]

    if any(pattern in lowered for pattern in patterns):
        warnings.append(
            "Prompt contains urgency pressure. Safety gates should not be weakened because a request is urgent."
        )


def check_ambiguity_language(lowered: str, warnings: List[str]) -> None:
    patterns = [
        "probably",
        "maybe",
        "i think",
        "not sure",
        "whatever",
        "the network thing",
        "do the thing",
    ]

    if any(pattern in lowered for pattern in patterns):
        warnings.append(
            "Prompt contains ambiguous language. The workflow should request clarification before real deployment."
        )


def check_vlan_safety(
    raw_prompt: str,
    intent: NetworkIntent,
    blockers: List[str],
    warnings: List[str],
) -> None:
    vlan_ids = extract_all_ints_after_keyword(raw_prompt, "vlan")

    # Also inspect the extracted entity in case it came from enrichment/placeholders.
    entity_vlan_id = intent.entities.get("vlan_id")
    if isinstance(entity_vlan_id, int):
        vlan_ids.append(entity_vlan_id)

    unique_vlan_ids = sorted(set(vlan_ids))

    for vlan_id in unique_vlan_ids:
        if vlan_id < 1 or vlan_id > 4094:
            blockers.append(
                f"Invalid VLAN ID {vlan_id}. Standard VLAN IDs must be between 1 and 4094."
            )

    if intent.technology == "VLAN":
        vlan_name = intent.entities.get("vlan_name")

        if not vlan_name:
            blockers.append("VLAN request is missing a VLAN name.")
        elif len(vlan_name) > 32:
            warnings.append(
                f"VLAN name {vlan_name!r} is longer than 32 characters. Some platforms may reject it."
            )
        elif not re.match(r"^[A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*$", vlan_name):
            warnings.append(
                f"VLAN name {vlan_name!r} contains unusual characters. Confirm platform naming rules."
            )


def check_bgp_safety(
    raw_prompt: str,
    intent: NetworkIntent,
    blockers: List[str],
    warnings: List[str],
) -> None:
    asn_candidates = extract_asn_candidates(raw_prompt)

    for entity_key in ["local_as", "remote_as"]:
        value = intent.entities.get(entity_key)
        if isinstance(value, int):
            asn_candidates.append(value)

    unique_asns = sorted(set(asn_candidates))

    for asn in unique_asns:
        if asn < 1 or asn > 4_294_967_295:
            blockers.append(
                f"Invalid AS number {asn}. BGP ASNs must be between 1 and 4294967295."
            )

    if intent.technology == "BGP":
        peer_ips = intent.entities.get("peer_ips", [])
        if len(peer_ips) < 2:
            warnings.append(
                "BGP request has fewer than two peer IPs. A real workflow should ask for both sides."
            )

        required_policy_fields = [
            "inbound_route_policy",
            "outbound_route_policy",
        ]

        for field_name in required_policy_fields:
            if not intent.entities.get(field_name):
                warnings.append(
                    f"BGP request is missing {field_name}. Route policy should be explicit."
                )


def check_ip_safety(raw_prompt: str, blockers: List[str]) -> None:
    ip_like_values = extract_ip_like_values(raw_prompt)

    for value in sorted(set(ip_like_values)):
        try:
            ipaddress.ip_address(value)
        except ValueError:
            blockers.append(
                f"Invalid IP address {value!r}. The prompt contains an address-like value that is not valid IPv4 or IPv6."
            )


# ---------------------------------------------------------------------------
# Spec Generation
# ---------------------------------------------------------------------------

def generate_spec(intent: NetworkIntent) -> Dict[str, Any]:
    """
    Generate a spec dictionary using the same major shape as the supplied
    Itential-style spec:

        1. Problem Statement
        2. High-Level Flow
        3. Phases
        4. Key Design Decisions
        5. Scope
        6. Risks & Mitigations
        7. Requirements
        8. Batch Strategy
        9. Acceptance Criteria
    """
    if intent.technology == "VLAN":
        return generate_vlan_spec(intent)

    if intent.technology == "BGP":
        return generate_bgp_spec(intent)

    return generate_generic_spec(intent)


def generate_vlan_spec(intent: NetworkIntent) -> Dict[str, Any]:
    vlan_id = intent.entities.get("vlan_id") or 50
    vlan_name = intent.entities.get("vlan_name") or "Finance"
    switch = intent.entities.get("target_switch_hostname", "switch-01")
    device_os = intent.entities.get("device_os", "Cisco IOS-XE")
    interface_scope = intent.entities.get("interface_scope", "global only")

    return {
        "title": "Use Case: VLAN Provisioning",
        "metadata": {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "device_os": device_os,
            "source_prompt": intent.raw_prompt,
        },
        "sections": {
            "1_problem_statement": {
                "problem": (
                    f"Provisioning VLAN {vlan_id} named {vlan_name!r} on {switch} "
                    "requires careful validation so the VLAN ID, name, device target, "
                    "and deployment scope are correct before any configuration is applied."
                ),
                "goal": (
                    f"Automate the VLAN lifecycle: validate inputs, back up the device, "
                    f"deploy VLAN {vlan_id}, verify it exists, optionally validate allowed "
                    "trunk/access scope, save configuration only after success, and produce evidence."
                ),
            },
            "2_high_level_flow": [
                "Validate Inputs",
                "Pre-Flight Checks",
                "Deploy VLAN Config",
                "Verify VLAN State",
                "Post-Flight Checks",
                "Close Out",
            ],
            "3_phases": [
                {
                    "name": "Validate Inputs",
                    "description": (
                        "Confirm VLAN ID is between 1 and 4094, VLAN name is present, "
                        "target switch is known, and requested scope is supported."
                    ),
                    "failure_behavior": "Stop before touching the device.",
                },
                {
                    "name": "Pre-Flight Checks",
                    "description": (
                        "Confirm the switch is reachable, identify the device OS, check "
                        "current VLAN database, and back up running configuration."
                    ),
                    "failure_behavior": "Stop and report unreachable or unsafe state.",
                },
                {
                    "name": "Deploy VLAN Config",
                    "description": (
                        f"Generate and apply VLAN {vlan_id} configuration with name "
                        f"{vlan_name!r} on {switch}."
                    ),
                    "failure_behavior": "Rollback candidate changes if supported.",
                },
                {
                    "name": "Verify VLAN State",
                    "description": (
                        "Read back VLAN state from the device and confirm the VLAN ID "
                        "and name match the requested intent."
                    ),
                    "failure_behavior": "Rollback and capture before/after evidence.",
                },
                {
                    "name": "Post-Flight Checks",
                    "description": (
                        "Validate requested interface scope, confirm no unexpected VLAN "
                        "changes occurred, and save running config only after verification."
                    ),
                    "failure_behavior": "Do not save configuration if verification fails.",
                },
                {
                    "name": "Close Out",
                    "description": (
                        "Generate an evidence report containing the requested VLAN, "
                        "target device, validation results, and before/after command output."
                    ),
                    "failure_behavior": "Mark ticket/manual follow-up as required.",
                },
            ],
            "4_key_design_decisions": [
                {
                    "decision": "Input validation is a hard gate",
                    "choice": "Reject invalid VLAN IDs or missing VLAN names",
                    "rationale": "Bad VLAN changes can cause connectivity issues.",
                },
                {
                    "decision": "Backup before deploy",
                    "choice": "Capture running config before configuration",
                    "rationale": "Rollback requires a known-good previous state.",
                },
                {
                    "decision": "Save only after verification",
                    "choice": "Do not write memory until VLAN is confirmed",
                    "rationale": "A reload should clear a bad unverified change.",
                },
            ],
            "5_scope": {
                "in_scope": [
                    "VLAN creation",
                    "VLAN naming",
                    "Switch reachability checks",
                    "Configuration backup",
                    "Read-back verification",
                    "Evidence generation",
                ],
                "out_of_scope": [
                    "Campus-wide VLAN design",
                    "Spanning Tree topology redesign",
                    "IP subnet allocation",
                    "Firewall policy changes",
                ],
            },
            "6_risks_and_mitigations": [
                {
                    "risk": "Config applied to wrong switch",
                    "impact": "Unexpected network change",
                    "mitigation": "Validate hostname and device identity before deploy.",
                },
                {
                    "risk": "Invalid VLAN ID",
                    "impact": "Device rejects config or behavior is undefined",
                    "mitigation": "Validate VLAN ID range before deployment.",
                },
                {
                    "risk": "VLAN not allowed where needed",
                    "impact": "Hosts cannot communicate",
                    "mitigation": "Ask for interface scope and verify operational state.",
                },
            ],
            "7_requirements": {
                "platform_capabilities": [
                    {
                        "capability": "Execute CLI commands on network devices",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Generate device config from templates",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Apply config and read it back",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Backup and restore configurations",
                        "required": True,
                        "if_not_available": "Cannot safely proceed",
                    },
                ],
                "external_systems": [
                    {
                        "system": "Target switch",
                        "purpose": "Apply and verify VLAN config",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "system": "ITSM / ticketing",
                        "purpose": "Track change request",
                        "required": False,
                        "if_not_available": "Engineer tracks manually",
                    },
                ],
                "discovery_questions": [
                    "What switch or switch group should receive the VLAN?",
                    "Should this VLAN be global only, assigned to access ports, or allowed on trunks?",
                    "Is the VLAN ID already reserved in IPAM or source of truth?",
                    "Should the configuration be saved after successful verification?",
                ],
            },
            "8_batch_strategy": [
                {
                    "strategy": "Sequential",
                    "behavior": "One switch at a time, verify before moving on",
                    "when_to_use": "First-time deployment or mixed switch platforms",
                },
                {
                    "strategy": "Grouped by site",
                    "behavior": "Deploy to all switches in a site after validation",
                    "when_to_use": "Campus or branch rollout",
                },
                {
                    "strategy": "Parallel",
                    "behavior": "Deploy to independent switches simultaneously",
                    "when_to_use": "Large-scale standardized rollout",
                },
            ],
            "9_acceptance_criteria": [
                "Invalid VLAN IDs are rejected before deployment",
                "Target switch configuration is backed up before changes",
                "VLAN configuration is applied successfully",
                "VLAN state is verified by reading from the device",
                "Running config is saved only after successful verification",
                "Evidence report includes before/after VLAN state",
            ],
        },
        "normalized_inputs": {
            "vlan_id": vlan_id,
            "vlan_name": vlan_name,
            "target_switch": switch,
            "device_os": device_os,
            "interface_scope": interface_scope,
        },
    }


def generate_bgp_spec(intent: NetworkIntent) -> Dict[str, Any]:
    entities = intent.entities

    return {
        "title": "Use Case: BGP Peer Provisioning",
        "metadata": {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "device_os": entities.get("device_os"),
            "source_prompt": intent.raw_prompt,
        },
        "sections": {
            "1_problem_statement": {
                "problem": (
                    "Adding a BGP peering session requires precise coordination "
                    "between routers. Incorrect AS numbers, peer IPs, policies, "
                    "prefix limits, or authentication can prevent the session from "
                    "establishing or create routing risk."
                ),
                "goal": (
                    "Automate the full BGP peer lifecycle: validate inputs, deploy "
                    "near-side and far-side configuration, verify session establishment, "
                    "validate route exchange, and rollback on failure."
                ),
            },
            "2_high_level_flow": [
                "Validate Inputs",
                "Pre-Flight Checks",
                "Deploy Near Side",
                "Deploy Far Side",
                "Verify Session",
                "Post-Flight Checks",
                "Close Out",
            ],
            "3_phases": [
                {
                    "name": "Validate Inputs",
                    "description": (
                        "Confirm AS numbers, peer IPs, route policies, prefix limits, "
                        "device OS, and access mode before touching devices."
                    ),
                    "failure_behavior": "Stop with a clear error.",
                },
                {
                    "name": "Pre-Flight Checks",
                    "description": (
                        "Verify both routers are reachable, back up configs, confirm "
                        "BGP process is running, and check peer does not already exist."
                    ),
                    "failure_behavior": "Stop before deployment.",
                },
                {
                    "name": "Deploy Near Side",
                    "description": (
                        "Generate and apply local BGP neighbor configuration. Verify "
                        "the config was applied by reading it back."
                    ),
                    "failure_behavior": "Stop. Do not configure far side.",
                },
                {
                    "name": "Deploy Far Side",
                    "description": (
                        "Generate and apply mirror BGP neighbor configuration on the "
                        "remote router. Verify by reading it back."
                    ),
                    "failure_behavior": "Rollback near side.",
                },
                {
                    "name": "Verify Session",
                    "description": (
                        "Poll BGP neighbor state until Established or timeout. Capture "
                        "state and reset reason if session fails."
                    ),
                    "failure_behavior": "Rollback both sides if auto-rollback is enabled.",
                },
                {
                    "name": "Post-Flight Checks",
                    "description": (
                        "Confirm route exchange and prefix counts are within expected "
                        "ranges. Save config only after success."
                    ),
                    "failure_behavior": "Do not save failed configuration.",
                },
                {
                    "name": "Close Out",
                    "description": (
                        "Update change record and generate evidence report with before "
                        "and after BGP neighbor tables."
                    ),
                    "failure_behavior": "Mark manual follow-up required.",
                },
            ],
            "4_key_design_decisions": [
                {
                    "decision": "Input validation is a hard gate",
                    "choice": "Reject bad AS numbers, IPs, or missing policies",
                    "rationale": "A misconfigured BGP peer can leak or black-hole traffic.",
                },
                {
                    "decision": "Near side deploys first",
                    "choice": "Configure local side before far side",
                    "rationale": "If near side fails, nothing must be rolled back remotely.",
                },
                {
                    "decision": "Both sides rollback together",
                    "choice": "Rollback both devices on verification failure",
                    "rationale": "A one-sided BGP config will never establish.",
                },
            ],
            "5_scope": {
                "in_scope": [
                    "eBGP and iBGP peer addition",
                    "Peer modification",
                    "Peer removal",
                    "Session verification",
                    "Route exchange validation",
                    "Backup and rollback",
                    "Evidence generation",
                ],
                "out_of_scope": [
                    "Route policy design",
                    "Route reflector topology design",
                    "IX port provisioning",
                    "RPKI/ROA setup",
                    "Traffic engineering design",
                ],
            },
            "6_risks_and_mitigations": [
                {
                    "risk": "Config applied to wrong device",
                    "impact": "Peering with unintended neighbor",
                    "mitigation": "Validate device identity and peer IPs before deploy.",
                },
                {
                    "risk": "Session never establishes",
                    "impact": "No traffic flow on new peer",
                    "mitigation": "Timeout with state capture and auto-rollback.",
                },
                {
                    "risk": "Route leak due to wrong policy",
                    "impact": "Potential outage",
                    "mitigation": "Validate route-map exists before deployment.",
                },
            ],
            "7_requirements": {
                "platform_capabilities": [
                    {
                        "capability": "Execute CLI commands on network devices",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Generate config from templates",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Apply config and read it back",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Backup and restore configurations",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "capability": "Poll device state with timeout",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                ],
                "external_systems": [
                    {
                        "system": "Near-side router",
                        "purpose": "Apply BGP config and verify session",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    },
                    {
                        "system": "Far-side router",
                        "purpose": "Apply mirror BGP config and verify session",
                        "required": False,
                        "if_not_available": "Use near-side-only mode",
                    },
                    {
                        "system": "ITSM / ticketing",
                        "purpose": "Track change",
                        "required": False,
                        "if_not_available": "Engineer tracks manually",
                    },
                ],
                "discovery_questions": [
                    "Is this eBGP or iBGP?",
                    "What are the local and remote AS numbers?",
                    "What are the peer IP addresses?",
                    "What route policies should be applied inbound and outbound?",
                    "What prefix limits should be used?",
                    "Is authentication required?",
                    "Do you have access to configure both sides?",
                    "What device OS are the routers running?",
                ],
            },
            "8_batch_strategy": [
                {
                    "strategy": "Sequential",
                    "behavior": "One peering session at a time",
                    "when_to_use": "Mixed device types or first-time peers",
                },
                {
                    "strategy": "Grouped by router",
                    "behavior": "All peers on one router, then verify",
                    "when_to_use": "Multiple peers on a single device",
                },
                {
                    "strategy": "Parallel",
                    "behavior": "Independent peerings simultaneously",
                    "when_to_use": "Large-scale peering buildout",
                },
            ],
            "9_acceptance_criteria": [
                "Invalid inputs are rejected before deployment",
                "Both devices have config backups before changes",
                "BGP config is applied and verified by reading it back",
                "BGP session reaches Established within timeout",
                "Routes are exchanged and prefix counts are expected",
                "Both sides rollback cleanly on failure",
                "Running config is saved only after verification",
                "Evidence report includes before/after BGP state",
            ],
        },
        "normalized_inputs": {
            "local_as": entities.get("local_as"),
            "remote_as": entities.get("remote_as"),
            "peer_ips": entities.get("peer_ips"),
            "near_side_router": entities.get("near_side_router"),
            "far_side_router": entities.get("far_side_router"),
            "inbound_route_policy": entities.get("inbound_route_policy"),
            "outbound_route_policy": entities.get("outbound_route_policy"),
            "prefix_limits": entities.get("prefix_limits"),
            "device_os": entities.get("device_os"),
        },
    }


def generate_generic_spec(intent: NetworkIntent) -> Dict[str, Any]:
    return {
        "title": "Use Case: Network Change Automation",
        "metadata": {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "device_os": intent.entities.get("device_os"),
            "source_prompt": intent.raw_prompt,
        },
        "sections": {
            "1_problem_statement": {
                "problem": (
                    "Manual network changes can fail when inputs are unclear, "
                    "pre-checks are skipped, or verification is not consistent."
                ),
                "goal": (
                    "Convert a natural language request into a validated network "
                    "change spec with deployment, verification, rollback, and evidence."
                ),
            },
            "2_high_level_flow": [
                "Validate Inputs",
                "Pre-Flight Checks",
                "Deploy Config",
                "Verify State",
                "Post-Flight Checks",
                "Close Out",
            ],
            "3_phases": [
                {
                    "name": "Validate Inputs",
                    "description": "Confirm required change parameters are present.",
                    "failure_behavior": "Stop before deployment.",
                },
                {
                    "name": "Pre-Flight Checks",
                    "description": "Confirm device reachability and back up config.",
                    "failure_behavior": "Stop if unsafe.",
                },
                {
                    "name": "Deploy Config",
                    "description": "Apply intended configuration.",
                    "failure_behavior": "Rollback if deployment fails.",
                },
                {
                    "name": "Verify State",
                    "description": "Read back config and operational state.",
                    "failure_behavior": "Rollback if verification fails.",
                },
                {
                    "name": "Post-Flight Checks",
                    "description": "Save configuration after successful verification.",
                    "failure_behavior": "Do not save failed change.",
                },
                {
                    "name": "Close Out",
                    "description": "Generate evidence report.",
                    "failure_behavior": "Mark manual follow-up required.",
                },
            ],
            "4_key_design_decisions": [
                {
                    "decision": "Spec before deploy",
                    "choice": "Compile request into structured spec first",
                    "rationale": "The system needs deterministic inputs.",
                }
            ],
            "5_scope": {
                "in_scope": ["Validation", "Deployment", "Verification", "Rollback", "Evidence"],
                "out_of_scope": ["Network architecture design"],
            },
            "6_risks_and_mitigations": [
                {
                    "risk": "Ambiguous request",
                    "impact": "Wrong change may be deployed",
                    "mitigation": "Require structured validation before deployment.",
                }
            ],
            "7_requirements": {
                "platform_capabilities": [
                    {
                        "capability": "Execute CLI commands",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    }
                ],
                "external_systems": [
                    {
                        "system": "Network device",
                        "purpose": "Apply and verify change",
                        "required": True,
                        "if_not_available": "Cannot proceed",
                    }
                ],
                "discovery_questions": [
                    "What device should be changed?",
                    "What exact configuration should be applied?",
                    "How should success be verified?",
                ],
            },
            "8_batch_strategy": [
                {
                    "strategy": "Sequential",
                    "behavior": "One device or change at a time",
                    "when_to_use": "Default safe mode",
                }
            ],
            "9_acceptance_criteria": [
                "Inputs are validated",
                "Device backup is captured",
                "Configuration is applied",
                "State is verified",
                "Rollback is available",
                "Evidence report is generated",
            ],
        },
        "normalized_inputs": intent.entities,
    }


# ---------------------------------------------------------------------------
# Spec Validation
# ---------------------------------------------------------------------------

def validate_spec(spec: Dict[str, Any]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    required_top_level = ["title", "metadata", "sections", "normalized_inputs"]
    for key in required_top_level:
        if key not in spec:
            errors.append(f"Missing top-level key: {key}")

    sections = spec.get("sections", {})
    if not isinstance(sections, dict):
        errors.append("sections must be a dictionary")
        return ValidationResult(False, errors, warnings)

    expected_sections = [
        "1_problem_statement",
        "2_high_level_flow",
        "3_phases",
        "4_key_design_decisions",
        "5_scope",
        "6_risks_and_mitigations",
        "7_requirements",
        "8_batch_strategy",
        "9_acceptance_criteria",
    ]

    for section in expected_sections:
        if section not in sections:
            errors.append(f"Missing required spec section: {section}")

    problem = sections.get("1_problem_statement", {})
    if not isinstance(problem, dict):
        errors.append("1_problem_statement must be an object")
    else:
        if not problem.get("problem"):
            errors.append("Problem Statement is missing 'problem'")
        if not problem.get("goal"):
            errors.append("Problem Statement is missing 'goal'")

    phases = sections.get("3_phases", [])
    if not isinstance(phases, list) or not phases:
        errors.append("3_phases must be a non-empty list")
    else:
        for idx, phase in enumerate(phases, start=1):
            if not phase.get("name"):
                errors.append(f"Phase {idx} is missing name")
            if not phase.get("description"):
                errors.append(f"Phase {idx} is missing description")
            if not phase.get("failure_behavior"):
                warnings.append(f"Phase {idx} is missing failure behavior")

    acceptance = sections.get("9_acceptance_criteria", [])
    if not isinstance(acceptance, list) or len(acceptance) < 3:
        errors.append("9_acceptance_criteria must include at least three criteria")

    normalized = spec.get("normalized_inputs", {})
    if contains_none(normalized):
        warnings.append("Some normalized inputs are still null or unresolved")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def contains_none(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, dict):
        return any(contains_none(v) for v in value.values())

    if isinstance(value, list):
        return any(contains_none(v) for v in value)

    return False


# ---------------------------------------------------------------------------
# Markdown Renderer
# ---------------------------------------------------------------------------

def render_markdown_spec(spec: Dict[str, Any]) -> str:
    sections = spec["sections"]

    lines: List[str] = []
    lines.append(f"# {spec['title']}")
    lines.append("")

    ps = sections["1_problem_statement"]
    lines.append("## 1. Problem Statement")
    lines.append(ps["problem"])
    lines.append("")
    lines.append(f"**Goal:** {ps['goal']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 2. High-Level Flow")
    lines.append(" → ".join(sections["2_high_level_flow"]))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 3. Phases")
    for phase in sections["3_phases"]:
        lines.append(f"### {phase['name']}")
        lines.append(phase["description"])
        lines.append("")
        lines.append(f"**Failure behavior:** {phase['failure_behavior']}")
        lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 4. Key Design Decisions")
    lines.append("| Decision | Choice | Rationale |")
    lines.append("|----------|--------|-----------|")
    for item in sections["4_key_design_decisions"]:
        lines.append(
            f"| {item['decision']} | {item['choice']} | {item['rationale']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    scope = sections["5_scope"]
    lines.append("## 5. Scope")
    lines.append("**In scope:**")
    for item in scope["in_scope"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("**Out of scope:**")
    for item in scope["out_of_scope"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 6. Risks & Mitigations")
    lines.append("| Risk | Impact | Mitigation |")
    lines.append("|------|--------|------------|")
    for item in sections["6_risks_and_mitigations"]:
        lines.append(
            f"| {item['risk']} | {item['impact']} | {item['mitigation']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    requirements = sections["7_requirements"]
    lines.append("## 7. Requirements")
    lines.append("### What the platform must be able to do")
    lines.append("| Capability | Required | If Not Available |")
    lines.append("|-----------|----------|------------------|")
    for item in requirements["platform_capabilities"]:
        required = "Yes" if item["required"] else "No"
        lines.append(
            f"| {item['capability']} | {required} | {item['if_not_available']} |"
        )

    lines.append("")
    lines.append("### What external systems are involved")
    lines.append("| System | Purpose | Required | If Not Available |")
    lines.append("|--------|---------|----------|------------------|")
    for item in requirements["external_systems"]:
        required = "Yes" if item["required"] else "No"
        lines.append(
            f"| {item['system']} | {item['purpose']} | {required} | {item['if_not_available']} |"
        )

    lines.append("")
    lines.append("### Discovery Questions")
    for idx, question in enumerate(requirements["discovery_questions"], start=1):
        lines.append(f"{idx}. {question}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 8. Batch Strategy")
    lines.append("| Strategy | Behavior | When to Use |")
    lines.append("|----------|----------|-------------|")
    for item in sections["8_batch_strategy"]:
        lines.append(
            f"| {item['strategy']} | {item['behavior']} | {item['when_to_use']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 9. Acceptance Criteria")
    for idx, item in enumerate(sections["9_acceptance_criteria"], start=1):
        lines.append(f"{idx}. {item}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Asset Payload Compiler
# ---------------------------------------------------------------------------

def compile_asset_payload(
    intent: NetworkIntent,
    spec: Dict[str, Any],
    markdown_spec: str,
    safety: SafetyCheckResult,
    validation: ValidationResult,
) -> Dict[str, Any]:
    """
    Build a fake API-ready payload.

    This is not an actual Itential API contract. It is a mock payload that shows
    how a spec compiler might package the result for a downstream platform.
    """
    asset_name = slugify(spec["title"])

    return {
        "assetType": "itential.spec.mock",
        "assetName": asset_name,
        "builder": {
            "name": "mock-builder",
            "version": "0.2.0",
            "mode": "local-demo",
        },
        "request": {
            "id": str(uuid.uuid4()),
            "compiledAt": datetime.now(timezone.utc).isoformat(),
            "sourcePrompt": intent.raw_prompt,
        },
        "safety": {
            "status": "passed" if safety.passed else "blocked",
            "blockers": safety.blockers,
            "warnings": safety.warnings,
            "observations": safety.observations,
        },
        "validation": {
            "status": "passed" if validation.passed else "failed",
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "intent": {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "useCase": intent.use_case,
            "deviceOS": intent.device_os,
            "entities": intent.entities,
            "assumptions": intent.assumptions,
        },
        "apiTarget": {
            "method": "POST",
            "path": "/api/spec-assets",
            "dryRun": True,
            "note": "Mock endpoint for interview demonstration only.",
        },
        "compiledSpec": {
            "format": "markdown+json",
            "document": markdown_spec,
            "json": spec,
        },
    }


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "network-spec"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_pipeline_output(
    terminal: Terminal,
    intent: NetworkIntent,
    spec: Dict[str, Any],
    markdown_spec: str,
    safety: SafetyCheckResult,
    validation: ValidationResult,
    payload: Dict[str, Any],
) -> None:
    terminal.rule(
        "[bold cyan]Mock Itential Spec Builder[/bold cyan]"
        if RICH_AVAILABLE
        else "Mock Itential Spec Builder"
    )

    terminal.status_table([
        ("1. Prompt Intake", "OK", "Raw network request captured"),
        ("2. Intent Extraction", "OK", f"Detected {intent.technology} / {intent.action}"),
        (
            "3. Safety Policy Check",
            "PASSED" if safety.passed else "BLOCKED",
            "Prompt allowed to compile" if safety.passed else "Prompt blocked before spec generation",
        ),
        ("4. Spec Generation", "OK", "Generated sections 1 through 9"),
        (
            "5. Schema Validation",
            "PASSED" if validation.passed else "FAILED",
            "Spec shape is valid" if validation.passed else "Spec has blocking errors",
        ),
        ("6. Asset Compile", "OK", "Mock API payload generated"),
    ])

    terminal.json_panel(
        {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "use_case": intent.use_case,
            "entities": intent.entities,
            "assumptions": intent.assumptions,
        },
        title="Structured Intent",
    )

    terminal.json_panel(
        {
            "status": "passed" if safety.passed else "blocked",
            "blockers": safety.blockers,
            "warnings": safety.warnings,
            "observations": safety.observations,
        },
        title="Safety Policy Check",
    )

    terminal.markdown_panel(markdown_spec, title="Generated Itential-Style Spec")

    terminal.json_panel(payload, title="Compiled Itential Asset Payload")


def print_safety_blocked_output(
    terminal: Terminal,
    intent: NetworkIntent,
    safety: SafetyCheckResult,
) -> None:
    terminal.rule(
        "[bold red]Mock Itential Spec Builder - Safety Blocked[/bold red]"
        if RICH_AVAILABLE
        else "Mock Itential Spec Builder - Safety Blocked"
    )

    terminal.status_table([
        ("1. Prompt Intake", "OK", "Raw network request captured"),
        ("2. Intent Extraction", "OK", f"Detected {intent.technology} / {intent.action}"),
        (
            "3. Safety Policy Check",
            "BLOCKED",
            "Unsafe or ambiguous prompt stopped before spec generation",
        ),
        ("4. Spec Generation", "SKIPPED", "No spec generated because safety gate failed"),
        ("5. Schema Validation", "SKIPPED", "No spec available to validate"),
        ("6. Asset Compile", "SKIPPED", "No payload compiled"),
    ])

    terminal.json_panel(
        {
            "domain": intent.domain,
            "technology": intent.technology,
            "action": intent.action,
            "use_case": intent.use_case,
            "entities": intent.entities,
            "assumptions": intent.assumptions,
        },
        title="Structured Intent",
    )

    terminal.json_panel(
        {
            "status": "blocked",
            "blockers": safety.blockers,
            "warnings": safety.warnings,
            "observations": safety.observations,
        },
        title="Safety Policy Check",
    )

    friendly_message = (
        "The request was intentionally stopped before spec generation.\n\n"
        "That is the correct behavior.\n\n"
        "A safe automation system should not turn unsafe natural language into "
        "an executable network plan. The prompt must be corrected first."
    )

    terminal.panel(friendly_message, title="Result", style="red")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local mock builder for Itential-style Spec-Driven Development demos."
    )

    parser.add_argument(
        "--prompt",
        help="Raw network prompt to compile into a spec.",
    )

    parser.add_argument(
        "--no-questions",
        action="store_true",
        help="Do not ask follow-up questions. Use safe placeholders.",
    )

    parser.add_argument(
        "--save",
        help="Optional path to save the compiled payload JSON.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    terminal = Terminal()

    terminal.rule("Spec-Driven Network Automation Demo")

    raw_prompt = args.prompt
    if not raw_prompt:
        raw_prompt = terminal.ask(
            "Describe the network change",
            default="Provision a new corporate VLAN 50 named 'Finance' on a Cisco IOS-XE switch",
        )

    if not raw_prompt.strip():
        terminal.print("No prompt supplied. Exiting.")
        return 1

    intent = simulate_llm_extract(raw_prompt)
    intent = enrich_intent_interactively(
        intent,
        terminal=terminal,
        no_questions=args.no_questions,
    )

    safety = safety_policy_check(intent)

    if not safety.passed:
        print_safety_blocked_output(
            terminal=terminal,
            intent=intent,
            safety=safety,
        )
        return 3

    spec = generate_spec(intent)
    validation = validate_spec(spec)
    markdown_spec = render_markdown_spec(spec)

    payload = compile_asset_payload(
        intent=intent,
        spec=spec,
        markdown_spec=markdown_spec,
        safety=safety,
        validation=validation,
    )

    print_pipeline_output(
        terminal=terminal,
        intent=intent,
        spec=spec,
        markdown_spec=markdown_spec,
        safety=safety,
        validation=validation,
        payload=payload,
    )

    if args.save:
        with open(args.save, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        terminal.panel(
            f"Saved compiled payload to: {args.save}",
            title="Saved",
            style="green",
        )

    return 0 if validation.passed else 2


if __name__ == "__main__":
    sys.exit(main())