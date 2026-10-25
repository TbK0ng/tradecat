# Test Strategy

TradeCat Public is a headless Agent paper-trading runtime with an embedded Skill package. Tests protect three boundaries: public signal ingestion, Agent market-context contracts, and local paper/watch execution.

## Core Test Areas

| Area | Risk | Examples |
| --- | --- | --- |
| Skill/manifest governance | Agent gets stale or unsafe commands | `.github/tests/test_agent_contract.py` |
| Public sheet request contract | Wrong tap, partial rows, missing provenance | `.github/tests/test_transport.py`, `.github/tests/test_dataset_consumption_contract.py` |
| Agent market context audit | Signed/private/account data enters pipeline | `.github/tests/test_agent_market_context.py` |
| Thesis sizing/exits | TradeCat invents defaults or swallows missing inputs | `.github/tests/test_pipeline.py`, `.github/tests/test_service.py` |
| Paper ledger | Duplicate positions, bad mark-to-market, missing exits | `.github/tests/test_paper_ledger.py`, `.github/tests/test_paper_broker.py` |
| Runtime reports | Health/daily/replay/audit evidence drifts | `.github/tests/test_replay_reporting.py`, `.github/tests/test_audit_journal.py`, `.github/tests/test_production_control.py` |
| Repository governance | Collaboration files, CI gates, and local runtime boundaries drift | `.github/tests/test_public_repo_guardrails.py` |
| Safety scans | Credentials or private executor code leaks | `.github/scripts/security-scan.sh`, `.github/scripts/supply-chain-audit.sh` |

## Required Local Gate

```bash
bash .github/scripts/agent-smoke.sh
bash .github/scripts/verify.sh
bash .github/scripts/validate-skill.sh --strict
bash .github/scripts/security-scan.sh
bash .github/scripts/supply-chain-audit.sh
python3 .github/scripts/validate_dependency_policy.py
ruff format --check .github/src .github/tests .github/scripts
git diff --check
```

## Regression Checklist

- `src/tradecat_terminal/`, root installers, and old watchdog scripts stay absent.
- `.github/scripts/request.py` can list datasets and fetch `signal_flow` / `anomaly_panel`.
- `context-audit` rejects signed requests, key-like fields, account/order endpoints, and true safety flags.
- Missing Agent sizing/exits remains fail-closed.
- Explicit Agent sizing/exits can open paper positions.
- Same-symbol concurrency remains single-position by default and requires explicit Agent authorization to expand.
- Reports retain `schema_version=1.0.0`, error codes, provenance, and safety fields.
- Runtime files remain under ignored `.github/.runtime/`.

## Performance Notes

The hot path is cyclic signal ingestion and paper runtime reporting. Keep sheet reads bounded, deduplicate repeated snapshot/event inputs, avoid unbounded Agent context payloads, and prefer schema validation plus small JSON reports over large opaque logs. Any future high-frequency loop must add timing metrics and bounded retry/backoff before increasing poll rate.
