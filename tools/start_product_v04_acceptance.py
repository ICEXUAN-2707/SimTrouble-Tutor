"""Build and run the local Product v0.4 browser acceptance service."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
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
PRODUCT_VERSION = "0.4.0"
LOG_ROOT = ROOT / "var" / "acceptance"

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
SECRET_KEYS = frozenset(
    {"DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY", "SILICONFLOW_API_KEY"}
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_ -]?key|authorization|password|secret)\b(\s*[:=]\s*)([^\s,;]+)"
)
AUTHORIZATION_VALUE = re.compile(r"(?i)\bAuthorization\b(\s*[:=]\s*)([^\r\n,;]+)")
BEARER_VALUE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
LOG_THREADS: dict[int, threading.Thread] = {}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class LauncherError(RuntimeError):
    """An actionable local setup, configuration or startup failure."""


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_local_config(path: Path) -> dict[str, str]:
    """Read a strict local NAME=value file; never evaluate shell syntax."""
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise LauncherError(f"Could not read local settings from {path.name}.") from error

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
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
    """Validate with the existing Tutor settings and registry, without exposing secrets."""
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
        summary = f"Tutor uses rule fallback ({resolution.disabled_reason or 'provider_unavailable'})."
    return effective, summary


def build_child_environments(
    process_environment: Mapping[str, str],
    provider_environment: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Pass provider variables to FastAPI only; Vite and build tools receive none."""
    shared = {name: value for name, value in process_environment.items() if name not in LLM_KEYS}
    backend = dict(shared)
    backend.update(provider_environment)
    backend["PYTHONUNBUFFERED"] = "1"
    return backend, dict(shared)


def find_runtime() -> tuple[Path, str, Path, Path]:
    python_executable = (
        ROOT / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else ROOT / ".venv" / "bin" / "python"
    )
    if not python_executable.is_file():
        raise LauncherError(
            "Project Python environment is missing. Follow the Product v0.4 setup in README.md."
        )
    node_executable = shutil.which("node")
    if node_executable is None:
        raise LauncherError("Node.js was not found on PATH. Install Node.js and reopen the launcher.")

    vite_entry = WEB_ROOT / "node_modules" / "vite" / "bin" / "vite.js"
    tsc_entry = WEB_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
    if not vite_entry.is_file() or not tsc_entry.is_file():
        raise LauncherError(
            "Frontend packages are missing. Run 'npm.cmd ci' in apps\\training_web first."
        )
    return python_executable, node_executable, vite_entry, tsc_entry


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
            return response.read(64_000) if response.status == 200 else None
    except (OSError, URLError):
        return None


def _health_matches(url: str) -> bool:
    body = _read_local(url)
    if body is None:
        return False
    try:
        health = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return (
        isinstance(health, dict)
        and health.get("status") == "ok"
        and health.get("version") == PRODUCT_VERSION
    )


def api_is_ready() -> bool:
    return _health_matches(f"{API_URL}/healthz")


def web_is_ready() -> bool:
    body = _read_local(WEB_URL)
    return (
        body is not None
        and b'id="app"' in body
        and _health_matches(f"{WEB_URL}/healthz")
    )


def run_frontend_build(node_executable: str, vite_entry: Path, tsc_entry: Path,
                       environment: Mapping[str, str]) -> None:
    commands = (
        ("TypeScript type check", [node_executable, str(tsc_entry), "--noEmit"]),
        ("Vite production build", [node_executable, str(vite_entry), "build"]),
    )
    for label, command in commands:
        print(f"[BUILD] {label}...", flush=True)
        try:
            subprocess.run(command, cwd=WEB_ROOT, env=dict(environment), check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            raise LauncherError(f"{label} failed; see the build output above.") from error

    built_page = WEB_ROOT / "dist" / "index.html"
    if not built_page.is_file() or b'id="app"' not in built_page.read_bytes():
        raise LauncherError("Production build did not produce the Product v0.4 workspace page.")


def redact_log_line(line: str, secret_values: tuple[str, ...]) -> str:
    redacted = line
    for secret in secret_values:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = AUTHORIZATION_VALUE.sub(r"Authorization\1[REDACTED]", redacted)
    redacted = SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", redacted)
    return BEARER_VALUE.sub("Bearer [REDACTED]", redacted)


def safe_console_text(text: str, encoding: str | None) -> str:
    encoding = encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def _pump_output(stream: TextIO, log_path: Path, label: str,
                 secret_values: tuple[str, ...]) -> None:
    with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
        for line in stream:
            safe_line = redact_log_line(line, secret_values)
            log_file.write(safe_line)
            log_file.flush()
            console_line = safe_console_text(
                f"[{label}] {safe_line}", sys.stdout.encoding
            )
            sys.stdout.write(console_line)
            sys.stdout.flush()


def start_process(
    command: list[str],
    cwd: Path,
    environment: Mapping[str, str],
    log_path: Path,
    label: str,
    secret_values: tuple[str, ...],
) -> subprocess.Popen[str]:
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=flags,
        )
    except OSError as error:
        raise LauncherError(f"Could not start {Path(command[0]).name}.") from error
    assert process.stdout is not None
    reader = threading.Thread(
        target=_pump_output,
        args=(process.stdout, log_path, label, secret_values),
        daemon=True,
    )
    LOG_THREADS[process.pid] = reader
    reader.start()
    return process


def wait_until_ready(
    name: str,
    ready: Callable[[], bool],
    process: subprocess.Popen[str],
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


def stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
            process.wait(timeout=5)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            if process.poll() is None:
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
    reader = LOG_THREADS.pop(process.pid, None)
    if reader is not None:
        reader.join(timeout=2)


def _preflight(config_path: Path):
    local_config = load_local_config(config_path)
    provider_environment, summary = resolve_provider_settings(os.environ, local_config)
    python_executable, node_executable, vite_entry, tsc_entry = find_runtime()
    require_free_port(API_HOST, API_PORT)
    require_free_port(WEB_HOST, WEB_PORT)
    return python_executable, node_executable, vite_entry, tsc_entry, provider_environment, summary


def run_launcher(args: argparse.Namespace, output: TextIO = sys.stdout) -> int:
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    python_executable, node_executable, vite_entry, tsc_entry, provider_environment, summary = (
        _preflight(config_path)
    )
    backend_environment, frontend_environment = build_child_environments(
        os.environ, provider_environment
    )

    commit_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
    print(f"[INFO] Product v{PRODUCT_VERSION}; commit {commit}; mode=browser-acceptance.", file=output)
    print("[OK] Python and frontend runtimes are available.", file=output)
    print("[OK] API and Preview ports are available.", file=output)
    print(f"[INFO] {summary}", file=output)
    if args.check_only:
        print("[OK] Product v0.4 acceptance preflight passed.", file=output)
        return 0

    run_frontend_build(node_executable, vite_entry, tsc_entry, frontend_environment)
    require_free_port(API_HOST, API_PORT)
    require_free_port(WEB_HOST, WEB_PORT)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_directory = LOG_ROOT / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    api_log = log_directory / f"api-{timestamp}.log"
    web_log = log_directory / f"preview-{timestamp}.log"
    secret_values = tuple(backend_environment.get(name, "") for name in SECRET_KEYS)

    api_process: subprocess.Popen[str] | None = None
    web_process: subprocess.Popen[str] | None = None
    try:
        api_process = start_process(
            [str(python_executable), "-B", "-m", "apps.training_api"],
            ROOT,
            backend_environment,
            api_log,
            "API",
            secret_values,
        )
        wait_until_ready("FastAPI", api_is_ready, api_process, args.startup_timeout)

        web_process = start_process(
            [
                node_executable,
                str(vite_entry),
                "preview",
                "--host",
                WEB_HOST,
                "--port",
                str(WEB_PORT),
                "--strictPort",
            ],
            WEB_ROOT,
            frontend_environment,
            web_log,
            "Preview",
            (),
        )
        wait_until_ready("Vite Preview", web_is_ready, web_process, args.startup_timeout)
        print(f"[READY] Product v0.4 acceptance workspace: {WEB_URL}", file=output, flush=True)
        print(f"[INFO] Logs: {api_log.relative_to(ROOT)}; {web_log.relative_to(ROOT)}", file=output)
        if not args.no_browser:
            try:
                if not webbrowser.open(WEB_URL, new=1):
                    print(f"[INFO] Open this address in your browser: {WEB_URL}", file=output)
            except Exception:
                print(f"[INFO] Open this address in your browser: {WEB_URL}", file=output)
        if args.ci_smoke:
            print("[INFO] Running CI browser smoke against the production Preview.", file=output)
            smoke_environment = dict(frontend_environment)
            smoke_environment.setdefault("SIMTROUBLE_URL", WEB_URL)
            smoke_environment.setdefault("SIMTROUBLE_BROWSER_CHANNEL", "bundled")
            try:
                result = subprocess.run(
                    [node_executable, str(WEB_ROOT / "e2e" / "smoke-ci.mjs")],
                    cwd=WEB_ROOT,
                    env=smoke_environment,
                    check=False,
                )
            except OSError as error:
                raise LauncherError("Could not start the Playwright browser smoke.") from error
            return result.returncode
        print("Press Ctrl+C in this window to stop the services started here.", file=output)
        while True:
            for name, process in (("FastAPI", api_process), ("Vite Preview", web_process)):
                exit_code = process.poll()
                if exit_code is not None:
                    raise LauncherError(f"{name} stopped unexpectedly (exit code {exit_code}).")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping acceptance services...", file=output)
        return 0
    finally:
        stop_process(web_process)
        stop_process(api_process)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Use a local NAME=value configuration file")
    parser.add_argument("--check-only", action="store_true", help="Preflight without building or starting")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser after startup")
    parser.add_argument(
        "--ci-smoke",
        action="store_true",
        help="Run the CI Playwright smoke against the production Preview, then stop services",
    )
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
