"""Preflight and launch the local Product v0.5 web and API services."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from typing import TextIO
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "training_web"
DEFAULT_CONFIG = ROOT / ".env.local"
API_HOST = "127.0.0.1"
API_PORT = 8001
WEB_HOST = "127.0.0.1"
WEB_PORT = 5174
API_URL = f"http://{API_HOST}:{API_PORT}"
WEB_URL = f"http://{WEB_HOST}:{WEB_PORT}"
API_VERSION = "0.5.0"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LLM_KEYS = frozenset(
    {
        "SIMTROUBLE_LLM_ENABLED",
        "SIMTROUBLE_LLM_PROVIDER",
        "SIMTROUBLE_LLM_MODEL",
        "SIMTROUBLE_LLM_BASE_URL",
        "SIMTROUBLE_LLM_TIMEOUT_SECONDS",
        "SIMTROUBLE_LLM_MAX_RETRIES",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_TIMEOUT_SECONDS",
        "DEEPSEEK_MAX_RETRIES",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "SILICONFLOW_API_KEY",
    }
)


class LauncherError(RuntimeError):
    """An actionable local setup, configuration, or startup failure."""


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_local_config(path: Path) -> dict[str, str]:
    """Read a small NAME=value file; never evaluate shell syntax."""
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise LauncherError(f"Could not read local settings from {path.name}.") from error
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        lines, start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise LauncherError(f"{path.name}:{line_number} must use NAME=value syntax")
        name, raw_value = line.split("=", maxsplit=1)
        name = name.strip()
        if name not in LLM_KEYS:
            raise LauncherError(
                f"{path.name}:{line_number} contains unsupported setting {name!r}"
            )
        if name in values:
            raise LauncherError(f"{path.name}:{line_number} repeats setting {name!r}")
        values[name] = _unquote(raw_value.strip())
    return values


def resolve_provider_settings(
    process_environment: Mapping[str, str],
    local_config: Mapping[str, str],
) -> tuple[dict[str, str], str]:
    """Validate the same provider rules as the API and return a secret-free summary."""
    from apps.training_api.tutor.providers.registry import TutorProviderRegistry
    from apps.training_api.tutor.settings import LLMProviderSettings

    effective = dict(local_config)
    effective.update(
        {name: process_environment[name] for name in LLM_KEYS if name in process_environment}
    )
    try:
        settings = LLMProviderSettings.from_env(effective)
    except ValueError as error:
        raise LauncherError(
            "Tutor configuration is invalid; review provider, URL, model, timeout and retry values."
        ) from error

    resolution = TutorProviderRegistry().build(settings=settings)
    if resolution.provider is not None:
        summary = f"Tutor provider {settings.provider} is enabled for the API process."
    else:
        summary = (
            f"Tutor uses rule fallback ({resolution.disabled_reason or 'provider_unavailable'})."
        )
    return effective, summary


def build_child_environments(
    process_environment: Mapping[str, str],
    provider_environment: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Keep provider settings in the API environment and omit them from Vite."""
    shared = {name: value for name, value in process_environment.items() if name not in LLM_KEYS}
    backend = dict(shared)
    backend.update(provider_environment)
    backend["PYTHONUNBUFFERED"] = "1"
    frontend = dict(shared)
    return backend, frontend


def find_runtime() -> tuple[Path, str, Path]:
    if os.name == "nt":
        python_executable = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        python_executable = ROOT / ".venv" / "bin" / "python"
    if not python_executable.is_file():
        raise LauncherError(
            "Project Python environment is missing. Follow the first-time setup in README.md."
        )

    node_executable = shutil.which("node")
    if node_executable is None:
        raise LauncherError("Node.js was not found on PATH. Install Node.js and reopen the launcher.")
    vite_entry = WEB_ROOT / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite_entry.is_file():
        raise LauncherError(
            "Frontend packages are missing. Run 'npm.cmd ci' in apps\\training_web first."
        )
    return python_executable, node_executable, vite_entry


def require_free_port(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind((host, port))
        except OSError as error:
            raise LauncherError(
                f"Port {port} on {host} is already in use. Close its service and restart this launcher."
            ) from error


def _read_local(url: str, timeout: float = 1.0) -> bytes | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read(64_000)
    except (OSError, URLError):
        return None


def api_is_ready() -> bool:
    body = _read_local(f"{API_URL}/healthz")
    if body is None:
        return False
    try:
        health = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return (
        isinstance(health, dict)
        and health.get("status") == "ok"
        and health.get("version") == API_VERSION
    )


def web_is_ready() -> bool:
    body = _read_local(WEB_URL)
    return body is not None and b'id="auth-shell"' in body


def start_process(
    command: list[str], cwd: Path, environment: Mapping[str, str]
) -> subprocess.Popen[bytes]:
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        return subprocess.Popen(command, cwd=cwd, env=dict(environment), creationflags=flags)
    except OSError as error:
        raise LauncherError(f"Could not start {Path(command[0]).name}.") from error


def wait_until_ready(
    name: str,
    ready: Callable[[], bool],
    process: subprocess.Popen[bytes],
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ready():
            return
        exit_code = process.poll()
        if exit_code is not None:
            raise LauncherError(f"{name} stopped during startup (exit code {exit_code}).")
        time.sleep(0.25)
    raise LauncherError(f"{name} did not become ready within {timeout_seconds:g} seconds.")


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        process.wait(timeout=5)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _preflight(config_path: Path) -> tuple[Path, str, Path, dict[str, str], str]:
    local_config = load_local_config(config_path)
    provider_environment, summary = resolve_provider_settings(os.environ, local_config)
    python_executable, node_executable, vite_entry = find_runtime()
    require_free_port(API_HOST, API_PORT)
    require_free_port(WEB_HOST, WEB_PORT)
    return python_executable, node_executable, vite_entry, provider_environment, summary


def run_launcher(args: argparse.Namespace, output: TextIO = sys.stdout) -> int:
    config_path = Path(args.config).resolve() if args.config else DEFAULT_CONFIG
    python_executable, node_executable, vite_entry, provider_environment, summary = _preflight(
        config_path
    )
    backend_environment, frontend_environment = build_child_environments(
        os.environ, provider_environment
    )
    print("[OK] Python and frontend runtimes are available.", file=output)
    print("[OK] API and Web ports are available.", file=output)
    print(f"[INFO] {summary}", file=output)
    if args.check_only:
        print("[OK] Product v0.5 preflight passed.", file=output)
        return 0

    api_process: subprocess.Popen[bytes] | None = None
    web_process: subprocess.Popen[bytes] | None = None
    try:
        api_process = start_process(
            [str(python_executable), "-B", "-m", "apps.training_api"],
            ROOT,
            backend_environment,
        )
        wait_until_ready("FastAPI", api_is_ready, api_process, args.startup_timeout)

        web_process = start_process(
            [node_executable, str(vite_entry), "--host", WEB_HOST, "--strictPort"],
            WEB_ROOT,
            frontend_environment,
        )
        wait_until_ready("Vite", web_is_ready, web_process, args.startup_timeout)
        print(f"[READY] Training workspace: {WEB_URL}", file=output, flush=True)
        if not args.no_browser:
            try:
                if not webbrowser.open(WEB_URL, new=1):
                    print(f"[INFO] Open this address in your browser: {WEB_URL}", file=output)
            except Exception:
                print(f"[INFO] Open this address in your browser: {WEB_URL}", file=output)
        print("Press Ctrl+C in this window to stop the services started here.", file=output)
        while True:
            for name, process in (("FastAPI", api_process), ("Vite", web_process)):
                exit_code = process.poll()
                if exit_code is not None:
                    raise LauncherError(f"{name} stopped unexpectedly (exit code {exit_code}).")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping launcher-owned services...", file=output)
        return 0
    finally:
        stop_process(web_process)
        stop_process(api_process)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Use a local NAME=value configuration file")
    parser.add_argument("--check-only", action="store_true", help="Preflight without starting services")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser after startup")
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not math.isfinite(args.startup_timeout) or not 1 <= args.startup_timeout <= 120:
        print("[ERROR] --startup-timeout must be between 1 and 120 seconds.", file=sys.stderr)
        return 2
    try:
        return run_launcher(args)
    except LauncherError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
