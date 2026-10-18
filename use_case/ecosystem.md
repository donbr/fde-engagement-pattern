# Someone else's ecosystem

*Carried over from an earlier solution-first spike (not included in this repo) in step 1. The changes for this pass are in the section "What I'd change about the app".*

Where the gateway would actually run inside the client. **The client is hypothetical**, so every answer below is an **assumed pattern** for a regional health insurer, paired with the role I'd ask to confirm it. Discovery rule: "Unknown — ask X" is a legitimate answer; a blank is not.

Patterns only: no hostnames, IPs or diagrams.

---

## Week 1: the first eight questions

**Who I'd ask:** the platform engineering lead, with a draft of this table so they can say "roughly right" or correct it.

| # | Question | Assumed pattern | Confirm with |
| :---: | --- | --- | --- |
| 1 | Where do internal apps run? | Managed Kubernetes for new services; legacy claims systems on VMs | Platform engineering lead |
| 2 | Which cloud? | One primary hyperscaler, plus on-prem for core claims | Platform engineering lead |
| 3 | Internal container registry? | Yes; public registries blocked from the cluster | Platform engineering lead |
| 4 | How do users log in? | Workforce SSO (SAML/OIDC through the corporate IdP) | Identity team |
| 5 | Can the app reach the internet? | Only through an egress proxy with an allowlist; TLS is likely re-signed by an internal CA | Network / security engineering |
| 6 | Where do secrets come from? | The cloud's secrets manager, injected at deploy | Platform engineering lead |
| 7 | Who approves a deployment? | Change advisory board plus an architecture review; CISO sign-off for anything touching PHI | Enterprise architect |
| 8 | Approved internal LLM endpoint? | **The key question.** Likely one provider account under a BAA, shared by every team. That shared account is the root cause in `CHARTER.md`. | CIO office / AI CoE |

**What would surprise me, and what to check first:** whether an API gateway already sits in front of the provider (Azure API Management, Kong, an internal proxy). If it does, the shedder becomes **a policy on that gateway**, not a new service. Azure APIM's `llm-token-limit` and Kong's AI rate-limiting plugin both limit tokens per minute per key, so the per-tier floors and showback are the new part.

**What I'd change about the app to deploy there:**
- Take the tier from the caller's identity (per-workload API key or workload identity), not from the request body.
- Move the counters to a shared store before a second replica.
- Never log prompt content.
- **New this pass:** ship it as a library with a shadow mode, so it can run as a policy on an existing gateway and observe one peak before it enforces anything (R7, R14). Turning shadow mode on is the kill switch.
- **New this pass:** the first change to request isn't the gateway at all. It's the refresh schedule, or the batch lane (option 1), which needs only the Content Operations owner.

---

## Week 1: what the machine told me

**Not run, because there's no client network to probe.** On a real engagement, I'd run an egress probe from inside the deployment target, not from a laptop. The interesting result is *who signed* the provider's certificate: an internal CA means a TLS-intercepting proxy, and containers must trust it.

---

## The full checklist

Thirty ecosystem questions, adapted from FDE training material. ✓ means answered above.

| Area | Question | Assumed pattern (to confirm) | Ask | Why it matters for the gateway |
| --- | --- | --- | --- | --- |
| Compute | Where do internal apps run? | ✓ #1 | — | — |
| Compute | Which cloud, or on-prem? | ✓ #2 | — | — |
| Compute | GPU pool? | Not needed: the gateway is CPU-only, standard library | — | Removes one gate entirely; say so early |
| Compute | Who owns the cluster; intake process? | Platform team, ticket intake | Platform engineering lead | Sets the first realistic date |
| Images | Internal registry? | ✓ #3 | — | — |
| Images | Mandatory base image? | Likely a hardened internal Python image | Platform engineering lead | Pins the Python version |
| Images | Scanning or signing before run? | Likely both | Security engineering | Adds to elapsed time, not effort |
| Identity | How do users authenticate? | ✓ #4 | — | — |
| Identity | SSO terminated before my app? | Yes, at the ingress or existing gateway | Identity team | The gateway serves services, not people |
| Identity | How does my app authenticate outward? | The provider key from the secrets manager | Platform engineering lead | The one credential for the shared account |
| Identity | Workload identity or secrets? | Workload identity, if the cluster supports it | Platform engineering lead | **Where the tier comes from.** Callers prove which workload they are. |
| Identity | Reachable except through the gateway? | Must be no; otherwise callers bypass the floors | Network engineering | A bypass makes the policy optional |
| Secrets | Where do secrets live? | ✓ #6 | — | — |
| Secrets | Injection and rotation? | Injected at deploy; rotation policy unknown | Platform engineering lead | Rotating the provider key must not drop live chats |
| Network | Internet access? Proxy? | ✓ #5 | — | — |
| Network | Egress allowlist; who adds to it? | The provider API host must be on it | Network / security engineering | Usually the longest wait |
| Network | Which VPC or VNet; internal reach? | The app subnet; reaches the provider via the proxy only | Network engineering | — |
| Data | What classification may it process? | PHI flows *through* it; the gateway reads none of it | Privacy officer | Approve the blast radius, not the use case |
| Data | May data leave the region? | Governed by the provider BAA and region | Privacy officer | Fixes which provider region |
| Data | Prompt and response retention? | The gateway keeps none; it logs metadata only | Privacy officer | Logs carry ids, tiers and token counts, never text |
| Data | DLP on egress? | Likely at the proxy | Security engineering | Adds latency to every call; measure it |
| Models | Approved internal LLM endpoint? | ✓ #8 | — | — |
| Models | Open-weights download allowed? | Not needed | — | — |
| Models | Model registry or approval? | Model choice stays with each workload | AI CoE | The gateway is model-agnostic |
| Legacy | What must it integrate with; owner? | Chat platform, claims summarizer, refresh job | Each workload owner | Each caller changes one call site |
| Legacy | Real-time or batch? | Chat and claims real-time; refresh batch | Content Operations | The refresh moves to the batch lane |
| Process | Who approves a deployment? | ✓ #7 | — | — |
| Process | Required review; how long? | Architecture review and change board | Enterprise architect | See the map below |
| Process | On call once live? | SRE, with the platform team as backup | SRE lead | Runbook and kill switch before go-live |
| Process | Rollback procedure? | Turn off the policy; calls pass straight through as they do today | SRE lead | The kill switch *is* the rollback: it returns to today's behaviour |

**The question that isn't on the list:** "What usually goes wrong?" Likely answers for this kind of gateway:
- The TLS-intercepting proxy breaks the provider SDK inside containers.
- Every team shares one provider key, so the provider's limit is per account, not per workload.
- An existing gateway policy already rate-limits and nobody remembers why.

---

## The checkpoint map

*How long* is my planning estimate, to be replaced with what each owner says. The point stands: this is the column managers want and nobody produces.

| What (gate) | Who | How long (estimate, to confirm) | What they need |
| --- | --- | --- | --- |
| Architecture review | Enterprise architect | 2–3 weeks to get a slot | Data-flow diagram with boundary crossings; `decisions.md` |
| Security and privacy sign-off | CISO / privacy officer | 2–4 weeks | Threat model (OWASP agentic list); blast-radius statement; no-PHI-in-logs evidence |
| Egress allowlist entry | Network / security engineering | 1–2 weeks | Provider host, port, purpose, owner |
| Image scan and signing | Security engineering | Days, once the pipeline exists | An image built from the mandated base |
| Tier policy sign-off | Member Services and Claims ops managers | One meeting, if they see the trade-off numbers | `CHARTER.md` § Success table; the replay rerun with their settings |
| Change approval | Change advisory board | Next scheduled board | Runbook, kill switch, rollback = policy off |
| Shadow run before enforcement | SRE lead + Member Services | One peak period | Dashboards: would-be sheds by tier, spend by department |

**Critical path:** the security review and the egress entry run in parallel from week 2. That's why the CISO conversation is in week 2 of `stakeholders.md`, not at the end.
