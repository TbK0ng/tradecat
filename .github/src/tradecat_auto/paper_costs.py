from __future__ import annotations

from typing import Any

from tradecat_auto.safety_boundary import paper_watch_safety_boundary

SCHEMA_VERSION = "1.0.0"
PAPER_COST_MODEL_SCHEMA = "tradecat_auto.paper_execution_cost_model.v1"
BINANCE_USDM_PUBLIC_TAKER_FEE_BPS = 4.0
BINANCE_USDM_PUBLIC_MAKER_FEE_BPS = 2.0
DEFAULT_PAPER_SLIPPAGE_BPS = 0.0
BINANCE_USDM_TAKER_FEE_MODEL = "binance_usdm_public_docs_vip0_taker_fallback"


def build_public_taker_cost_model(
    *,
    symbol: str,
    side: str,
    action: str,
    notional_usdt: Any,
    depth: Any,
    fallback_price: Any = None,
    fee_bps: Any = BINANCE_USDM_PUBLIC_TAKER_FEE_BPS,
    fallback_slippage_bps: Any = DEFAULT_PAPER_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Estimate paper execution cost from public Binance USD-M depth.

    This intentionally does not call the signed commission endpoint. The fee
    fallback is the public Binance USD-M documentation example for VIP0 taker
    commission, while the fill price is estimated from public order-book depth
    whenever the supplied bundle contains enough levels.
    """

    context = _cost_model_context(
        symbol=symbol,
        side=side,
        action=action,
        notional_usdt=notional_usdt,
        fee_bps=fee_bps,
        fallback_slippage_bps=fallback_slippage_bps,
    )
    base = _cost_model_base(context)
    if context["notional"] is None:
        return {**base, "error_code": "paper_cost_notional_required"}
    if context["side"] not in {"LONG", "SHORT"}:
        return {**base, "error_code": "paper_cost_side_required"}
    depth_result = _depth_cost_model(base, context, depth)
    if depth_result is not None:
        return depth_result
    return _fallback_cost_model(base, context, fallback_price)


def _cost_model_context(
    *,
    symbol: str,
    side: str,
    action: str,
    notional_usdt: Any,
    fee_bps: Any,
    fallback_slippage_bps: Any,
) -> dict[str, Any]:
    normalized_action = str(action or "OPEN").upper().strip()
    normalized_side = str(side or "").upper().strip()
    buying = (normalized_action == "OPEN" and normalized_side == "LONG") or (
        normalized_action == "CLOSE" and normalized_side == "SHORT"
    )
    return {
        "symbol": str(symbol or "").upper().strip(),
        "side": normalized_side,
        "action": normalized_action,
        "notional": _positive_float(notional_usdt),
        "fee_bps": _non_negative_float(fee_bps, BINANCE_USDM_PUBLIC_TAKER_FEE_BPS),
        "fallback_slippage_bps": _non_negative_float(fallback_slippage_bps, DEFAULT_PAPER_SLIPPAGE_BPS),
        "buying": buying,
        "book_side": "asks" if buying else "bids",
    }


def _cost_model_base(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": PAPER_COST_MODEL_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "error_code": "paper_cost_model_unavailable",
        "symbol": context["symbol"],
        "side": context["side"],
        "action": context["action"],
        "liquidity_role": "taker",
        "book_side": context["book_side"],
        "requested_notional_usdt": context["notional"],
        "fee_bps": context["fee_bps"],
        "maker_fee_bps": BINANCE_USDM_PUBLIC_MAKER_FEE_BPS,
        "taker_fee_bps": BINANCE_USDM_PUBLIC_TAKER_FEE_BPS,
        "fee_model": BINANCE_USDM_TAKER_FEE_MODEL,
        "fee_source": "binance_usdm_user_commission_rate_docs_example_no_signed_lookup",
        "fallback_slippage_bps": context["fallback_slippage_bps"],
        "fill_price_includes_slippage": False,
        "depth_estimated": False,
        "provenance": _cost_model_provenance(),
        "safety": _safety_boundary(),
        "limitations": _cost_model_limitations(),
    }


def _depth_cost_model(base: dict[str, Any], context: dict[str, Any], depth: Any) -> dict[str, Any] | None:
    levels = _levels(depth, context["book_side"])
    best_bid, best_ask = _best_bid_ask(depth)
    mid = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
    if levels and mid and mid > 0:
        fill = _consume_quote_notional(levels, context["notional"])
        if fill is not None:
            return _depth_success_payload(base, context, fill, best_bid=best_bid, best_ask=best_ask, mid=mid)
    return None


def _depth_success_payload(
    base: dict[str, Any],
    context: dict[str, Any],
    fill: tuple[float, float],
    *,
    best_bid: float,
    best_ask: float,
    mid: float,
) -> dict[str, Any]:
    estimated_price, estimated_quantity = fill
    return {
        **base,
        "ok": True,
        "error_code": None,
        "price_source": "binance_usdm_public_order_book_depth",
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        "spread_bps": (best_ask - best_bid) / mid * 10_000,
        "estimated_fill_price": estimated_price,
        "estimated_quantity": estimated_quantity,
        "estimated_notional_usdt": context["notional"],
        "slippage_bps_vs_mid": _slippage_bps_vs_mid(estimated_price, mid, buying=context["buying"]),
        "depth_impact_bps_over_best": _depth_impact_bps(
            estimated_price,
            best_ask if context["buying"] else best_bid,
            mid,
            buying=context["buying"],
        ),
        "fill_price_includes_slippage": True,
        "depth_estimated": True,
    }


def _fallback_cost_model(base: dict[str, Any], context: dict[str, Any], fallback_price: Any) -> dict[str, Any]:
    fallback = _positive_float(fallback_price)
    if fallback is None:
        return {**base, "error_code": "paper_cost_depth_unavailable"}
    fallback_fill = _slipped_price(fallback, buying=context["buying"], slippage_bps=context["fallback_slippage_bps"])
    return {
        **base,
        "ok": True,
        "error_code": "paper_cost_depth_fallback_used",
        "price_source": "fallback_price_with_configured_slippage",
        "estimated_fill_price": fallback_fill,
        "estimated_quantity": context["notional"] / fallback_fill if fallback_fill > 0 else None,
        "estimated_notional_usdt": context["notional"],
        "slippage_bps_vs_mid": context["fallback_slippage_bps"],
        "fill_price_includes_slippage": True,
    }


def _slippage_bps_vs_mid(estimated_price: float, mid: float, *, buying: bool) -> float:
    return (estimated_price - mid) / mid * 10_000 if buying else (mid - estimated_price) / mid * 10_000


def _depth_impact_bps(estimated_price: float, best_price: float | None, mid: float, *, buying: bool) -> float | None:
    if best_price is None:
        return None
    return (estimated_price - best_price) / mid * 10_000 if buying else (best_price - estimated_price) / mid * 10_000


def _cost_model_provenance() -> dict[str, Any]:
    return {
        "source": "binance_usdm_public_order_book_depth",
        "endpoint": "/fapi/v1/depth",
        "commission_reference_endpoint": "/fapi/v1/commissionRate",
        "commission_reference_requires_signed_user_data": True,
    }


def _cost_model_limitations() -> list[str]:
    return [
        "public order-book estimate only; no real order was placed",
        "does not query signed account commission rate",
        "actual account VIP/BNB/symbol discounts can differ and must be supplied by a private executor if needed",
    ]


def _levels(depth: Any, side: str) -> list[tuple[float, float]]:
    if not isinstance(depth, dict):
        return []
    raw_levels = depth.get(side)
    if not isinstance(raw_levels, list):
        return []
    levels: list[tuple[float, float]] = []
    for item in raw_levels:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        price = _positive_float(item[0])
        quantity = _positive_float(item[1])
        if price is not None and quantity is not None:
            levels.append((price, quantity))
    return levels


def _best_bid_ask(depth: Any) -> tuple[float | None, float | None]:
    bids = _levels(depth, "bids")
    asks = _levels(depth, "asks")
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None
    return best_bid, best_ask


def _consume_quote_notional(levels: list[tuple[float, float]], notional: float) -> tuple[float, float] | None:
    remaining = notional
    quantity = 0.0
    filled_notional = 0.0
    for price, available_quantity in levels:
        level_notional = price * available_quantity
        take_notional = min(remaining, level_notional)
        if take_notional <= 0:
            continue
        quantity += take_notional / price
        filled_notional += take_notional
        remaining -= take_notional
        if remaining <= 1e-9:
            break
    if remaining > 1e-6 or quantity <= 0:
        return None
    return filled_notional / quantity, quantity


def _slipped_price(price: float, *, buying: bool, slippage_bps: float) -> float:
    slip = max(0.0, float(slippage_bps or 0.0)) / 10_000
    return price * (1 + slip if buying else 1 - slip)


def _positive_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _non_negative_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _safety_boundary() -> dict[str, bool]:
    return paper_watch_safety_boundary()
