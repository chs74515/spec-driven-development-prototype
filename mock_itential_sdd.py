#!/usr/bin/env python3
import json
import time
import os

# Terminal color codes for professional Mac output
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

def clear_screen():
    os.system('clear')

def print_header(title):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}🚀 {title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def simulate_agent_thinking(agent_name, steps):
    print(f"{BOLD}{YELLOW}[{agent_name}]{RESET} Initializing orchestration pipeline...")
    for step in steps:
        time.sleep(0.8)
        print(f"  {YELLOW}↳{RESET} {step}")
    print(f"{GREEN}✓ {agent_name} process completed successfully.{RESET}\n")

def main():
    clear_screen()
    print_header("Itential PS Delivery Prototyping Terminal\n   Spec-Driven Development (SDD) Simulation")
    
    print(f"{BOLD}Select a common enterprise network use case to automate:{RESET}")
    print("1) Provision Corporate VLAN (Cisco IOS-XE)")
    print("2) Update Enterprise DNS Zone Record (Infoblox)")
    print("3) Deploy BGP Peer Configuration (Juniper JunOS)")
    
    choice = input(f"\n{BOLD}Enter choice (1-3): {RESET}").strip()
    
    # Define Mock Customer Requirements based on selection
    if choice == '2':
        raw_prompt = "Hey Caleb, we need to map an A record for backend-api.internal to 10.240.12.55 inside our core Infoblox view. Ensure validation is enabled."
        target_tech = "Infoblox NIOS"
        asset_type = "DNS_Record_Workflow"
    elif choice == '3':
        raw_prompt = "Configure a new external BGP neighbor at 192.168.99.2 with AS 65100 on our branch routers. We need explicit ingress route-filtering."
        target_tech = "Juniper JunOS"
        asset_type = "BGP_Peer_Template"
    else:
        raw_prompt = "Set up VLAN 150 named 'Secure_Finance' across our switch infrastructure. Needs to be tagged on trunk ports 1-4."
        target_tech = "Cisco IOS-XE"
        asset_type = "VLAN_Provisioning_Workflow"

    clear_screen()
    print_header(f"Processing Requirement for Target: {target_tech}")
    print(f"{BOLD}Unstructured Customer Input:{RESET}\n\"{raw_prompt}\"\n")
    input(f"{BOLD}Press [ENTER] to initiate Itential Spec Agent Lifecycle...{RESET}")
    print("\n" + "-"*60)

    # 1. SPEC AGENT STAGE
    simulate_agent_thinking("Spec Agent", [
        "Ingesting raw text input and parsing intent tokens...",
        "Validating network target constraints...",
        "Structuring formal JSON specification against Itential Schema v3.2..."
    ])
    
    # Formulate the deterministic Itential Spec layout extracted from builder-skills principles
    itential_spec = {
        "schema_version": "3.2.0",
        "metadata": {
            "generated_by": "itential-builder-skills-spec-agent",
            "intent": "Infrastructure Provisioning"
        },
        "target_infrastructure": {
            "vendor": target_tech.split()[0],
            "environment": "Enterprise_Core_PS"
        },
        "spec_definition": {
            "asset_type": asset_type,
            "parameters": {
                "id": "150" if choice!='2' and choice!='3' else ("192.168.99.2" if choice=='3' else "backend-api.internal"),
                "name": "Secure_Finance" if choice!='2' and choice!='3' else ("BGP_65100" if choice=='3' else "10.240.12.55"),
                "governance_required": True,
                "pre_check_dependencies": ["Device_Reachability", "Auth_Validation"]
            }
        }
    }
    print(f"{BOLD}{BLUE}[OUTPUT] Compliant Itential Spec File Generated:{RESET}")
    print(json.dumps(itential_spec, indent=2))
    
    input(f"\n{BOLD}Press [ENTER] to hand over to Solution Architecture Agent...{RESET}")
    print("\n" + "-"*60)

    # 2. SOLUTION ARCHITECT AGENT STAGE
    simulate_agent_thinking("Solution Architecture Agent", [
        "Analyzing JSON Spec parameters against safe networking guardrails...",
        "Performing feasibility check against available platform adapters...",
        "Designing deterministic orchestration block topology..."
    ])
    
    # 3. BUILDER AGENT STAGE
    input(f"{BOLD}Press [ENTER] to execute Builder Agent (Compile Canvas Asset Portfolio)...{RESET}")
    print("\n" + "-"*60)
    simulate_agent_thinking("Builder Agent", [
        "Mapping speculative data elements to physical API structural elements...",
        "Injecting deterministic error-handling, rollback states, and pre-checks...",
        "Assembling ready-to-import Canvas Operations Manager Payload..."
    ])

    # Final Compiled Representation of what goes into Itential
    compiled_canvas_asset = {
        "itential_asset_export": {
            "type": "Workflow_Canvas_Layout",
            "id": f"wf-{asset_type.lower()}-generated",
            "tasks": [
                {
                    "task_id": "pre_check_1",
                    "component": "Adapter-Network-Inventory",
                    "action": "verifyStatus",
                    "next_on_success": "state_evaluation"
                },
                {
                    "task_id": "state_evaluation",
                    "component": "Transformation-Engine",
                    "action": "evaluateSpecMatchesLiveState",
                    "next_on_success": "execution_payload_push",
                    "next_on_failure": "workflow_graceful_abort"
                },
                {
                    "task_id": "execution_payload_push",
                    "component": f"Adapter-{target_tech.replace(' ', '-')}",
                    "action": "applyConfiguration",
                    "payload_data": itential_spec["spec_definition"]["parameters"],
                    "next_on_success": "post_validation_audit",
                    "next_on_failure": "trigger_rollback_sequence"
                },
                {
                    "task_id": "trigger_rollback_sequence",
                    "component": "Orchestration-Core",
                    "action": "revertToSafeState",
                    "next_on_success": "workflow_graceful_abort"
                }
            ]
        }
    }

    print(f"{BOLD}{GREEN}[FINAL REPO EXPORT] Production-Ready Canvas Object Compiled:{RESET}")
    print(json.dumps(compiled_canvas_asset, indent=2))
    print(f"\n{BOLD}{CYAN}🌟 Pipeline Complete. Ready to show the Architect! 🌟{RESET}\n")

if __name__ == "__main__":
    main()
