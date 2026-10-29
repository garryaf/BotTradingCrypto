#!/usr/bin/env python3
"""Plain-assert self-check for [PH5-T2] 30-Day Calendar Soak Test Runner.
Run: python scripts/test_soak_runner.py
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.soak_test_runner import (
    MAX_DRAWDOWN_LIMIT_PCT,
    MemoryLeakDetector,
    SoakTelemetrySample,
    SoakTestSupervisor,
)


def test_memory_leak_detector_flat_profile():
    detector = MemoryLeakDetector(window_size=10)
    # 10 samples of constant 100 MB at 1-second intervals
    for i in range(10):
        detector.add_sample(time_sec=float(i), ram_bytes=100 * 1024 * 1024)
    slope = detector.calculate_slope_mb_per_hour()
    assert abs(slope) < 0.01, f"Expected ~0 slope for constant RAM, got {slope}"


def test_memory_leak_detector_leaking_profile():
    detector = MemoryLeakDetector(window_size=10)
    # Leaking: grows by 1 MB every 10 seconds -> 0.1 MB/sec = 360 MB/hour
    for i in range(10):
        detector.add_sample(time_sec=float(i * 10), ram_bytes=int((100 + i) * 1024 * 1024))
    slope = detector.calculate_slope_mb_per_hour()
    assert abs(slope - 360.0) < 1.0, f"Expected ~360 MB/h slope, got {slope}"


def test_supervisor_telemetry_and_crash_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "telemetry.jsonl"
        supervisor = SoakTestSupervisor(log_path=log_file)

        # 1. Normal sample
        sample1 = supervisor.sample_telemetry()
        assert sample1.health_status in ("ok", "unknown")
        assert supervisor.cumulative_crashes == 0
        assert log_file.exists()

        # 2. Inject simulated health with crashed background task
        supervisor.fetch_health_payload = lambda: {
            "status": "degraded",
            "db": "connected",
            "tasks": {
                "binance_ingestion": "running",
                "risk_engine": "crashed",
                "aggregator": "running",
            },
            "current_drawdown_pct": 2.5,
        }

        sample2 = supervisor.sample_telemetry()
        assert "risk_engine" in sample2.crashed_tasks
        assert supervisor.cumulative_crashes == 1
        assert any("crash" in w.lower() for w in sample2.warnings)

        # 3. Inject simulated excessive drawdown >= 8.0%
        supervisor.fetch_health_payload = lambda: {
            "status": "ok",
            "db": "connected",
            "tasks": {"risk_engine": "running"},
            "current_drawdown_pct": 8.5,
        }

        sample3 = supervisor.sample_telemetry()
        assert supervisor.max_observed_drawdown == 8.5
        assert any("drawdown" in w.lower() for w in sample3.warnings)

        # Evaluation should fail due to crash and drawdown
        eval_result = supervisor.evaluate_safety_gate()
        assert eval_result["status"] == "FAILED"
        assert eval_result["zero_crash_passed"] is False
        assert eval_result["drawdown_passed"] is False


def test_supervisor_30_day_progress_evaluation():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "telemetry.jsonl"
        supervisor = SoakTestSupervisor(log_path=log_file)

        # Clean state, zero crash, zero drawdown breach
        supervisor.fetch_health_payload = lambda: {
            "status": "ok",
            "db": "connected",
            "tasks": {"risk_engine": "running"},
            "current_drawdown_pct": 1.2,
        }
        supervisor.sample_telemetry()

        # In-progress at start
        res = supervisor.evaluate_safety_gate()
        assert res["status"] == "IN_PROGRESS"
        assert res["criteria_summary"]["kriteria_1_30d_continuous"] == "PENDING"
        assert res["criteria_summary"]["kriteria_2_zero_crash"] == "PASS"
        assert res["criteria_summary"]["kriteria_2_drawdown_under_8pct"] == "PASS"

        # Simulate 30 days elapsed
        supervisor.start_time = supervisor.start_time - (30 * 86400 + 10)
        supervisor.sample_telemetry()
        res_30d = supervisor.evaluate_safety_gate()
        assert res_30d["status"] == "PASSED"
        assert res_30d["criteria_summary"]["kriteria_1_30d_continuous"] == "PASS"


if __name__ == "__main__":
    test_memory_leak_detector_flat_profile()
    test_memory_leak_detector_leaking_profile()
    test_supervisor_telemetry_and_crash_detection()
    test_supervisor_30_day_progress_evaluation()
    print("ok")
