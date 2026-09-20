# CACE Capability-Gap Feedback and Tool Incubation Loop

Status: product/engineering governance. Not proof evidence.

## User experience

When a user asks the Research Assistant for a capability CACE does not currently
have, the assistant should not fabricate support or end at "unsupported."

It should:

1. explain briefly what is missing;
2. offer **Request this capability / Send feedback**;
3. capture a structured Tool Request;
4. offer an available workaround only when semantically honest;
5. optionally route the request into the rigorous AI tool contribution pipeline.

Suggested assistant language:

> CACE does not currently have a production-ready tool for that operation.
> I can save this as a tool request so it can be implemented and reviewed for
> rigor. If you want, I can also propose the typed inputs/outputs and an initial
> experiment workaround.

## Structured Tool Request

A request should capture:

- request ID;
- user-visible title;
- intended scientific/mathematical purpose;
- example inputs/outputs;
- desired evidence level;
- modules it should connect to;
- units/dimensions;
- expected failure cases;
- motivating experiment/workspace reference;
- priority/frequency metadata;
- privacy-safe user feedback text;
- consent to include anonymized request context in developer feedback.

No research data is uploaded by default.

## Builder path

For approved development work:

user request
 -> Tool Request
 -> Gemini / local Rigorous Tool Builder
 -> typed specification
 -> canonical C++ implementation
 -> unit/property/adversarial tests
 -> exact/certified checker where applicable
 -> thin Python/API binding
 -> Lean statement/proof attempt
 -> source-to-formal bridge
 -> proof-ready submission packet
 -> quarantine / Exact-Pin
 -> audited promotion
 -> canonical qualification when applicable
 -> production module + Help/demo

If formal closure is incomplete, the builder submits the unresolved proof
obligations rather than claiming completion.

## Canonical-proof update rule

A new tool may reuse qualified existing theorems only through an explicit
runtime-to-formal binding. If new theorems are needed, they enter the ordinary
quarantine and qualification flow.

AI builders never directly edit canonical evidence state to PASS.

## Acceptance criteria

- unsupported capability detection is grounded in the real module/tool registry;
- users can submit or cancel feedback without losing their experiment;
- requests deduplicate by semantic tool intent when feasible;
- approved requests can be converted into cace-ai-tool-submission-v1 work;
- a tool is not advertised as available until its production-completeness gate passes;
- missing proof obligations remain visible;
- feedback frequency can help prioritize engineering but cannot affect evidence truth.
