"""Lightweight platform performance runner based on requests."""

from app.modules.performance_automation.runtime import execute_performance_case


def run_performance_case(case: dict) -> dict:
    """Run one configured performance scenario and return a report."""
    return execute_performance_case(case)
