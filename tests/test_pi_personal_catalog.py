"""Personal Pi discovery without provider calls or credential replication."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from omnigent import pi_native_credentials as creds
from omnigent.host.connect import _RUNNER_ENV_ALLOWLIST, HostProcess
from omnigent.host.frames import HostModelOptionsFrame


@pytest.fixture
def personal_pi(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OMNIGENT_PI_NATIVE_CATALOG", "1")
    monkeypatch.setattr(creds, "resolve_pi_native_provider", lambda: None)
    monkeypatch.setattr("omnigent.pi_native.resolve_pi_executable", lambda: "/bin/pi")


def test_native_catalog_reaches_host_picker(
    personal_pi: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [
            "/bin/pi",
            "--no-extensions",
            "--no-skills",
            "--no-prompt-templates",
            "--no-themes",
            "--no-context-files",
            "--no-approve",
            "--no-session",
            "--list-models",
        ]
        assert kwargs["cwd"] == Path.home()
        assert kwargs["timeout"] == 10
        assert kwargs["stderr"] == subprocess.DEVNULL
        assert kwargs["stdin"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(
            args,
            0,
            """provider model context max-out thinking images
openrouter ~vendor/model-latest 1.1M 128K yes yes
openrouter vendor/model:free 128K 8K yes yes
anthropic model 200K 32K yes no
openrouter vendor/model:free 128K 8K yes yes
diagnostic text must never become picker metadata
""",
        )

    monkeypatch.setattr(creds.subprocess, "run", run)
    result = asyncio.run(
        HostProcess._handle_model_options(
            SimpleNamespace(),  # type: ignore[arg-type]
            HostModelOptionsFrame(request_id="personal-catalog", harness="pi-native"),
        )
    )
    assert result.status == "ok"
    assert result.models == [
        {"id": "anthropic/model", "model": "anthropic/model", "displayName": "anthropic/model"},
        {
            "id": "openrouter/vendor/model:free",
            "model": "openrouter/vendor/model:free",
            "displayName": "openrouter/vendor/model:free",
        },
        {
            "id": "openrouter/~vendor/model-latest",
            "model": "openrouter/~vendor/model-latest",
            "displayName": "openrouter/~vendor/model-latest",
        },
    ]


@pytest.mark.parametrize(
    "output", ["No models available", "", "not a catalog\nopenrouter m 1K 1K yes yes"]
)
def test_no_auth_or_unknown_format_is_empty(
    personal_pi: None,
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(
        creds.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, output)
    )
    assert creds.pi_native_model_options() == []


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("pi", 10),
        subprocess.CalledProcessError(1, "pi", stderr="secret-fixture"),
    ],
)
def test_probe_failure_does_not_relay_diagnostics(
    personal_pi: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    def run(*a: object, **k: object) -> None:
        raise error

    monkeypatch.setattr(creds.subprocess, "run", run)
    assert creds.pi_native_model_options() == []
    assert "secret-fixture" not in caplog.text


def test_native_catalog_requires_opt_in(
    personal_pi: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OMNIGENT_PI_NATIVE_CATALOG")
    monkeypatch.setattr(creds.subprocess, "run", lambda *a, **k: pytest.fail("must not probe"))
    assert creds.pi_native_model_options() == []


def test_managed_provider_keeps_precedence(
    personal_pi: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = creds.PiProviderConfig(
        provider_id="omnigent",
        base_url="https://gateway.invalid/v1",
        api="openai-completions",
        model="managed-model",
        api_key="fixture",
        auth_header=True,
    )
    monkeypatch.setattr(creds, "resolve_pi_native_provider", lambda: provider)
    monkeypatch.setattr(creds.subprocess, "run", lambda *a, **k: pytest.fail("must not probe"))
    assert [m["model"] for m in creds.pi_native_model_options()] == ["omnigent/managed-model"]


def test_host_passes_only_nonsecret_opt_in() -> None:
    assert "OMNIGENT_PI_NATIVE_CATALOG" in _RUNNER_ENV_ALLOWLIST
    assert "OPENROUTER_API_KEY" not in _RUNNER_ENV_ALLOWLIST
