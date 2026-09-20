# CACE Local Agent Runtime v1

Status: implementation intent, not scientific/proof evidence.

CACE owns a provider-independent agent runtime. Google Antigravity and Gemini/AI Studio are preferred builders and optional provider/orchestration surfaces, not mandatory runtime dependencies.

## Required components

- provider-neutral `AgentController`;
- replaceable `ModelProvider` interface;
- Local / Zero Contact, Hybrid, and General Agent modes;
- typed capability-scoped CACE Tool Bus;
- planner/action/observation loop;
- critic/verifier routing;
- resource/tool/token budgets;
- durable checkpoint/recovery;
- Research Notebook / Grow / Build-on-Canvas integration;
- later specialist roles: Math, Proof, FEM/PDE, Physics/Science, Experiment, Critic, Librarian.

## Zero Contact mode

Must require no external cloud/network service, no cloud credentials, and no unrestricted host shell. CACE remains fully useful with AI disabled.

## Evidence boundary

AI may request canonical deterministic/exact/interval/formal verification, but it cannot authoritatively set PASS, VERIFIED, FORMAL, claim promotion, proof-ledger state, or source-to-formal qualification.

## Architecture

```text
Local AI / AgentController
        |
        v
typed CACE tool calls
        |
        +--> Python orchestration/API
        |       |
        |       +--> C++ rigorous math/science kernels
        |
        +--> canonical verifier/proof readers
                |
                +--> Lean exact qualification
```

Browser/TypeScript remains presentation only.


## Self-improving tool contribution loop

The Local AI should be able to make CACE progressively more capable through bounded contributions:

```text
observe canvas / notebook
 -> identify reusable missing capability
 -> specify typed tool
 -> implement/test C++ kernel
 -> add thin orchestration/binding
 -> attempt Lean formalization
 -> package unresolved obligations if needed
 -> collaboration review
 -> proof qualification when applicable
 -> register accepted tool
 -> expose Help/example
 -> reuse tool in later experiments
```

The canonical contract is `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`.

A contribution may stop at a proof-ready packet without being discarded. Another agent/human can continue from the explicit unresolved obligations.

This is how CACE can become better over time without allowing an AI to redefine evidence truth.
