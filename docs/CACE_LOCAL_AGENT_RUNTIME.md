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


## Daily Research Assistant experience

The Local AI is not only a configuration option or one-off experiment generator. It should act as the user's persistent Research Assistant across onboarding, experiment design, execution, interpretation, notebook organization, and later sessions.

The canonical UX is defined by `docs/POST_ACCOUNT_RESEARCH_ASSISTANT_UX.md`.

After account creation/entitlement, the assistant should greet the user with:

> What would you like to investigate today? Describe a problem, ask for demos in your field, or let me show you CACE's full capabilities.

The assistant should be able to:

- recommend real demos grounded in structured catalog metadata;
- translate natural-language research intent into previewable typed graphs;
- provide Minimal/Balanced/Exploratory alternatives;
- remain present after Build on Canvas;
- understand the active workspace, selected nodes, notebook and permitted artifacts through typed interfaces;
- use heartbeat/perception to notice convergence, blockers, stale dependencies, new results and verification transitions;
- help maintain Research Ideas and suggest next experiments;
- support geometric reasoning pedagogy and visualization;
- resume useful context across sessions according to local memory/privacy policy.

The assistant should feel continuous with the experiment, but it remains outside the evidence trusted-computing base.
