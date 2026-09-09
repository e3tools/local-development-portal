# Draft brief: AI chat on the Local Development Portal (LDP) for development partners

**Status:** draft v0.1 · **Owner:** TBD · **Date:** 2026-09-09
**Ask:** decide whether we build this, in which shape, and what v1 must ship.

## 1. The point

Development partners (IDA/COSO, AFD, GIZ, UNICEF, PNUD, BOAD, ANADEB, UE, Plan) already have read access to the LDP, but they don't use it: they email the UCP for numbers, and the UCP answers by hand.
We add a chat panel to the portal so a partner can ask questions in plain French or English ("Which cantons in Savanes have a water priority nobody funds?") and get an answer computed from the live portal data, with links back to the pages the answer came from.

Goal: partners self-serve 80 % of their data questions. UCP stops being the reporting bottleneck.

## 2. Who it's for and what they ask

Primary users: partner focal points and programme officers (see `/partenaires` and the read-only partner role in `/utilisateurs`). Secondary: UCP M&E team, regional coordinators.

Questions we heard or expect (all answerable from data the portal already holds):

- Coverage / targeting: "Villages with vulnerability > 70 and no functional water point in Kpendjal." "Population covered by our projects in Kara."
- Gaps and overlap: "Priorities validated by CCD in the Education sector with no funding partner." "Where do AFD and UNICEF both position on water in the same canton?"
- Pipeline: "Sub-projects stuck at the regional review for more than 30 days." "Disbursement rate of IDA-funded sub-projects by region."
- Accountability: "Open grievances linked to our sub-projects." "Average resolution time for HIMO payment complaints."
- Reporting: "Give me a one-paragraph summary of Centrale for our quarterly report, with the numbers."

Out of scope for v1: writing to the portal (no creating priorities, no approving packages), free-form policy advice, anything about individuals.

## 3. Scope

**v1 (ship it):**
- Chat panel inside the portal, available to signed-in users with the partner role and UCP roles.
- Answers grounded in the portal's data only. Every answer shows the figures used and links to the LDP page (village, canton, sub-project, partner).
- Read-only. The model can run queries, never mutations.
- French and English; the answer follows the question's language.
- Suggested questions per page (on a canton page: "Compare this canton to its prefecture").
- Export answer as table/CSV.

**v2 (if v1 gets used):**
- Scheduled briefs ("email me new grievances on our sub-projects every Monday").
- Charts in answers.
- Partner-uploaded documents (their own project lists) matched against the registry to spot overlaps.

**Never:** access to sensitive GRM records (VBG/EAS/HS), complainant identities, or user-management data. Hard filter at the data layer, not in the prompt.

## 4. Data it speaks to

Same entities the portal already renders (today mock, later the real COSO-MIS database):

| Domain | Entities | Partner-visible? |
|---|---|---|
| Territories | region, prefecture, canton, village profile (demography, infrastructure, CVD, vulnerability) | Yes |
| Priorities registry | priority, rank, sector, status, estimated cost, beneficiaries | Yes |
| Investment packages | sub-project, budget, disbursement, progress, approval steps, contractor | Yes, all partners (not only their own) |
| GRM | grievance counts, categories, status, delays, satisfaction | Aggregates only; no free-text summaries, no sensitive category rows |
| Partners | positions by region × sector, commitments | Yes |
| Users | accounts, roles | No |

Assumption: the production data model matches the portal's (see `src/data/*.ts` in the mockup). If the COSO-MIS schema differs, the query layer below is where we absorb it.

## 5. How we build it (recommendation)

Three options were considered:

| Option | How | Pros | Cons |
|---|---|---|---|
| A. Text-to-SQL | Model writes SQL against a read replica | Flexible, fast to prototype | Hard to enforce row/column restrictions; wrong joins produce confident wrong numbers; hard to audit |
| B. Tool calling over a typed query API (**recommended**) | Model picks from ~15 predefined query functions (filters, aggregations) that we write and test | Access rules live in code; every answer reproducible; easy to unit test; portal pages can reuse the same functions | Less flexible; new question types need a new function |
| C. RAG over exported reports | Embed PDFs/reports and retrieve | Cheap | Stale, no computation, cannot answer "how many" reliably |

Go with B. Reasoning: the value is trust. A partner will use this once, and if the number is wrong they never come back. Typed queries are the only option where we can say "every number is computed by code we tested".

Shape of v1:

- **Query API** (server-side, TypeScript): `listVillages(filters)`, `aggregatePriorities(groupBy, filters)`, `listSubprojects(filters)`, `approvalDelays(filters)`, `grmStats(groupBy, filters)`, `partnerPositions(filters)`, `comparePlaces(a, b)`. Each function applies the caller's role scope before running.
- **Model:** Claude via the Anthropic API with tool use. Sonnet-class model for routine questions; escalate to Opus-class only when the model requests a multi-step plan (cost control).
- **Grounding contract:** the model may only state figures returned by a tool call. Answer template: short answer, table of figures, "Sources" list of portal links, "Data as of" timestamp. If the tools can't answer, it says so and suggests who at UCP to ask.
- **Surface:** side panel in the portal shell, keeps the current page as context (canton page → canton pre-filtered).
- **Logging:** every question, tool calls, and answer stored for audit and for building the eval set.

## 6. Guardrails and risks

- **Data protection:** partner scope enforced in the query API, not the prompt. Sensitive GRM categories and complainant fields never leave the database layer. Users module excluded entirely.
- **Wrong answers:** mitigated by typed queries plus a golden set of 50 question/answer pairs run before each release. Target: 95 % exact-figure match.
- **Over-reliance:** answers carry "computed from LDP data on <date>, not an official UCP statement". Official reporting stays with UCP.
- **Cost:** budget cap per user per day; typical question should be well under 10 tool calls. We measure in the pilot before committing to a plan.
- **Language quality:** French is primary; we test French prompts first, English second.
- **Adoption risk:** partners may still email. Mitigation: UCP replies to data emails with a link to the chat and the answer it gave.

## 7. Success metrics (pilot, 8 weeks, 3 partners)

- ≥ 60 % of pilot partner data requests answered in chat without UCP involvement.
- ≥ 90 % of answers rated "correct" in the weekly spot check (20 answers/week).
- Median time to answer < 20 s.
- Zero sensitive-data exposure incidents (checked by automated tests plus manual review of logs).

## 8. Plan

| Phase | Weeks | Output |
|---|---|---|
| 0. Align | 1 | This brief approved; data owner at UCP named; 3 pilot partners confirmed |
| 1. Query API + access rules | 2–3 | Typed query functions over the real schema, tests, role scoping |
| 2. Chat v1 | 4–5 | Panel in portal, tool-use loop, answer template, logging |
| 3. Eval + hardening | 6 | Golden set, red-team for data leakage, cost measurement |
| 4. Pilot | 7–14 | 3 partners, weekly review, decision on v2 |

Team: 1 full-stack dev, 0.5 data/M&E lead from UCP, 0.25 product. External: Anthropic API account under the project.

## 9. Open questions / decisions needed

1. **Data source for v1:** production COSO-MIS read replica, or the mockup dataset first to validate the UX? Recommendation: mockup for weeks 1–3, real data from week 4.
2. **Who owns answer accuracy** when a partner quotes a chat answer in a report? Proposal: UCP M&E lead signs off on the golden set; disclaimer on every answer.
3. **Hosting / data residency:** is sending aggregated figures to a third-party model API acceptable under the project's data agreement? Needs a yes from the Bank/UCP safeguards team before phase 2. Aggregates only, no personal data, but we need it in writing.
4. **Partner scope:** can every partner see every other partner's positions and sub-projects (today's portal says yes)? Confirm with UCP; this decides the access rules in phase 1.
5. **Languages beyond FR/EN:** not for v1. Confirm.

## Appendix: example exchange

> **Partner (AFD):** Quelles priorités eau validées par le CCD dans les Savanes n'ont aucun partenaire positionné ?
>
> **Assistant:** 14 priorités « Eau & assainissement » validées CCD ou intégrées au PDC dans la région Savanes n'ont pas de sous-projet financé, pour un coût estimé cumulé de 312 M FCFA. Elles se concentrent dans les cantons de Mandouri (4), Borgou (3) et Timbou (3).
> *(table: code, village, canton, coût estimé, statut)*
> Sources : Registre des priorités (filtres : Savanes, Eau & assainissement, statut ≠ Financée) · Profils cantons Mandouri, Borgou, Timbou · Données au 09/09/2026.
