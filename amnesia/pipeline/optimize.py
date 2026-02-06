from __future__ import annotations


def optimize_skill(skill: dict) -> dict:
    optimized = dict(skill)
    metrics = dict(optimized.get("metrics", {}))
    metrics["optimized"] = True
    optimized["metrics"] = metrics
    return optimized
