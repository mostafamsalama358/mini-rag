# Failure Vignette Catalog (018)

Used for defect attribution drills (quickstart §2, SC-002). Earliest broken contract wins.

| VignetteId | Symptom | Earliest Broken Contract | Owning Stage |
|------------|---------|--------------------------|--------------|
| V01 | Entity filter declared in plan ignored in retrieved candidates | C2 | Retrieval |
| V02 | Filter never declared though Understood Query had constraints | C9 / Planner duty | Retrieval Plan |
| V03 | Planner intent conflicts with Understood Query; no degradation reason | C9 | Retrieval Plan |
| V04 | Engine substitutes unplanned strategy family without trace | C1 | Retrieval |
| V05 | Definitive answer despite Evidence sufficiency=`missing` | C10 | Answer Generation |
| V06 | Answer claims completeness when sufficiency=`partial` and gaps unstated | C10 | Answer Generation |
| V07 | Evidence marks complete but required facet absent (dishonest coverage) | C10 | Evidence |
| V08 | Conflict candidates present; answer picks one side with no disclosure | C4 | Answer Generation |
| V09 | Budget drops one conflict side; answer claims sources agree | C4 | Context / Answer Generation |
| V10 | Citation references document never in Context citation map | C5 | Answer Generation |
| V11 | Included block missing citation map entry after compression | C5 | Context |
| V12 | Claim marked grounded with zero supporting included evidence | C12 | Answer Generation |
| V13 | Empty evidence; generative parametric fill-in returned | C7 | Answer Generation |
| V14 | Ambiguity/clarification_required ignored; high-confidence unconstrained plan | C9 | Retrieval Plan |
| V15 | Near-duplicates flood context; identity and content dedup both skipped | C3 | Retrieval / Evidence |
| V16 | Rerank disabled but Trace invents rerank scores | C11 | Retrieval |

**Themes covered**: filter loss (V01–V02), re-parse drift (V03), false completeness (V05–V07), silent conflict (V08–V09), broken citation (V10–V11), ungrounded claim (V12), hallucination/empty fill-in (V13), ambiguity ignore (V14), dedup failure (V15), trace honesty (V16).
