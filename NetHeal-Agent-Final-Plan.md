# NetHeal Agent - Final Implementation Plan

## Goal

Build a **micro Agentic AI application** that demonstrates a real
non-deterministic AI agent for network troubleshooting.

The objective is **not** to hardcode a workflow.

Instead, the LLM must repeatedly:

1.  Analyze the current observations.
2.  Decide which tool should be executed next.
3.  Execute exactly one tool.
4.  Observe the result.
5.  Decide whether another tool is required.
6.  Finish only after the issue has been verified as resolved.

------------------------------------------------------------------------

# Functional Requirements

The application must include:

-   Machine-readable input
-   System Prompt
-   Skills
-   Independent tools
-   Agentic loop
-   Traceable reasoning
-   Network simulator
-   Modern UI
-   Non-deterministic tool execution

------------------------------------------------------------------------

# Folder Structure

``` text
network-agent/
│
├── app.py
├── agent.py
├── llm.py
├── tool_registry.py
│
├── prompts/
│   └── system_prompt.md
│
├── skills/
│   ├── network_engineer.md
│   ├── troubleshooting.md
│   └── repair_policy.md
│
├── tools/
│   ├── ping.py
│   ├── traceroute.py
│   ├── show_interfaces.py
│   ├── show_routes.py
│   ├── show_vlan.py
│   ├── show_acl.py
│   ├── show_logs.py
│   ├── restart_interface.py
│   ├── move_port_vlan.py
│   ├── add_route.py
│   ├── update_acl.py
│   ├── verify_connectivity.py
│   └── finish.py
│
├── scenarios/
│   ├── interface_down/
│   │   ├── metadata.json
│   │   ├── incident.json
│   │   ├── network.json
│   │   └── expected_flow.md
│   │
│   ├── wrong_vlan/
│   ├── missing_route/
│   ├── firewall_acl/
│   ├── dns_failure/
│   └── high_cpu/
│
├── simulator/
│   ├── simulator.py
│   ├── topology.json
│   └── models.py
│
└── ui/
```

------------------------------------------------------------------------

# Scenario Structure

Each scenario is completely isolated.

metadata.json

``` json
{
  "name":"Interface Down",
  "description":"Router interface is administratively down",
  "difficulty":"Easy"
}
```

incident.json (visible to the LLM)

``` json
{
  "problem":"Server unreachable",
  "source":"PC1",
  "destination":"Server1"
}
```

network.json (hidden from the LLM)

Contains the complete simulated network state.

expected_flow.md

Contains one possible expected troubleshooting path for documentation
only.

------------------------------------------------------------------------

# Network Simulator

The simulator owns the network state.

The LLM NEVER reads network.json directly.

Only tools can access the simulator.

Example:

LLM

↓

show_interfaces(router1)

↓

Tool

↓

Simulator

↓

Returns observation

------------------------------------------------------------------------

# System Prompt

Load:

-   system_prompt.md
-   every markdown file from the skills folder

The prompt should instruct the model to:

-   Think like a senior network engineer.
-   Use exactly one tool per iteration.
-   Never guess.
-   Base every decision on observations.
-   Verify every repair.
-   Finish only after successful verification.

------------------------------------------------------------------------

# Skills

network_engineer.md

Defines the persona.

troubleshooting.md

Defines troubleshooting methodology.

repair_policy.md

Defines repair rules.

Additional skills can be added later without changing the agent.

------------------------------------------------------------------------

# Tool Architecture

Each tool is an independent Python module.

Every tool exposes:

``` python
name
description
input_schema
execute()
```

The Tool Registry automatically loads every Python file found in the
tools directory.

No tool registration is hardcoded.

------------------------------------------------------------------------

# Available Tools

Diagnostics

-   ping
-   traceroute
-   show_interfaces
-   show_routes
-   show_vlan
-   show_acl
-   show_logs

Repair

-   restart_interface
-   move_port_vlan
-   add_route
-   update_acl

Verification

-   verify_connectivity

Termination

-   finish

------------------------------------------------------------------------

# Agent Loop

``` python
history = []

while True:

    decision = llm.plan(
        incident,
        history,
        available_tools
    )

    if decision.tool == "finish":
        break

    result = execute_tool(decision)

    history.append({
        "tool": decision.tool,
        "parameters": decision.parameters,
        "result": result
    })
```

No predefined troubleshooting workflow exists.

The LLM decides the next step after every observation.

------------------------------------------------------------------------

# LLM Input

Each iteration receives:

-   Incident JSON
-   System Prompt
-   Loaded Skills
-   Tool descriptions
-   Previous observations

Example:

``` json
{
  "problem":"Server unreachable",
  "history":[
    {
      "tool":"ping",
      "result":"Timeout"
    }
  ]
}
```

------------------------------------------------------------------------

# LLM Output

Always structured JSON.

Example

``` json
{
  "reason":"Connectivity failed. Need interface status.",
  "tool":"show_interfaces",
  "parameters":{
      "device":"router1"
  }
}
```

Finish

``` json
{
  "tool":"finish",
  "reason":"Connectivity restored."
}
```

------------------------------------------------------------------------

# User Interface

The UI is the main part of the demo.

## Left Panel

Scenario selector

Dropdown

Examples:

-   Interface Down
-   Wrong VLAN
-   Missing Route
-   Firewall ACL
-   DNS Failure
-   High CPU

Buttons

-   Load Scenario
-   Upload Incident JSON
-   Troubleshoot & Heal

The incident JSON should be displayed in a read-only editor.

------------------------------------------------------------------------

## Center Panel

Network Topology

Visual representation of:

Router

Switches

Firewall

Server

PC

Device colors

🟢 Healthy

🟡 Investigating

🔴 Fault

The topology updates as repairs are executed.

------------------------------------------------------------------------

## Right Panel

Current LLM Decision

Shows

Current reasoning

Chosen tool

Parameters

Example

Reason

Need interface status.

Tool

show_interfaces(router1)

------------------------------------------------------------------------

## Bottom Panel

Agent Timeline

Every iteration appears immediately.

Example

Iteration 1

LLM

Need connectivity information.

↓

Tool

ping()

↓

Observation

Timeout

------------------------------------------------------------------------

Iteration 2

LLM

Need interface status.

↓

Tool

show_interfaces()

↓

Observation

Gi0/1 DOWN

------------------------------------------------------------------------

Iteration 3

LLM

Attempt repair.

↓

Tool

restart_interface()

↓

Observation

SUCCESS

------------------------------------------------------------------------

Iteration 4

LLM

Verify repair.

↓

Tool

verify_connectivity()

↓

Observation

SUCCESS

------------------------------------------------------------------------

Iteration 5

LLM

finish()

------------------------------------------------------------------------

# Application Flow

User opens application

↓

Selects scenario

or uploads incident JSON

↓

Clicks

Troubleshoot & Heal

↓

Scenario is loaded

↓

Simulator loads hidden network.json

↓

Agent starts

↓

LLM selects tool

↓

Tool queries simulator

↓

Observation returned

↓

LLM selects next tool

↓

Repeat

↓

finish()

------------------------------------------------------------------------

# Non-Deterministic Requirement

The implementation MUST NOT contain logic like:

``` python
if ping_failed:
    show_interfaces()
```

Instead, after every observation the LLM is free to choose any available
tool.

Possible choices:

-   show_interfaces
-   show_routes
-   show_vlan
-   show_logs
-   traceroute
-   show_acl

Different scenarios --- and even repeated executions of the same
scenario --- may produce different valid tool sequences.

------------------------------------------------------------------------

# Success Criteria

The demo is complete when:

-   Users can select predefined scenarios.
-   Users can upload custom incident JSON.
-   The simulator loads the hidden network state.
-   The LLM performs one decision per iteration.
-   Every tool call is displayed.
-   Every LLM decision is displayed.
-   The network topology updates after repairs.
-   The loop terminates only when the LLM calls finish().
