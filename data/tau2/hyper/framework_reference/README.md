# Agent Framework Reference

This directory contains documentation for the tau2 agent framework — an
open-source agent framework that this platform embeds within its own
architecture. The `tau2.*` imports in these contracts come from that
framework. Read these docs to understand the contracts your code must
satisfy.

## Files

| File | What it covers |
|------|---------------|
| `toolkit_contract.md` | How to write domain tools (ToolKitBase, DB, @is_tool) |
| `client_api_contract.md` | How to write agent tools backed by the Client REST API |
| `agent_contract.md` | How to write the agent (create_agent factory, HalfDuplexAgent) |
| `scenario_contract.md` | How to write simulated customer scenarios |

A construction kit includes the interface contract that applies to that kit:
either `toolkit_contract.md` or `client_api_contract.md`.
