## What changed

- 

## Why

- 

## How tested

- [ ] `bash .github/scripts/agent-smoke.sh`
- [ ] `bash .github/scripts/verify.sh`
- [ ] `bash .github/scripts/validate-skill.sh --strict`
- [ ] `bash .github/scripts/security-scan.sh`
- [ ] `bash .github/scripts/supply-chain-audit.sh`
- [ ] `git diff --check`

## Safety boundary

- [ ] Public/read-only market data only
- [ ] Paper/watch only
- [ ] No Binance key/secret/listen key reads
- [ ] No signed requests
- [ ] No account/order/leverage/margin private endpoints
- [ ] No real orders
- [ ] No default sizing/exits invented by TradeCat

## Risk and rollback

- Risk:
- Rollback:
