from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tradecat_auto.agent_trade_thesis import paper_intent_from_agent_trade_thesis
from tradecat_auto.market_enrichment import build_market_enrichment
from tradecat_auto.paper_autonomy import synthesize_agent_trade_thesis
from tradecat_auto.paper_broker import open_paper_position
from tradecat_auto.paper_costs import build_public_taker_cost_model
from tradecat_auto.risk import default_risk_policy, evaluate_risk
from tradecat_auto.safety_boundary import paper_watch_report_flags, paper_watch_safety_boundary
from tradecat_auto.signals import build_signal_score
from tradecat_auto.strategies import build_strategy_intent


def build_paper_pipeline_report(
    *,
    selected_symbol: str,
    anomaly_symbols: dict[str, Any],
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    mode: str = "paper",
    requested_notional_usdt: float | None = None,
    requested_margin_usdt: float | None = None,
    paper_leverage: float | None = None,
    margin_budget_usdt: float | None = None,
    sizing_source: str = "agent_supplied_or_explicit",
    agent_trade_thesis: dict[str, Any] | None = None,
    paper_autonomy_profile: dict[str, Any] | None = None,
    risk_policy: dict[str, Any] | None = None,
    paper_fee_bps: float | None = None,
    paper_slippage_bps: float | None = None,
) -> dict[str, Any]:
    selected = str(selected_symbol or "").upper().strip()
    anomaly_item = _selected_anomaly_item(anomaly_symbols, events, selected)
    if not anomaly_item:
        return _selected_symbol_not_found_report(selected, events, market_bundle, mode)
    return _paper_pipeline_report_for_anomaly(
        selected=selected,
        anomaly_item=anomaly_item,
        market_bundle=market_bundle,
        events=events,
        mode=mode,
        sizing_inputs={
            "requested_notional_usdt": requested_notional_usdt,
            "requested_margin_usdt": requested_margin_usdt,
            "paper_leverage": paper_leverage,
            "margin_budget_usdt": margin_budget_usdt,
            "sizing_source": sizing_source,
        },
        agent_trade_thesis=agent_trade_thesis,
        paper_autonomy_profile=paper_autonomy_profile,
        risk_policy=risk_policy,
        paper_fee_bps=paper_fee_bps,
        paper_slippage_bps=paper_slippage_bps,
    )


def _paper_pipeline_report_for_anomaly(
    *,
    selected: str,
    anomaly_item: dict[str, Any],
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    mode: str,
    sizing_inputs: dict[str, Any],
    agent_trade_thesis: dict[str, Any] | None,
    paper_autonomy_profile: dict[str, Any] | None,
    risk_policy: dict[str, Any] | None,
    paper_fee_bps: float | None,
    paper_slippage_bps: float | None,
) -> dict[str, Any]:
    context = _paper_pipeline_context(
        selected=selected,
        anomaly_item=anomaly_item,
        market_bundle=market_bundle,
        events=events,
        mode=mode,
        sizing_inputs=sizing_inputs,
        agent_trade_thesis=agent_trade_thesis,
        paper_autonomy_profile=paper_autonomy_profile,
        risk_policy=risk_policy,
        paper_fee_bps=paper_fee_bps,
        paper_slippage_bps=paper_slippage_bps,
    )
    return _pipeline_report_payload(selected, mode, market_bundle, events, context)


def _paper_pipeline_context(
    *,
    selected: str,
    anomaly_item: dict[str, Any],
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    mode: str,
    sizing_inputs: dict[str, Any],
    agent_trade_thesis: dict[str, Any] | None,
    paper_autonomy_profile: dict[str, Any] | None,
    risk_policy: dict[str, Any] | None,
    paper_fee_bps: float | None,
    paper_slippage_bps: float | None,
) -> dict[str, Any]:
    analysis = _pipeline_analysis_context(
        anomaly_item,
        market_bundle,
        events,
        agent_trade_thesis=agent_trade_thesis,
        paper_autonomy_profile=paper_autonomy_profile,
    )
    decision = _pipeline_decision_context(
        mode=mode,
        risk_policy=risk_policy,
        market_bundle=market_bundle,
        analysis=analysis,
        sizing_inputs=sizing_inputs,
    )
    execution = _pipeline_execution_context(
        selected_symbol=selected,
        mode=mode,
        analysis=analysis,
        market_bundle=market_bundle,
        sizing=decision["sizing"],
        risk_decision=decision["risk_decision"],
        paper_fee_bps=paper_fee_bps,
        paper_slippage_bps=paper_slippage_bps,
    )
    return _pipeline_context_payload(mode, analysis, decision, execution)


def _pipeline_decision_context(
    *,
    mode: str,
    risk_policy: dict[str, Any] | None,
    market_bundle: dict[str, Any],
    analysis: dict[str, Any],
    sizing_inputs: dict[str, Any],
) -> dict[str, Any]:
    active_risk_policy = _pipeline_risk_policy(
        mode, risk_policy, market_bundle, strategy_intent=analysis["strategy_intent"]
    )
    sizing = _pipeline_sizing(
        requested_notional_usdt=sizing_inputs["requested_notional_usdt"],
        requested_margin_usdt=sizing_inputs["requested_margin_usdt"],
        paper_leverage=sizing_inputs["paper_leverage"],
        margin_budget_usdt=sizing_inputs["margin_budget_usdt"],
        sizing_source=sizing_inputs["sizing_source"],
        agent_trade_thesis=analysis["agent_trade_thesis"],
        mode=mode,
    )
    active_risk_policy.update(_risk_sizing_update(mode, sizing))
    return {"sizing": sizing, "risk_decision": evaluate_risk(analysis["decision_signal"], active_risk_policy)}


def _pipeline_execution_context(
    *,
    selected_symbol: str,
    mode: str,
    analysis: dict[str, Any],
    market_bundle: dict[str, Any],
    sizing: dict[str, Any],
    risk_decision: dict[str, Any],
    paper_fee_bps: float | None,
    paper_slippage_bps: float | None,
) -> dict[str, Any]:
    paper_execution_cost, paper_execution = _pipeline_paper_execution(
        selected_symbol=selected_symbol,
        decision_signal=analysis["decision_signal"],
        risk_decision=risk_decision,
        enrichment=analysis["enrichment"],
        strategy_intent=analysis["strategy_intent"],
        agent_trade_thesis=analysis["agent_trade_thesis"],
        market_bundle=market_bundle,
        sizing=sizing,
        fee_bps=paper_fee_bps,
        slippage_bps=paper_slippage_bps,
    )
    research_cycle_run_id = _research_cycle_run_id(analysis["agent_trade_thesis"])
    if research_cycle_run_id:
        paper_execution["research_cycle_run_id"] = research_cycle_run_id
    return {"paper_execution_cost": paper_execution_cost, "paper_execution": paper_execution}


def _pipeline_context_payload(
    mode: str,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    sizing = decision["sizing"]
    risk_decision = decision["risk_decision"]
    paper_execution = execution["paper_execution"]
    report_ok = _pipeline_report_ok(mode, analysis, risk_decision, paper_execution)
    error = _pipeline_error(mode, report_ok, sizing, risk_decision, paper_execution)
    return {
        "analysis": analysis,
        "sizing": sizing,
        "risk_decision": risk_decision,
        "paper_execution_cost": execution["paper_execution_cost"],
        "paper_execution": paper_execution,
        "report_ok": report_ok,
        "error": error,
        "research_cycle_run_id": _research_cycle_run_id(analysis["agent_trade_thesis"]),
    }


def _selected_anomaly_item(
    anomaly_symbols: dict[str, Any], events: dict[str, Any], selected: str
) -> dict[str, Any] | None:
    anomaly_item = _find_anomaly_symbol(anomaly_symbols, selected)
    if anomaly_item:
        return _merge_anomaly_item_with_latest_event(anomaly_item, events, selected)
    return _anomaly_item_from_latest_event(events, selected)


def _selected_symbol_not_found_report(
    selected: str, events: dict[str, Any], market_bundle: dict[str, Any], mode: str
) -> dict[str, Any]:
    return {
        "schema": "tradecat_auto.run_once_report.v1",
        "schema_version": "1.0.0",
        "ok": False,
        **paper_watch_report_flags(),
        "mode": mode,
        "selected_symbol": selected,
        "error_code": "selected_symbol_not_found_in_anomaly_symbols",
        "error": "selected_symbol_not_found_in_anomaly_symbols",
        "events_count": len(events.get("events") or []) if isinstance(events, dict) else 0,
        "provenance": _report_provenance(selected, market_bundle),
        "safety": _safety_boundary(),
    }


def _pipeline_analysis_context(
    anomaly_item: dict[str, Any],
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    *,
    agent_trade_thesis: dict[str, Any] | None,
    paper_autonomy_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    enrichment = build_market_enrichment(anomaly_item, market_bundle)
    signal = build_signal_score(enrichment)
    resolved_agent_trade_thesis = synthesize_agent_trade_thesis(
        agent_trade_thesis=agent_trade_thesis,
        paper_autonomy_profile=paper_autonomy_profile,
        signal=signal,
        enrichment=enrichment,
        events=events,
    )
    decision_signal = _apply_agent_signal_override(signal, resolved_agent_trade_thesis)
    return {
        "enrichment": enrichment,
        "signal": signal,
        "agent_trade_thesis": resolved_agent_trade_thesis,
        "decision_signal": decision_signal,
        "strategy_intent": build_strategy_intent(
            decision_signal, enrichment, agent_trade_thesis=resolved_agent_trade_thesis
        ),
    }


def _pipeline_risk_policy(
    mode: str, risk_policy: dict[str, Any] | None, market_bundle: dict[str, Any], *, strategy_intent: dict[str, Any]
) -> dict[str, Any]:
    active_risk_policy = default_risk_policy(mode=mode)
    if risk_policy:
        active_risk_policy.update(risk_policy)
    if active_risk_policy.get("current_abnormal_move_bps") is None:
        move_bps = _market_move_bps(market_bundle)
        if move_bps is not None:
            active_risk_policy["current_abnormal_move_bps"] = move_bps
    if mode == "paper" and _agent_exit_plan_missing(strategy_intent):
        force_reject_reasons = list(active_risk_policy.get("force_reject_reasons") or [])
        force_reject_reasons.append("agent_exit_plan_required")
        active_risk_policy["force_reject_reasons"] = force_reject_reasons
    return active_risk_policy


def _pipeline_sizing(
    *,
    requested_notional_usdt: float | None,
    requested_margin_usdt: float | None,
    paper_leverage: float | None,
    margin_budget_usdt: float | None,
    sizing_source: str,
    agent_trade_thesis: dict[str, Any] | None,
    mode: str,
) -> dict[str, Any]:
    resolved = _resolved_sizing_inputs(
        requested_notional_usdt=requested_notional_usdt,
        requested_margin_usdt=requested_margin_usdt,
        paper_leverage=paper_leverage,
        sizing_source=sizing_source,
        agent_trade_thesis=agent_trade_thesis,
    )
    return resolve_paper_sizing(
        requested_notional_usdt=resolved["requested_notional_usdt"],
        requested_margin_usdt=resolved["requested_margin_usdt"],
        paper_leverage=resolved["paper_leverage"],
        margin_budget_usdt=margin_budget_usdt,
        sizing_source=resolved["sizing_source"],
        sizing_required=(mode == "paper"),
    )


def _resolved_sizing_inputs(
    *,
    requested_notional_usdt: float | None,
    requested_margin_usdt: float | None,
    paper_leverage: float | None,
    sizing_source: str,
    agent_trade_thesis: dict[str, Any] | None,
) -> dict[str, Any]:
    thesis_sizing = _paper_sizing_from_agent_trade_thesis(agent_trade_thesis)
    if any(value is not None for value in (requested_notional_usdt, requested_margin_usdt, paper_leverage)):
        return {
            "requested_notional_usdt": requested_notional_usdt,
            "requested_margin_usdt": requested_margin_usdt,
            "paper_leverage": paper_leverage,
            "sizing_source": sizing_source,
        }
    if thesis_sizing:
        return {
            "requested_notional_usdt": thesis_sizing.get("requested_notional_usdt"),
            "requested_margin_usdt": thesis_sizing.get("requested_margin_usdt"),
            "paper_leverage": thesis_sizing.get("paper_leverage"),
            "sizing_source": "agent_trade_thesis.paper_intent",
        }
    return {
        "requested_notional_usdt": requested_notional_usdt,
        "requested_margin_usdt": requested_margin_usdt,
        "paper_leverage": paper_leverage,
        "sizing_source": sizing_source,
    }


def _risk_sizing_update(mode: str, sizing: dict[str, Any]) -> dict[str, Any]:
    update = {
        "mode": mode,
        "sizing_required": sizing["sizing_required"],
        "sizing_source": sizing["source"],
        "paper_leverage": sizing["paper_leverage"],
        "requested_margin_usdt": sizing["requested_margin_usdt"],
        "requested_notional_usdt": sizing["effective_notional_usdt"],
    }
    if sizing["margin_budget_usdt"] is not None:
        update["paper_margin_budget_usdt"] = sizing["margin_budget_usdt"]
    return update


def _pipeline_paper_execution(
    *,
    selected_symbol: str,
    decision_signal: dict[str, Any],
    risk_decision: dict[str, Any],
    enrichment: dict[str, Any],
    strategy_intent: dict[str, Any],
    agent_trade_thesis: dict[str, Any] | None,
    market_bundle: dict[str, Any],
    sizing: dict[str, Any],
    fee_bps: float | None,
    slippage_bps: float | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paper_execution_cost = _paper_execution_cost_model(
        selected_symbol=selected_symbol,
        decision_signal=decision_signal,
        market_bundle=market_bundle,
        notional_usdt=sizing["effective_notional_usdt"],
        fee_bps=fee_bps,
        fallback_slippage_bps=slippage_bps,
    )
    return paper_execution_cost, open_paper_position(
        decision_signal,
        risk_decision,
        enrichment,
        requested_notional_usdt=sizing["effective_notional_usdt"],
        requested_margin_usdt=sizing["requested_margin_usdt"],
        paper_leverage=sizing["paper_leverage"],
        sizing_source=sizing["source"],
        strategy_intent=strategy_intent,
        allow_multiple_open_positions_per_symbol=_allow_multiple_open_positions_per_symbol(agent_trade_thesis),
        max_concurrent_positions_per_symbol=_max_concurrent_positions_per_symbol(agent_trade_thesis),
        execution_cost_model=paper_execution_cost,
    )


def _pipeline_report_ok(
    mode: str, analysis: dict[str, Any], risk_decision: dict[str, Any], paper_execution: dict[str, Any]
) -> bool:
    paper_ok = bool(paper_execution.get("ok") and paper_execution.get("status") == "OPENED")
    return bool(
        analysis["enrichment"].get("ok")
        and analysis["signal"].get("ok")
        and risk_decision.get("ok")
        and (mode != "paper" or (risk_decision.get("decision") == "ALLOW" and paper_ok))
    )


def _pipeline_error(
    mode: str,
    report_ok: bool,
    sizing: dict[str, Any],
    risk_decision: dict[str, Any],
    paper_execution: dict[str, Any],
) -> dict[str, Any] | None:
    if mode == "paper" and not report_ok:
        sizing_error = sizing.get("error_code")
        execution_reasons = paper_execution.get("reasons") if isinstance(paper_execution.get("reasons"), list) else []
        risk_reasons = risk_decision.get("reasons") if isinstance(risk_decision.get("reasons"), list) else []
        error_code = str(
            sizing_error
            or (risk_reasons[0] if risk_reasons else None)
            or (execution_reasons[0] if execution_reasons else None)
            or "paper_pipeline_rejected"
        )
        return {
            "code": error_code,
            "kind": "risk_reject" if risk_decision.get("decision") != "ALLOW" else "paper_execution_reject",
            "message": "paper pipeline did not open a position",
            "retryable": error_code in {"agent_sizing_required", "agent_exit_plan_required"},
        }
    return None


def _pipeline_report_payload(
    selected: str,
    mode: str,
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    analysis = context["analysis"]
    sizing = context["sizing"]
    return _pipeline_report_base(selected, mode, market_bundle, events, context) | {
        "agent_trade_thesis": _agent_trade_thesis_summary(analysis["agent_trade_thesis"]),
        "paper_sizing": sizing,
        "paper_execution_cost": context["paper_execution_cost"],
        "paper_margin_budget_usdt": sizing["margin_budget_usdt"],
        "requested_margin_usdt": sizing["requested_margin_usdt"],
        "paper_leverage": sizing["paper_leverage"],
        "effective_notional_usdt": sizing["effective_notional_usdt"],
        "events_count": len(events.get("events") or []) if isinstance(events, dict) else 0,
        "latest_event": (events.get("events") or [None])[0] if isinstance(events, dict) else None,
        "enrichment": analysis["enrichment"],
        "signal": analysis["decision_signal"],
        "strategy_intent": analysis["strategy_intent"],
        "risk_decision": context["risk_decision"],
        "paper_execution": context["paper_execution"],
        "limitations": _pipeline_limitations(),
    }


def _pipeline_report_base(
    selected: str,
    mode: str,
    market_bundle: dict[str, Any],
    events: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    error = context["error"]
    return {
        "schema": "tradecat_auto.run_once_report.v1",
        "schema_version": "1.0.0",
        "ok": context["report_ok"],
        **paper_watch_report_flags(),
        "mode": mode,
        "generated_at": _now_iso(),
        "selected_symbol": selected,
        "error_code": error["code"] if isinstance(error, dict) else None,
        "error": error,
        "provenance": _report_provenance(selected, market_bundle),
        "research_cycle_run_id": context["research_cycle_run_id"],
        "safety": _safety_boundary(),
    }


def _pipeline_limitations() -> list[str]:
    return [
        "paper run only; no Binance credentials were read",
        "no real order was placed",
        "paper size/leverage must be Agent-supplied or explicitly provided; TradeCat has no default trade amount",
    ]


def resolve_paper_sizing(
    *,
    requested_notional_usdt: Any = None,
    requested_margin_usdt: Any = None,
    paper_leverage: Any = None,
    margin_budget_usdt: Any = None,
    sizing_source: str = "agent_supplied_or_explicit",
    sizing_required: bool = True,
) -> dict[str, Any]:
    """Resolve paper sizing without inventing a default order amount or cap."""

    numbers = _paper_sizing_numbers(
        requested_notional_usdt=requested_notional_usdt,
        requested_margin_usdt=requested_margin_usdt,
        paper_leverage=paper_leverage,
        margin_budget_usdt=margin_budget_usdt,
    )
    effective = _effective_paper_notional(numbers["requested_notional"], numbers["margin"], numbers["leverage"])
    leverage = numbers["leverage"]
    effective_notional = effective["effective_notional"]
    complete = effective_notional is not None and effective_notional > 0 and leverage is not None and leverage > 0
    return _paper_sizing_payload(
        numbers=numbers,
        effective=effective,
        complete=complete,
        sizing_required=sizing_required,
        sizing_source=sizing_source,
    )


def _paper_sizing_payload(
    *,
    numbers: dict[str, float | None],
    effective: dict[str, Any],
    complete: bool,
    sizing_required: bool,
    sizing_source: str,
) -> dict[str, Any]:
    margin = effective["margin"]
    budget_exceeded = _paper_margin_budget_exceeded(numbers["margin_budget"], margin)
    return {
        "schema": "tradecat_auto.paper_sizing_decision.v1",
        "schema_version": "1.0.0",
        "ok": bool(complete),
        "source": str(sizing_source or "agent_supplied_or_explicit"),
        "agent_decided": str(sizing_source or "").startswith("agent"),
        "sizing_required": bool(sizing_required),
        "mode": effective["mode"],
        "margin_budget_usdt": numbers["margin_budget"],
        "requested_margin_usdt": margin,
        "paper_leverage": numbers["leverage"],
        "requested_notional_usdt": numbers["requested_notional"],
        "effective_notional_usdt": effective["effective_notional"],
        "budget_exceeded": budget_exceeded,
        "notional_semantics": "effective_notional_usdt; margin_budget_usdt is not an order amount",
        "error_code": None if complete or not sizing_required else "agent_sizing_required",
        "provenance": {
            "source": "tradecat_auto.pipeline.paper_sizing_decision",
            "sizing_source": str(sizing_source or "agent_supplied_or_explicit"),
        },
        "safety": _safety_boundary(),
    }


def _paper_sizing_numbers(
    *,
    requested_notional_usdt: Any,
    requested_margin_usdt: Any,
    paper_leverage: Any,
    margin_budget_usdt: Any,
) -> dict[str, float | None]:
    return {
        "leverage": _positive_float(paper_leverage),
        "margin_budget": _positive_float(margin_budget_usdt),
        "margin": _positive_float(requested_margin_usdt),
        "requested_notional": _positive_float(requested_notional_usdt),
    }


def _effective_paper_notional(
    requested_notional: float | None, margin: float | None, leverage: float | None
) -> dict[str, Any]:
    if margin is not None and leverage is not None:
        return {
            "effective_notional": margin * leverage,
            "margin": margin,
            "mode": "margin_times_leverage",
        }
    if requested_notional is not None and leverage is not None:
        return {
            "effective_notional": requested_notional,
            "margin": requested_notional / leverage,
            "mode": "explicit_effective_notional",
        }
    return {"effective_notional": None, "margin": margin, "mode": "missing"}


def _paper_margin_budget_exceeded(margin_budget: float | None, margin: float | None) -> bool:
    return bool(margin_budget is not None and margin_budget > 0 and margin is not None and margin > margin_budget)


def _paper_sizing_from_agent_trade_thesis(agent_trade_thesis: dict[str, Any] | None) -> dict[str, Any]:
    paper_intent = paper_intent_from_agent_trade_thesis(agent_trade_thesis)
    if not paper_intent:
        return {}
    leverage = paper_intent.get("paper_leverage")
    if leverage is None:
        leverage = paper_intent.get("requested_leverage")
    if leverage is None:
        leverage = paper_intent.get("leverage")
    return {
        "requested_margin_usdt": paper_intent.get("requested_margin_usdt"),
        "paper_leverage": leverage,
        "requested_notional_usdt": paper_intent.get("requested_notional_usdt"),
    }


def _paper_execution_cost_model(
    *,
    selected_symbol: str,
    decision_signal: dict[str, Any],
    market_bundle: dict[str, Any],
    notional_usdt: Any,
    fee_bps: Any = None,
    fallback_slippage_bps: Any = None,
) -> dict[str, Any]:
    return build_public_taker_cost_model(
        symbol=selected_symbol,
        side=str(decision_signal.get("direction") or ""),
        action="OPEN",
        notional_usdt=notional_usdt,
        depth=market_bundle.get("depth"),
        fallback_price=_last_price_from_market_bundle(market_bundle),
        fee_bps=fee_bps,
        fallback_slippage_bps=fallback_slippage_bps,
    )


def _last_price_from_market_bundle(market_bundle: dict[str, Any]) -> float | None:
    ticker = market_bundle.get("ticker24hr") if isinstance(market_bundle.get("ticker24hr"), dict) else {}
    return _positive_or_negative_float(ticker.get("lastPrice"))


def _anomaly_item_from_latest_event(events: dict[str, Any], selected_symbol: str) -> dict[str, Any] | None:
    event = _latest_event(events)
    if not event:
        return None
    symbol = str(event.get("symbol") or "").upper().strip()
    selected = str(selected_symbol or "").upper().strip()
    if selected and symbol and symbol != selected:
        return None
    source_values = _event_source_values(event)
    if not source_values:
        return None
    raw_symbol = str(event.get("raw_symbol") or source_values.get("交易对") or selected or symbol).upper().strip()
    return {
        "raw_symbol": raw_symbol,
        "normalized_symbol": selected or symbol,
        "first_row_index": event.get("row_index"),
        "source_dataset_key": str(event.get("source_dataset_key") or "signal_flow"),
        "source_values": source_values,
    }


def _merge_anomaly_item_with_latest_event(
    anomaly_item: dict[str, Any],
    events: dict[str, Any],
    selected_symbol: str,
) -> dict[str, Any]:
    event_item = _anomaly_item_from_latest_event(events, selected_symbol)
    if not event_item:
        return anomaly_item
    event_values = event_item.get("source_values") if isinstance(event_item.get("source_values"), dict) else {}
    anomaly_values = anomaly_item.get("source_values") if isinstance(anomaly_item.get("source_values"), dict) else {}
    merged = dict(anomaly_item)
    merged["source_dataset_key"] = str(
        event_item.get("source_dataset_key") or anomaly_item.get("source_dataset_key") or ""
    )
    merged["source_values"] = {**event_values, **anomaly_values}
    merged["related_signal_flow_values"] = event_values
    return merged


def _event_source_values(event: dict[str, Any]) -> dict[str, Any]:
    values = event.get("source_values") if isinstance(event.get("source_values"), dict) else {}
    related = event.get("related_anomaly_panel") if isinstance(event.get("related_anomaly_panel"), dict) else {}
    related_values = related.get("source_values") if isinstance(related.get("source_values"), dict) else {}
    return {**values, **related_values}


def _latest_event(events: dict[str, Any]) -> dict[str, Any] | None:
    rows = events.get("events") if isinstance(events, dict) else []
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return rows[0]
    return None


def _apply_agent_signal_override(signal: dict[str, Any], agent_trade_thesis: dict[str, Any] | None) -> dict[str, Any]:
    paper_intent = paper_intent_from_agent_trade_thesis(agent_trade_thesis)
    if paper_intent.get("allow_agent_direction_override") is not True:
        return signal
    thesis = agent_trade_thesis if isinstance(agent_trade_thesis, dict) else {}
    direction = (
        str(thesis.get("direction") or paper_intent.get("paper_direction") or paper_intent.get("direction") or "")
        .upper()
        .strip()
    )
    if direction not in {"LONG", "SHORT"}:
        return signal
    reasons = [str(item) for item in signal.get("do_not_trade_reasons") or [] if str(item)]
    removable_reasons = {"direction_conflict"}
    if paper_intent.get("allow_signal_reject_override") is True:
        removable_reasons.update({"low_score", "spread_too_wide"})
    remaining_reasons = [item for item in reasons if item not in removable_reasons]
    if remaining_reasons:
        return signal
    updated = dict(signal)
    updated["direction"] = direction
    updated["do_not_trade_reasons"] = remaining_reasons
    updated["tradable_candidate"] = True
    positives = list(signal.get("positive_factors") or [])
    positives.append("agent_direction_override")
    updated["positive_factors"] = _dedupe([str(item) for item in positives])
    updated["agent_direction_override"] = {
        "schema": "tradecat_auto.agent_signal_override.v1",
        "schema_version": "1.0.0",
        "ok": True,
        "source": "agent_trade_thesis.paper_intent",
        "reason": "direction_conflict overridden by explicit Agent paper-only authorization",
        **paper_watch_report_flags(),
        "safety": _safety_boundary(),
    }
    return updated


def _market_move_bps(market_bundle: dict[str, Any]) -> float | None:
    ticker = market_bundle.get("ticker24hr") if isinstance(market_bundle.get("ticker24hr"), dict) else {}
    value = _positive_or_negative_float(ticker.get("priceChangePercent"))
    if value is None:
        return None
    return abs(value) * 100.0


def _allow_multiple_open_positions_per_symbol(agent_trade_thesis: dict[str, Any] | None) -> bool:
    paper_intent = paper_intent_from_agent_trade_thesis(agent_trade_thesis)
    max_concurrent = _positive_float(paper_intent.get("max_concurrent_positions_per_symbol"))
    return bool(
        paper_intent.get("allow_multiple_open_positions_per_symbol") is True
        or (max_concurrent is not None and max_concurrent > 1)
    )


def _max_concurrent_positions_per_symbol(agent_trade_thesis: dict[str, Any] | None) -> int | None:
    paper_intent = paper_intent_from_agent_trade_thesis(agent_trade_thesis)
    try:
        if paper_intent.get("max_concurrent_positions_per_symbol") in (None, ""):
            return None
        value = int(paper_intent["max_concurrent_positions_per_symbol"])
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _agent_exit_plan_missing(strategy_intent: dict[str, Any]) -> bool:
    return str(strategy_intent.get("exit_plan_source") or "") == "agent_required_missing"


def _research_cycle_run_id(agent_trade_thesis: dict[str, Any] | None) -> str:
    thesis = agent_trade_thesis if isinstance(agent_trade_thesis, dict) else {}
    provenance = thesis.get("provenance") if isinstance(thesis.get("provenance"), dict) else {}
    for source in (provenance, thesis):
        for key in ("research_cycle_run_id", "run_id"):
            value = str(source.get(key) or "").strip()
            if value:
                return value
    return ""


def _agent_trade_thesis_summary(agent_trade_thesis: dict[str, Any] | None) -> dict[str, Any]:
    thesis = agent_trade_thesis if isinstance(agent_trade_thesis, dict) else {}
    provenance = thesis.get("provenance") if isinstance(thesis.get("provenance"), dict) else {}
    safety = thesis.get("safety") if isinstance(thesis.get("safety"), dict) else _safety_boundary()
    return {
        "schema": str(thesis.get("schema") or ""),
        "schema_version": str(thesis.get("schema_version") or ""),
        "ok": thesis.get("ok"),
        "symbol": str(thesis.get("symbol") or ""),
        "direction": str(thesis.get("direction") or ""),
        "mode": str(thesis.get("mode") or ""),
        "confidence": thesis.get("confidence"),
        "holding_horizon": str(thesis.get("holding_horizon") or ""),
        "rationale": str(thesis.get("rationale") or ""),
        "risk_notes": [str(item) for item in thesis.get("risk_notes") or []],
        "limitations": [str(item) for item in thesis.get("limitations") or []],
        "exit_rationale": str(thesis.get("exit_rationale") or ""),
        "paper_intent_present": isinstance(thesis.get("paper_intent"), dict),
        "exit_plan_present": any(
            thesis.get(key) not in (None, "")
            for key in ("invalidation_price", "take_profit_price", "max_holding_minutes")
        ),
        "paper_autonomy_profile": bool(provenance.get("paper_autonomy_profile")),
        "provenance": provenance,
        "safety": safety,
    }


def _find_anomaly_symbol(anomaly_symbols: dict[str, Any], selected_symbol: str) -> dict[str, Any] | None:
    symbols = anomaly_symbols.get("symbols") if isinstance(anomaly_symbols, dict) else []
    if not isinstance(symbols, list):
        return None
    for item in symbols:
        if not isinstance(item, dict):
            continue
        if str(item.get("normalized_symbol") or "").upper().strip() == selected_symbol:
            return item
    return None


def _positive_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


def _positive_or_negative_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _report_provenance(selected_symbol: str, market_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "tradecat_auto.pipeline.build_paper_pipeline_report",
        "selected_symbol": selected_symbol,
        "market_bundle_schema": str(market_bundle.get("schema") or ""),
        "market_bundle_source": str(market_bundle.get("source") or "binance_public_market_bundle"),
    }


def _safety_boundary() -> dict[str, bool]:
    return paper_watch_safety_boundary()
