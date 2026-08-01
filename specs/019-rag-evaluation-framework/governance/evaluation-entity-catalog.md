# Evaluation Entity Catalog (019)

Logical entities from [`../data-model.md`](../data-model.md). Physical type names are non-normative.

| Entity | Purpose | Key fields (logical) |
|--------|---------|----------------------|
| EvaluationDataset | Versioned labeled collection | dataset_id, version, tier, lifecycle_state, lineage, changelog_ref, approval |
| EvaluationItem | Single scored unit | item_id, query, labels, slice_tags, match_mode |
| Benchmark | Governed offline corpus | benchmark_id, version, tags, pinned_dataset_refs |
| EvaluationProfile | Reusable suite binding | profile_id, dataset_tiers, enabled_metrics, gate_type |
| RunPolicy | Concrete run policy | profile pins, cutoffs, baseline, judges, gate |
| Judge | Abstract judgment producer | judge_type, judge_version, precedence_notes |
| EvaluationRun | Persisted scoring execution | run_id, metadata, aggregates, gate_decision |
| ItemResult | Per-item outcomes | metric_scores, error categories, root_cause_annotation |
| MetricDefinition | Canonical metric + ownership | metric_id, primary_owner, honesty_rules |
| MetricScore | One metric on one item | value, status, confidence?, judge_version? |
| CompositeQualityScore | Derived rollup | composite_id, coverage_declaration, drilldown_refs |
| RegressionGate | Named decision gate | gate_class, decision, failed_item_ids |
| BaselineDiff | Run comparison | deltas, regressed items |
| ExperimentRef | Role assignment | Baseline…Canary |
| MonitoringWindow | Rolling live window | drift statuses |
| Alert | Monitoring notification | alert_category, related_gate |
| DatasetVersionLineage | Version genealogy | predecessor, changelog |
)
