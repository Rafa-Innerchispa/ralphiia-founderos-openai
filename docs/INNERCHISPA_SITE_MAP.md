# InnerChispa site map and publication plan

Status: proposal for Issue #1. This branch does not publish production.

## What exists today

- Public domain reviewed: `https://www.innerchispa.us`
- Observed public deployment: static website served from shared hosting, with public DNS pointing at a shared-hosting server.
- Current page model: one static home page with animated visual treatment, Tailwind/browser-CDN styling, dark canvas background, ecosystem links, WhatsApp, Calendly, LinkedIn, and older “InnerSpark / Ecosystem Hub” copy.
- GitHub source audit: no repository named for `innerchispa.us` and no code match for the domain was found under the connected GitHub owner during this review.
- Operational conclusion: this repository is not confirmed as the current production source of `innerchispa.us`. It is the safest place to prepare a reviewable public-site proposal until Rafael confirms the exact shared-hosting folder or official website repository.

## Publication boundary

Production publication is intentionally out of scope for this PR. The proposed `site/` directory can be reviewed, copied, or deployed only after Rafael approves.

Safe publish path after approval:

1. Confirm the exact shared-hosting folder for `innerchispa.us`.
2. Download and archive the current production files before any upload.
3. Upload only the contents of `site/` into the confirmed domain folder.
4. Verify `/`, `/ralphiia/`, `/infrastructure/`, `/solutions/`, `/case-studies/pc-doctor/`, `/investors/`, `/investors/deck/`, and `/impact/`.
5. Roll back by restoring the archived production files if anything fails.

## Content architecture

| Route | Purpose | Primary message | Evidence level |
| --- | --- | --- | --- |
| `/` | Public landing page | InnerChispa builds sovereign AI operations for real businesses. | Current positioning proposal |
| `/ralphiia/` | Product page | RalphiIA is the principal operations agent, not a chatbot. | Working-system narrative |
| `/infrastructure/` | Architecture page | Hybrid local/cloud intelligence, governed tools, memory, voice, human approval, and data sovereignty. | Sanitized architecture only |
| `/solutions/` | Commercial pipeline page | Active deployments and discovery-stage opportunities without overstating revenue or signed customers. | Qualified pipeline labels |
| `/case-studies/pc-doctor/` | First transformation case | PC Doctor is the active internal deployment and live validation environment. | Active internal deployment |
| `/investors/` | Fundraising page | InnerChispa is raising US$250K to productize RalphiIA and convert the pipeline into paid design partnerships. | Fundraising narrative |
| `/investors/deck/` | Stable deck route | Lightweight public pitch-deck route for investor sharing. | Public summary deck |
| `/impact/` | Mission and outcomes | Operational memory and pattern identification can improve service, health-adjacent workflows, and human accompaniment. | Directional, non-medical claims |

## Stable site versus living lab

InnerChispa now needs two public layers:

- `www.innerchispa.us`: the official, stable, low-risk public website. It should explain the company, RalphiIA, the sanitized infrastructure model, PC Doctor validation, investor narrative, and current commercial pipeline.
- `lab.innerchispa.us`: the living lab. It can show experimental interfaces, emerging maps, live demos, Astro prototypes, and evolving views of the system, but it should remain clearly labeled as a lab until Rafael approves any feature for the official site.

The team has private servers that provide different services and may include Astro or real-time components. Those internal addresses, ports, and operational details should not be published in the public repository or public site. Public copy should describe them only as “private local infrastructure,” “live lab services,” or “hybrid local/cloud systems.”

## Claim policy

Safe to publish:

- Working hybrid infrastructure
- Local inference
- Cloud intelligence
- Governed tools
- Operational memory
- Voice-enabled workflows
- Human approval checkpoints
- Active PC Doctor workflows
- Active development and proposal-stage opportunities

Must be qualified:

- Time savings
- Revenue pipeline
- Users
- ROI
- Recurring revenue
- Reliability

Do not publish without evidence:

- Signed customers
- Paid revenue
- Production deployments outside confirmed scope
- Guaranteed outcomes

## Security and privacy boundary

The public site must not expose internal IP addresses, ports, tunnel URLs, API headers, keys, raw logs, customer-private data, unresolved infrastructure issues, or sensitive service internals.

## Design direction

- Preserve the living-system feeling of the current site: animated background, luminous gradients, and “ecosystem map” energy.
- Reduce the heavy black look by shifting toward warm off-white surfaces, deep indigo text, glass panels, coral/gold/cyan accents, and soft animated orbs.
- Keep the page mobile-first and bilingual-ready.
- Make every page understandable to a first-time visitor: what InnerChispa is, what RalphiIA does, why PC Doctor matters, and what the current investment/pipeline status really is.

## Review checklist for the PR

- Required pages exist.
- English and Spanish content are available through the language switcher.
- SEO metadata and JSON-LD are present.
- Public copy distinguishes InnerChispa, RalphiIA, and PC Doctor.
- Commercial pipeline labels are accurate and qualified.
- Architecture diagram is sanitized.
- Investor page includes the US$250K pre-seed narrative and stable deck route.
- Static tests pass.
- No production deploy happens before Rafael approval.
