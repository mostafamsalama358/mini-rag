# Quickstart: Unified Pipeline Migration Validation

**Feature**: 015-unified-pipeline-migration | **Architecture validation guide**

This guide defines how to validate the migration design once implemented. It does NOT contain
implementation code — see `tasks.md` (Phase 2) for build tasks.

**Prerequisites**: Docker Compose stack running (Postgres, API, worker); indexed project with
golden fixture documents; specs 009–013 modules present in `src/core/`.

---

## 1. Verify Phase 0 — Foundation (legacy default)

### Setup

```bash
# .env
RAG_PIPELINE_MODE=legacy
RAG_SEMANTIC_PARSER_ENABLED=true
```

### Validate

1. Start API: `docker compose up api`
2. Send answer request:

```bash
curl -s -X POST "http://localhost:8000/api/v1/nlp/1/answer" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the dosage?", "limit": 8}'
```

3. **Expected**: HTTP 200, `signal=RAG_ANSWER_SUCCESS`, response keys exactly:
   `signal`, `answer`, `needs_clarification`, `full_prompt`, `chat_history`
4. **Expected logs**: No `rag_pipeline_mode=unified` entries
5. Run contract tests: `pytest tests/contract/test_answer_api.py -v`

**Pass criteria**: Identical behavior to pre-migration baseline.

---

## 2. Verify Unified Path (dev only)

### Setup

```bash
RAG_PIPELINE_MODE=unified
RAG_PIPELINE_FALLBACK_ON_ERROR=true
```

### Validate

1. Send same curl as above
2. **Expected logs**: Stage sequence `parse → plan → retrieve → evidence → context → answer`
3. **Expected metrics** (Prometheus): `rag_pipeline_stage_duration_seconds{stage="plan"}` populated
4. **Expected**: `plan_id` and `context_id` in structured log (not in HTTP body)

```bash
pytest tests/integration/test_unified_pipeline.py -v
```

**Pass criteria**: All stage traces present; API contract test passes.

---

## 3. Verify Shadow Mode

### Setup

```bash
RAG_PIPELINE_MODE=shadow
RAG_PIPELINE_SHADOW_PERSIST=true
RAG_PIPELINE_SHADOW_DIR=.rag_shadow/
```

### Validate

1. Send 10 varied questions via curl or golden fixture script
2. **Expected**: HTTP responses match `RAG_PIPELINE_MODE=legacy` run on same inputs
3. **Expected artifacts**: `.rag_shadow/YYYY-MM-DD/comparisons.jsonl` with 10 records
4. Inspect record fields per `data-model.md::ShadowComparisonRecord`

```bash
pytest tests/integration/test_shadow_mode.py -v
```

**Pass criteria**:

- User-visible responses == legacy-only run
- JSONL records written for each request
- Unified failure does not change HTTP status/answer

---

## 4. Verify Rollback

### Setup

1. Set `RAG_PIPELINE_MODE=unified`; confirm unified logs on one request
2. Flip to `RAG_PIPELINE_MODE=legacy`; restart API
3. Send same request

### Validate

- **Expected**: No unified stage logs after flip
- **Expected metric**: `rag_pipeline_requests_total{mode="legacy"}` increments

**Pass criteria**: Rollback completes in < 5 minutes including restart.

---

## 5. Verify Fallback on Unified Error

### Setup

```bash
RAG_PIPELINE_MODE=unified
RAG_PIPELINE_FALLBACK_ON_ERROR=true
```

### Validate

1. Simulate unified failure (test harness injects exception in orchestrator mock)
2. **Expected**: User receives legacy-equivalent answer; log contains
   `pipeline_fallback_total{reason="..."}`

```bash
pytest tests/integration/test_pipeline_fallback.py -v
```

---

## 6. Golden Quality Gate (spec 014)

### Setup

Golden fixtures at `tests/fixtures/answer_quality/*.yaml`

### Validate

```bash
# Baseline (legacy)
RAG_PIPELINE_MODE=legacy pytest tests/integration/test_pipeline_regression.py -v

# Candidate (unified) — offline golden scaffold
python scripts/run_unified_golden_eval.py \
  --fixtures tests/fixtures/answer_quality/golden.json \
  --out eval_run/unified_golden_result.json

# Shadow nightly aggregation
python scripts/aggregate_shadow_reports.py \
  --shadow-dir .rag_shadow \
  --out eval_run/shadow_aggregate.json

# Candidate (unified) pytest gate
RAG_PIPELINE_MODE=unified pytest tests/integration/test_pipeline_golden_quality.py -v
```

**CI gate thresholds** (from plan.md):

- `EvaluationResult.passed` true for unified
- Pass rate ≥ baseline − 5% (fail the job if `pass_rate < baseline_pass_rate - 0.05`)
- Shadow divergence rate reviewed before promoting canary (`divergence_rate` from aggregate script)
- `RegressionDiff.has_regressions` false or reviewed

**Baseline save/compare commands**:

```bash
# Save baseline EvaluationResult JSON
cp eval_run/unified_golden_result.json eval_run/baselines/unified_baseline.json

# Compare candidate vs baseline (threshold 5pp)
python -c "import json,sys; b=json.load(open('eval_run/baselines/unified_baseline.json')); c=json.load(open('eval_run/unified_golden_result.json')); sys.exit(0 if c.get('pass_rate',0)>=b.get('pass_rate',0)-0.05 else 1)"
```

See [014 quickstart](../014-answer-quality/quickstart.md) for evaluator details.

---

## 7. Canary Project Override

### Setup

```bash
RAG_PIPELINE_MODE=legacy
RAG_PIPELINE_CANARY_PROJECT_IDS=42
```

Set `project.config_json` for project 42: `{"pipeline_mode": "unified"}` (optional override test)

### Validate

- Request to project 42 → unified logs
- Request to project 1 → legacy logs

---

## 8. Production Rollout Smoke Checklist

Before setting `RAG_PIPELINE_MODE=unified` in production:

- [ ] Shadow run ≥ 7 days in staging
- [ ] Divergence rate reviewed (`rag_shadow_divergence_total / requests`)
- [ ] Golden pass rate within threshold
- [ ] Rollback drill executed
- [ ] On-call runbook updated with flag locations
- [ ] Dashboard panels for stage latencies and mode distribution

---

## Related Artifacts

- Architecture: [plan.md](../plan.md)
- Orchestrator contracts: [contracts/orchestrator.md](../contracts/orchestrator.md)
- Adapter contracts: [contracts/adapters.md](../contracts/adapters.md)
- API stability: [contracts/api-stability.md](../contracts/api-stability.md)
- Data model: [data-model.md](../data-model.md)

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Unified path never invoked | `RAG_PIPELINE_MODE`, project override, canary list |
| Shadow files empty | `RAG_PIPELINE_SHADOW_PERSIST`, directory permissions |
| API schema test fails | `ResponseAdapter` mapping; do not add fields to JSON |
| Type errors at evidence stage | `type_mapping.py` round-trip tests |
| Both stacks in one request | Ensure orchestrator does not call `NLPController.search_*` |
