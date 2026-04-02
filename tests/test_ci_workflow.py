"""Tests for the GitHub Actions PR syntax-check workflow.

These tests verify that the workflow YAML exists and is structurally correct
before the implementation file is created (TDD RED phase).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "pr-syntax-check.yml"


def _load_workflow() -> dict:
    """Load and parse the workflow YAML file.

    YAML parses the bare key ``on`` as the Python boolean ``True``.
    This helper normalises the dict so callers can always access ``data["on"]``.
    """
    assert WORKFLOW_PATH.exists(), (
        f"Workflow file not found at {WORKFLOW_PATH}. "
        "Create .github/workflows/pr-syntax-check.yml"
    )
    with WORKFLOW_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "Workflow YAML root must be a mapping"
    # yaml.safe_load converts the bare YAML key `on` to bool True in Python
    if True in data and "on" not in data:
        data = {**data, "on": data[True]}
    return data


class TestWorkflowFileExists:
    def test_workflow_file_exists(self):
        assert WORKFLOW_PATH.exists(), (
            f"Expected workflow at {WORKFLOW_PATH}"
        )

    def test_workflow_is_valid_yaml(self):
        with WORKFLOW_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert data is not None


class TestWorkflowTriggers:
    def test_triggered_on_pull_request(self):
        workflow = _load_workflow()
        assert "on" in workflow, "Workflow must have an 'on' trigger"
        on_section = workflow["on"]
        # 'on' can be a dict or a list; PR trigger can be plain 'pull_request' key
        if isinstance(on_section, dict):
            assert "pull_request" in on_section, (
                "Workflow must trigger on 'pull_request' events"
            )
        else:
            assert "pull_request" in on_section, (
                "Workflow must trigger on 'pull_request' events"
            )

    def test_pull_request_targets_main(self):
        workflow = _load_workflow()
        on_section = workflow["on"]
        if not isinstance(on_section, dict):
            pytest.skip("on-section is not a mapping, skipping branch check")
        pr_config = on_section.get("pull_request", {})
        if pr_config is None:
            # bare trigger without config is acceptable
            return
        branches = pr_config.get("branches", [])
        assert "main" in branches, (
            "pull_request trigger should target the 'main' branch"
        )


class TestWorkflowJobs:
    def test_jobs_section_exists(self):
        workflow = _load_workflow()
        assert "jobs" in workflow, "Workflow must define at least one job"
        assert isinstance(workflow["jobs"], dict)
        assert len(workflow["jobs"]) >= 1

    def test_syntax_check_job_exists(self):
        workflow = _load_workflow()
        jobs = workflow["jobs"]
        assert "syntax-check" in jobs, (
            "Workflow must contain a job named 'syntax-check'"
        )

    def test_job_runs_on_ubuntu(self):
        workflow = _load_workflow()
        job = workflow["jobs"]["syntax-check"]
        runs_on = job.get("runs-on", "")
        assert "ubuntu" in runs_on, (
            "syntax-check job should run on an ubuntu runner"
        )

    def test_job_has_steps(self):
        workflow = _load_workflow()
        job = workflow["jobs"]["syntax-check"]
        steps = job.get("steps", [])
        assert len(steps) >= 2, "Job must have at least 2 steps (checkout + linter)"


class TestWorkflowSteps:
    def test_checkout_step_present(self):
        workflow = _load_workflow()
        steps = workflow["jobs"]["syntax-check"]["steps"]
        uses_values = [step.get("uses", "") for step in steps]
        assert any("actions/checkout" in u for u in uses_values), (
            "Workflow must include an actions/checkout step"
        )

    def test_python_setup_step_present(self):
        workflow = _load_workflow()
        steps = workflow["jobs"]["syntax-check"]["steps"]
        uses_values = [step.get("uses", "") for step in steps]
        assert any("actions/setup-python" in u for u in uses_values), (
            "Workflow must include an actions/setup-python step"
        )

    def test_linter_run_step_present(self):
        """At least one step must run ruff or flake8 for syntax checking."""
        workflow = _load_workflow()
        steps = workflow["jobs"]["syntax-check"]["steps"]
        run_commands = [step.get("run", "") for step in steps if "run" in step]
        combined = " ".join(run_commands)
        assert "ruff" in combined or "flake8" in combined, (
            "Workflow must run 'ruff' or 'flake8' for syntax checking"
        )

    def test_linter_covers_src_directory(self):
        """The linter command must target the src directory."""
        workflow = _load_workflow()
        steps = workflow["jobs"]["syntax-check"]["steps"]
        run_commands = [step.get("run", "") for step in steps if "run" in step]
        combined = " ".join(run_commands)
        assert "src" in combined, (
            "Linter must target the 'src' directory"
        )

    def test_python_version_is_specified(self):
        """setup-python step must pin a Python version."""
        workflow = _load_workflow()
        steps = workflow["jobs"]["syntax-check"]["steps"]
        for step in steps:
            if "actions/setup-python" in step.get("uses", ""):
                with_block = step.get("with", {})
                assert "python-version" in with_block, (
                    "setup-python step must specify python-version"
                )
                return
        pytest.fail("setup-python step not found")


class TestWorkflowName:
    def test_workflow_has_name(self):
        workflow = _load_workflow()
        assert "name" in workflow, "Workflow should have a human-readable name"
        assert workflow["name"], "Workflow name must not be empty"
