# ODOS 0.1 normative profile

**Status:** approved OGIP profile  
**Version:** 0.1  
**Scope:** Dagster 1.13 and Prefect 3.4 or newer

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Boundary

ODOS describes orchestration: jobs, orchestration-native assets, automations, checks, hooks,
partitions, retries, concurrency, and failure reactions. Transformations belong to ODTS and
MUST NOT be embedded in ODOS. Instance/deployment configuration and orchestrator Components
MUST remain outside portable ODOS documents.

An implementation MUST support exactly the targets it declares. The 0.1 OGIP profile declares
`dagster` and `prefect`. A construct that cannot be projected to a requested target MUST fail
compilation unless its object has an explicit `targets` restriction. Silent omission is
forbidden.

## 2. Documents and versioning

An ODOS group document is YAML with these required top-level keys:

```yaml
odos: 0.1
group: warehouse
```

It MAY contain `doc`, `assets`, `jobs`, `automations`, `checks`, and `hooks`. One file represents
one group. Every object in those sections MAY contain `doc`, `tags`, and `targets`. Unknown keys
MUST be rejected.

The version applies to the whole file. Blocks MUST NOT carry independent versions.

Documents use YAML 1.2 semantics. Authors SHOULD quote the key `"on"` so YAML 1.1-compatible
loaders do not coerce it to the boolean key `true`.

`_defaults.yml` is a distinct document form. It requires `odos`, `owner`, and `registry`, and MAY
define named `partitions` and job `defaults`. Defaults are merged into every job; an explicit
job value wins.

## 3. Names and task registry

Asset keys and task names are dotted identifiers such as `core.game` and `dbt.build`.
Orchestrator-native key tuples and import paths MUST NOT appear in the portable form.

Every `task` and every callable named by `poll(...)` MUST resolve in the configured closed task
registry. Registry functions MUST be plain typed functions addressable by name. An unknown name
MUST fail compilation. A shell escape hatch is not part of ODOS 0.1.

## 4. Jobs

A job has exactly one of two forms:

- asset job: `select`;
- task job: `task`, optionally with keyword `args`.

The selection grammar is deliberately closed:

```text
name | name+ | +name | tag:name
```

A selection MAY be one expression or a non-empty list. `name+` is downstream closure and
`+name` is upstream closure. The compiler MUST expand selections against the ODTS lineage graph
plus ODOS-native assets.

`partitioned: true` is valid only when every selected asset shares one named partition
definition. The compiler MUST reject a mixed or missing partition definition.

Jobs MAY define:

```yaml
retry: { max_attempts: 3, type: exponential, interval: PT1M }
concurrency: { limit: 1, behavior: cancel }
on_failure: alerting.notify_run_failure
```

Retry intervals MUST use ISO-8601 durations. Retry type is `constant` or `exponential`.
Concurrency behavior is `queue`, `cancel`, or `fail`.

## 5. Assets

`assets` declares only assets that exist in neither ODTS nor an external component. An asset
requires a registry `task` and MAY define a named `partitions`, `kinds`, and `group_name`.
Portable asset keys remain dotted names; target adapters own their concrete key mapping.

## 6. Automations

An automation has one `on` expression from this closed set:

```text
cron("<cron>")
asset_materialized(<asset>)
poll(<registry-name>, every=<duration>)
partition_ready(<job>)
```

The first three forms require `run`, naming a job in the same compiled model.
`partition_ready(...)` names its job in the expression and MUST NOT also declare `run`.

`poll` callables return a cursor token or `None`. Dagster may own the cursor natively; a Prefect
projection requires an external cursor store. Selecting that store is an implementation
decision, but both projections MUST preserve identical comparison semantics.

`asset_materialized` projects to native asset events in both targets. Implementations MUST
document that cached Prefect tasks emit no materialization event.

## 7. Checks and hooks

A check requires `asset` and registry `task`, and MAY set `blocking`. Checks are correctness
gates. Freshness, volume anomaly, and schema drift are observability concerns and are outside
this section.

A hook requires `on`, `task`, and an explicit `targets` restriction. ODOS 0.1 defines the
location-scoped expression `run_failed(scope=location)`. Portable failure handling SHOULD use
job-level `on_failure`; hooks are for genuinely target-specific scope.

## 8. Capability requirements

| Construct | Dagster | Prefect | Required projection |
|---|---|---|---|
| `select` job | asset job | ordered flow | ODTS graph-derived |
| `task` job | job/op | flow/task | direct |
| asset | asset | materialize | direct |
| `cron` | schedule | deployment schedule | direct |
| `asset_materialized` | asset sensor | reactive event automation | direct |
| `poll` | cursor sensor | scheduled poll + external cursor | equivalent semantics |
| `partition_ready` | partition schedule | cron + partition argument | equivalent semantics |
| check | asset check | post-asset validation task | equivalent result |
| location hook | run-failure sensor | unavailable | target-restricted |
| resilience | native | native | direct |

## 9. Compilation and conformance

The frontend MUST:

1. validate the closed YAML vocabulary;
2. merge defaults;
3. resolve task and poll names against the registry;
4. resolve job, partition, asset, and automation cross-references;
5. expand selections against ODTS lineage;
6. enforce the capability/failure policy;
7. emit a typed intermediate representation before target rendering.

For every job projected to both targets, conformance tests MUST assert the same ordered registry
task sequence with identical keyword arguments. A conforming implementation MUST also test:

- successful compilation of every group for every requested target;
- target definitions load successfully;
- committed generated output matches a fresh compilation;
- unknown keys and task names fail;
- unprojectable objects without `targets` fail.

## 10. Deferred from 0.1

Task-level graphs inside a job, parameterized inputs, and backfill policy declarations are
deferred. They are not accepted as extension keys: the closed-vocabulary rule still applies.
