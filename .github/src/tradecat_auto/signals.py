from __future__ import annotations

from typing import Any

from tradecat_auto.safety_boundary import paper_watch_safety_boundary

MIN_TRADABLE_SCORE = 60
MAX_SPREAD_BPS = 10.0
MIN_QUOTE_VOLUME_USDT = 1_000_000.0


def build_signal_score(enrichment: dict[str, Any]) -> dict[str, Any]:
    symbol = str(enrichment.get("symbol") or "").upper().strip()
    if not enrichment.get("ok"):
        return _payload(
            symbol=symbol,
            score=0,
            direction="WATCH_ONLY",
            positive_factors=[],
            negative_factors=[],
            do_not_trade_reasons=["enrichment_not_ok"],
            metrics=enrichment.get("metrics") if isinstance(enrichment.get("metrics"), dict) else {},
            enrichment=enrichment,
        )

    metrics = enrichment.get("metrics") if isinstance(enrichment.get("metrics"), dict) else {}
    state = _score_state()
    _apply_price_change(metrics, state)
    _apply_liquidity(metrics, state)
    _apply_spread(metrics, state)
    _apply_open_interest(metrics, state)
    _apply_funding(metrics, state)
    _apply_taker_bias(metrics, state)
    _apply_long_short_bias(metrics, state)
    direction = _signal_direction(metrics, state)
    do_not_trade = _final_do_not_trade(state)
    return _payload(
        symbol=symbol,
        score=min(state["score"], 100),
        direction=direction,
        positive_factors=_dedupe(state["positive"]),
        negative_factors=_dedupe(state["negative"]),
        do_not_trade_reasons=do_not_trade,
        metrics=metrics,
        enrichment=enrichment,
    )


def _score_state() -> dict[str, Any]:
    return {
        "score": 20,
        "positive": ["sheet_anomaly_present"],
        "negative": [],
        "do_not_trade": [],
        "long_bias": 0,
        "short_bias": 0,
    }


def _apply_price_change(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    price_change = _num(metrics.get("price_change_24h_pct"))
    if price_change is None:
        return
    abs_change = abs(price_change)
    if abs_change >= 20:
        state["score"] += 20
        state["positive"].append("large_24h_price_move")
    elif abs_change >= 10:
        state["score"] += 10
        state["positive"].append("moderate_24h_price_move")


def _apply_liquidity(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    quote_volume = _num(metrics.get("quote_volume_24h"))
    if quote_volume is not None and quote_volume >= MIN_QUOTE_VOLUME_USDT:
        state["score"] += 10
        state["positive"].append("liquid_24h_quote_volume")
    else:
        state["negative"].append("low_quote_volume")


def _apply_spread(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    spread_bps = _num(metrics.get("spread_bps"))
    if spread_bps is not None and spread_bps <= MAX_SPREAD_BPS:
        state["score"] += 10
        state["positive"].append("tight_spread")
    else:
        state["negative"].append("spread_too_wide")
        state["do_not_trade"].append("spread_too_wide")


def _apply_open_interest(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    if (_num(metrics.get("open_interest")) or 0) > 0:
        state["score"] += 10
        state["positive"].append("open_interest_available")


def _apply_funding(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    funding_abs = abs(_num(metrics.get("funding_rate_latest")) or 0)
    if funding_abs <= 0.001:
        state["score"] += 5
        state["positive"].append("funding_not_extreme")
    else:
        state["negative"].append("funding_extreme")


def _apply_taker_bias(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    taker_ratio = _num(metrics.get("taker_buy_sell_ratio"))
    if taker_ratio is None:
        return
    if taker_ratio >= 1.05:
        state["long_bias"] += 1
        state["score"] += 10
        state["positive"].append("taker_buy_bias")
    elif taker_ratio <= 0.95:
        state["short_bias"] += 1
        state["score"] += 10
        state["positive"].append("taker_sell_bias")


def _apply_long_short_bias(metrics: dict[str, Any], state: dict[str, Any]) -> None:
    for key in ("global_long_short_account_ratio", "top_long_short_account_ratio", "top_long_short_position_ratio"):
        ratio = _num(metrics.get(key))
        if ratio is None:
            continue
        if ratio >= 1.05:
            state["long_bias"] += 1
            state["score"] += 3
            state["positive"].append(f"{key}_long_bias")
        elif ratio <= 0.95:
            state["short_bias"] += 1
            state["score"] += 3
            state["positive"].append(f"{key}_short_bias")


def _signal_direction(metrics: dict[str, Any], state: dict[str, Any]) -> str:
    if state["score"] < MIN_TRADABLE_SCORE or state["do_not_trade"]:
        state["do_not_trade"].append("low_score")
        return "WATCH_ONLY"
    price_change = _num(metrics.get("price_change_24h_pct")) or 0
    if price_change >= 0 and state["long_bias"] >= state["short_bias"]:
        return "LONG"
    if price_change < 0 and state["short_bias"] > state["long_bias"]:
        return "SHORT"
    state["do_not_trade"].append("direction_conflict")
    return "WATCH_ONLY"


def _final_do_not_trade(state: dict[str, Any]) -> list[str]:
    do_not_trade = list(state["do_not_trade"])
    if state["score"] >= MIN_TRADABLE_SCORE and "low_score" in do_not_trade:
        do_not_trade.remove("low_score")
    return _dedupe(do_not_trade)


def _payload(
    *,
    symbol: str,
    score: int,
    direction: str,
    positive_factors: list[str],
    negative_factors: list[str],
    do_not_trade_reasons: list[str],
    metrics: dict[str, Any],
    enrichment: dict[str, Any],
) -> dict[str, Any]:
    error_code = do_not_trade_reasons[0] if do_not_trade_reasons else None
    return {
        "schema": "tradecat_auto.signal_score.v1",
        "schema_version": "1.0.0",
        "ok": True,
        "error_code": error_code,
        "symbol": symbol,
        "score": score,
        "direction": direction,
        "tradable_candidate": bool(
            direction in {"LONG", "SHORT"} and score >= MIN_TRADABLE_SCORE and not do_not_trade_reasons
        ),
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "do_not_trade_reasons": do_not_trade_reasons,
        "metrics_used": {
            key: metrics.get(key)
            for key in (
                "price_change_24h_pct",
                "quote_volume_24h",
                "spread_bps",
                "open_interest",
                "funding_rate_latest",
                "taker_buy_sell_ratio",
                "global_long_short_account_ratio",
            )
        },
        "provenance": _provenance(enrichment),
        "safety": paper_watch_safety_boundary(),
        "limitations": ["signal only; not an order and not investment advice"],
    }


def _provenance(enrichment: dict[str, Any]) -> dict[str, Any]:
    enrichment_provenance = enrichment.get("provenance") if isinstance(enrichment.get("provenance"), dict) else {}
    return {
        "source": "tradecat_auto.signals.build_signal_score",
        "enrichment_schema": str(enrichment.get("schema") or ""),
        "enrichment_source": str(enrichment_provenance.get("source") or ""),
    }


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
