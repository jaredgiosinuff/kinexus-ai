#!/usr/bin/env python3
"""Tests for MetricsService snapshot helpers."""

from datetime import datetime, timedelta

import pytest

from src.core.services.metrics_service import MetricsService


@pytest.mark.asyncio
async def test_metrics_service_window_calculations():
    service = MetricsService()

    # Record sample activity
    await service.record_request("GET", "/health", 200, 0.1)
    await service.record_error("api", "server_error")
    await service.record_agent_performance(
        agent_id="agent-1",
        agent_type="supervisor",
        reasoning_time=0.5,
        confidence_score=0.9,
        thoughts_count=3,
        models_used=1,
        success=True,
        reasoning_pattern="chain_of_thought"
    )
    await service.record_model_usage(
        agent_type="supervisor",
        model_provider="bedrock",
        model_type="claude",
        input_tokens=100,
        output_tokens=50,
        cost=0.02
    )

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=30)

    active_agents = await service.get_active_agent_count(start_time, end_time)
    active_reasoning = await service.get_active_reasoning_chains(start_time, end_time)
    request_rate = await service.get_request_rate(start_time, end_time)
    error_rate = await service.get_error_rate(start_time, end_time)
    avg_response = await service.get_avg_response_time(start_time, end_time)
    total_cost = await service.get_total_cost(start_time, end_time)
    tokens_processed = await service.get_tokens_processed(start_time, end_time)

    assert active_agents == 1
    assert active_reasoning == 3
    assert request_rate > 0
    assert error_rate == pytest.approx(1.0)
    assert avg_response == pytest.approx(0.1)
    assert total_cost == pytest.approx(0.02)
    assert tokens_processed == 150
