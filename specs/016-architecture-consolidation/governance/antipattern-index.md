# Anti-Pattern Index (AP1–AP14)

**Normative**: [`../spec.md`](../spec.md) Forbidden Architecture Patterns  
**Supersession**: Requires ADR with scope, duration, exit — see [`exception-adr-template.md`](./exception-adr-template.md)

| ID | Anti-Pattern | Related |
|----|--------------|---------|
| AP1 | Parallel production implementations | P2, P4 |
| AP2 | Duplicate canonical contracts for one concept | P3 |
| AP3 | Multiple owners for the same concern | P1, I7 |
| AP4 | Business orchestration inside infrastructure | I4 |
| AP5 | Domain logic inside Composition | P8 |
| AP6 | Core depending on concrete infrastructure | P5, P7, I8 |
| AP7 | Pipeline bypasses that skip owned concerns while claiming the capability | I13 |
| AP8 | Feature flags as permanent architecture | P4 |
| AP9 | Temporary migration code becoming permanent | P11 |
| AP10 | Hidden production paths | I13 |
| AP11 | Duplicate lifecycle ownership | P10 |
| AP12 | Owner chosen by age, folder, or historical package name | Owner Selection Criteria |
| AP13 | Treating inactive capabilities as production-complete in docs | P10, I12 |
| AP14 | Prescribing implementation layout as architecture | P9, P13 |
