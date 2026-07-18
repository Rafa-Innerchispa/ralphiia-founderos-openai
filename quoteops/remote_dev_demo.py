from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import subprocess
import sys
import tempfile
from threading import RLock
from time import perf_counter
from typing import Any, Protocol


MAX_MESSAGE_CHARS = 1200
MAX_MEDIA_BYTES = 5 * 1024 * 1024
SESSION_TTL = timedelta(minutes=30)
MAX_ACTIONS_PER_SESSION = 3
MAX_ACTIVE_SESSIONS = 200
SAFE_ENV_KEYS = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "SHELL", "CODEX_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR")
ALLOWED_MEDIA = {
    "audio/ogg": "audio",
    "audio/webm": "audio",
    "audio/mp4": "audio",
    "audio/x-m4a": "audio",
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
}

SECRET_RE = re.compile(
    r"(?i)(api[_ -]?key|authorization|bearer|password|token|secret|private[_ -]?key)\s*[:=]\s*\S+"
)
PATH_RE = re.compile(r"/(?:home|root|Users)/[^\s]+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(value: str, limit: int = 2000) -> str:
    text = str(value or "")[:limit]
    text = SECRET_RE.sub("[REDACTED_SECRET]", text)
    text = PATH_RE.sub("[REDACTED_PATH]", text)
    return IP_RE.sub("[REDACTED_IP]", text)


def _safe_id(prefix: str, size: int = 8) -> str:
    return f"{prefix}_{secrets.token_urlsafe(size).replace('-', '').replace('_', '').lower()}"


@dataclass(frozen=True)
class DemoScenario:
    scenario_id: str
    label: str
    agent: str
    task_title: str
    fixed_prompt: str
    allowed_tools: tuple[str, ...]
    scopes: tuple[str, ...]
    requires_human_approval: bool = True


SCENARIOS: dict[str, DemoScenario] = {
    "fix_quote_total": DemoScenario(
        scenario_id="fix_quote_total",
        label="Corregir total de cotización y probar",
        agent="codex",
        task_title="DEMO — Corregir cálculo seguro de total y ejecutar pruebas",
        fixed_prompt=(
            "Trabaja únicamente en este repositorio sintético. Implementa safe_total en "
            "calculator.py para sumar valores no negativos, sin modificar test_calculator.py. "
            "Ejecuta las pruebas y resume el cambio. No accedas a red, secretos ni rutas externas."
        ),
        allowed_tools=("repo:read", "repo:write", "test:unittest", "git:diff", "git:commit"),
        scopes=("ralfia:demo", "ralfia:repo:write", "ralfia:test:run"),
    ),
    "inspect_services": DemoScenario(
        scenario_id="inspect_services",
        label="Revisar estado de servicios",
        agent="codex",
        task_title="DEMO — Inspeccionar fixture de servicios y producir diagnóstico",
        fixed_prompt=(
            "Analiza service_status.json en este repositorio sintético, crea DIAGNOSIS.md con "
            "hallazgos y recomendaciones, y ejecuta las pruebas. No uses red ni comandos de sistema."
        ),
        allowed_tools=("repo:read", "repo:write", "test:unittest", "git:diff", "git:commit"),
        scopes=("ralfia:demo", "ralfia:repo:write", "ralfia:test:run"),
    ),
}


@dataclass
class DemoEvent:
    event_id: str
    event_type: str
    actor: str
    status: str
    occurred_at: str
    latency_ms: float | None = None
    tool: str | None = None
    detail: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DemoSession:
    session_id: str
    actor_id: str
    token_hash: str
    created_at: str
    expires_at: str
    events: list[DemoEvent] = field(default_factory=list)
    actions: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency: dict[str, str] = field(default_factory=dict)


class DemoRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, DemoSession] = {}
        self._lock = RLock()

    def create(self) -> tuple[DemoSession, str]:
        token = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc)
        session = DemoSession(
            session_id=_safe_id("demo"),
            actor_id=_safe_id("demo_user", 5),
            token_hash=sha256(token.encode()).hexdigest(),
            created_at=now.isoformat(),
            expires_at=(now + SESSION_TTL).isoformat(),
        )
        with self._lock:
            for session_id, existing in list(self._sessions.items()):
                if datetime.fromisoformat(existing.expires_at) <= now:
                    del self._sessions[session_id]
            if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
                raise PermissionError("demo_capacity_reached")
            self._sessions[session.session_id] = session
        return session, token

    def require(self, session_id: str, token: str) -> DemoSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise PermissionError("demo_session_not_found")
            expected = session.token_hash
            supplied = sha256(str(token or "").encode()).hexdigest()
            if not hmac.compare_digest(expected, supplied):
                raise PermissionError("demo_session_token_invalid")
            if datetime.fromisoformat(session.expires_at) <= datetime.now(timezone.utc):
                raise PermissionError("demo_session_expired")
            return session

    def add_event(
        self,
        session: DemoSession,
        event_type: str,
        *,
        actor: str,
        status: str = "completed",
        latency_ms: float | None = None,
        tool: str | None = None,
        detail: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> DemoEvent:
        safe_evidence = {
            str(key): _redact(str(value), 500)
            for key, value in (evidence or {}).items()
            if key in {"message_id", "correlation_id", "task_id", "job_id", "commit", "tests", "checksum", "provider"}
        }
        event = DemoEvent(
            event_id=_safe_id("evt", 6),
            event_type=event_type,
            actor=actor,
            status=status,
            occurred_at=_now(),
            latency_ms=round(latency_ms, 2) if latency_ms is not None else None,
            tool=tool,
            detail=_redact(detail or "", 800) or None,
            evidence=safe_evidence,
        )
        with self._lock:
            session.events.append(event)
        return event

    def snapshot(self, session: DemoSession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "actor_id": session.actor_id,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
            "events": [asdict(item) for item in session.events],
            "actions": [
                {
                    key: value
                    for key, value in action.items()
                    if key not in {"checkpoint_hash", "raw_media", "prompt"}
                }
                for action in session.actions.values()
            ],
        }


class CoordinationGateway(Protocol):
    mode: str

    async def create_task(self, scenario: DemoScenario, correlation_id: str) -> dict[str, Any]: ...

    async def start_task(self, task_id: str) -> None: ...

    async def finish_task(self, task_id: str, *, ok: bool, evidence: dict[str, Any]) -> None: ...


class OfflineCoordinationGateway:
    mode = "offline_local_first"

    async def create_task(self, scenario: DemoScenario, correlation_id: str) -> dict[str, Any]:
        return {"task_id": _safe_id("ops_demo", 7), "correlation_id": correlation_id, "status": "proposed"}

    async def start_task(self, task_id: str) -> None:
        return None

    async def finish_task(self, task_id: str, *, ok: bool, evidence: dict[str, Any]) -> None:
        return None


class McpCoordinationGateway:
    mode = "mcp_live"

    def __init__(self, url: str, api_key: str) -> None:
        if not url or not api_key:
            raise ValueError("mcp_url_and_api_key_required")
        self.url = url
        self.api_key = api_key

    async def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport

        transport = StreamableHttpTransport(self.url, headers={"X-API-Key": self.api_key})
        async with Client(transport, timeout=30) as client:
            result = await client.call_tool(name, arguments, raise_on_error=False)
        payload = result.data if isinstance(result.data, dict) else result.structured_content
        if result.is_error or not isinstance(payload, dict):
            raise RuntimeError(f"mcp_{name}_failed")
        if payload.get("ok") is False:
            raise RuntimeError(str(payload.get("error") or f"mcp_{name}_failed"))
        return payload

    async def create_task(self, scenario: DemoScenario, correlation_id: str) -> dict[str, Any]:
        result = await self._call(
            "create_ops_task",
            {
                "assignee": scenario.agent,
                "title": scenario.task_title,
                "checklist": [scenario.fixed_prompt],
                "evidence_required": ["commit", "tests", "latency", "response"],
                "priority": "normal",
                "from_agent": "RAFAEL",
                "correlation_id": correlation_id,
            },
        )
        task = result.get("task") if isinstance(result.get("task"), dict) else result
        return {
            "task_id": result.get("task_id") or task.get("task_id"),
            "correlation_id": result.get("correlation_id") or correlation_id,
            "status": task.get("status", "proposed"),
        }

    async def start_task(self, task_id: str) -> None:
        accepted = await self._call(
            "update_ops_task_state",
            {"task_id": task_id, "status": "accepted", "actor": "codex", "expected_revision": 1},
        )
        await self._call(
            "update_ops_task_state",
            {
                "task_id": task_id,
                "status": "in_progress",
                "actor": "codex",
                "expected_revision": accepted.get("revision", 2),
            },
        )

    async def finish_task(self, task_id: str, *, ok: bool, evidence: dict[str, Any]) -> None:
        if ok:
            verification = await self._call(
                "update_ops_task_state",
                {"task_id": task_id, "status": "verification", "actor": "codex", "evidence": evidence},
            )
            await self._call(
                "update_ops_task_state",
                {
                    "task_id": task_id,
                    "status": "completed",
                    "actor": "codex",
                    "expected_revision": verification.get("revision"),
                    "evidence": evidence,
                },
            )
        else:
            await self._call(
                "update_ops_task_state",
                {"task_id": task_id, "status": "failed", "actor": "codex", "evidence": evidence},
            )


@dataclass
class MediaResult:
    kind: str
    mimetype: str
    checksum: str
    provider: str
    text: str
    status: str


class LocalMediaProcessor:
    def __init__(self, root: Path, whisper_url: str = "http://127.0.0.1:9001") -> None:
        self.root = root.resolve()
        self.whisper_url = whisper_url.rstrip("/")

    def process(self, data: bytes, mimetype: str) -> MediaResult:
        mime = str(mimetype or "").split(";", 1)[0].lower().strip()
        kind = ALLOWED_MEDIA.get(mime)
        if not kind:
            raise ValueError("demo_media_mime_not_allowed")
        if len(data) > MAX_MEDIA_BYTES:
            raise ValueError("demo_media_size_limit_exceeded")
        checksum = sha256(data).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True)
        suffix = {"audio": ".input", "image": ".image"}[kind]
        with tempfile.NamedTemporaryFile(dir=self.root, suffix=suffix, delete=False) as handle:
            handle.write(data)
            path = Path(handle.name)
        try:
            if kind == "image":
                proc = subprocess.run(
                    ["tesseract", str(path), "stdout", "-l", os.getenv("OCR_LANG", "spa+eng")],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=False,
                )
                if proc.returncode != 0:
                    raise RuntimeError("local_ocr_unavailable")
                return MediaResult(kind, mime, checksum, "local_tesseract", proc.stdout.strip(), "processed")

            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("local_ffmpeg_unavailable")
            normalized = path.with_suffix(".wav")
            proc = subprocess.run(
                [ffmpeg, "-y", "-i", str(path), "-ac", "1", "-ar", "16000", "-vn", str(normalized)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError("audio_normalization_failed")
            import httpx

            with normalized.open("rb") as audio:
                response = httpx.post(
                    f"{self.whisper_url}/asr?output=json&task=transcribe&encode=true",
                    files={"audio_file": ("demo.wav", audio, "audio/wav")},
                    timeout=90,
                )
            response.raise_for_status()
            payload = response.json()
            return MediaResult(
                kind,
                mime,
                checksum,
                "local_whisper",
                str(payload.get("text") or "").strip(),
                "processed",
            )
        finally:
            path.unlink(missing_ok=True)
            path.with_suffix(".wav").unlink(missing_ok=True)


@dataclass
class ExecutionResult:
    ok: bool
    status: str
    job_id: str
    commit: str | None
    tests: str
    summary: str
    latency_ms: float
    model_requested: str | None = None
    codex_thread_id: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class ScenarioExecutor(Protocol):
    def run(self, session_id: str, scenario: DemoScenario) -> ExecutionResult: ...


class CodexScenarioExecutor:
    def __init__(self, root: Path, codex_bin: str, *, enabled: bool = False, timeout: int = 240, model: str = "gpt-5.6-sol") -> None:
        self.root = root.resolve()
        self.codex_bin = codex_bin
        self.enabled = enabled
        self.timeout = min(max(timeout, 30), 300)
        self.model = model

    @staticmethod
    def _codex_metadata(events: str) -> tuple[str | None, dict[str, int]]:
        thread_id = None
        usage: dict[str, int] = {}
        for line in (events or "").splitlines():
            try:
                event = json.loads(line)
            except (TypeError, ValueError):
                continue
            if event.get("type") == "thread.started":
                thread_id = str(event.get("thread_id") or "") or None
            elif event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                usage = {
                    str(key): int(value)
                    for key, value in event["usage"].items()
                    if isinstance(value, (int, float))
                }
        return thread_id, usage

    @staticmethod
    def _run(command: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        safe_env = {key: os.environ[key] for key in SAFE_ENV_KEYS if os.environ.get(key)}
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
            env=safe_env,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    def _prepare(self, session_id: str, scenario: DemoScenario) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        workspace = (self.root / session_id / scenario.scenario_id).resolve()
        if self.root not in workspace.parents:
            raise RuntimeError("demo_workspace_escape_rejected")
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        if scenario.scenario_id == "fix_quote_total":
            (workspace / "calculator.py").write_text(
                "def subtotal(values):\n    return sum(values)\n",
                encoding="utf-8",
            )
            (workspace / "test_calculator.py").write_text(
                "import unittest\n\n"
                "from calculator import safe_total\n\n"
                "class SafeTotalTest(unittest.TestCase):\n"
                "    def test_safe_total_ignores_negative_values(self):\n"
                "        self.assertEqual(safe_total([120.0, -5.0, 30.0]), 150.0)\n",
                encoding="utf-8",
            )
        else:
            (workspace / "service_status.json").write_text(
                json.dumps({"mcp": "active", "portal": "active", "worker": "degraded"}, indent=2),
                encoding="utf-8",
            )
            (workspace / "test_diagnosis.py").write_text(
                "from pathlib import Path\n"
                "import unittest\n\n"
                "class DiagnosisTest(unittest.TestCase):\n"
                "    def test_diagnosis_exists(self):\n"
                "        text = Path('DIAGNOSIS.md').read_text()\n"
                "        self.assertIn('worker', text.lower())\n",
                encoding="utf-8",
            )
        (workspace / ".gitignore").write_text("__pycache__/\n*.py[cod]\n", encoding="utf-8")
        self._run(["git", "init", "-q"], workspace)
        self._run(["git", "config", "user.email", "demo@ralfia.local"], workspace)
        self._run(["git", "config", "user.name", "RalfIA Demo"], workspace)
        self._run(["git", "add", "."], workspace)
        self._run(["git", "commit", "-qm", "Synthetic fixture"], workspace)
        return workspace

    def run(self, session_id: str, scenario: DemoScenario) -> ExecutionResult:
        started = perf_counter()
        job_id = _safe_id("exec", 7)
        if not self.enabled:
            return ExecutionResult(
                False,
                "disabled",
                job_id,
                None,
                "not_run",
                "La ejecución Codex está deshabilitada en este entorno.",
                (perf_counter() - started) * 1000,
            )
        workspace = self._prepare(session_id, scenario)
        with tempfile.NamedTemporaryFile(prefix=f"{job_id}-", suffix=".txt", delete=False) as handle:
            output_path = Path(handle.name)
        command = [
            self.codex_bin,
            "exec",
            "--ignore-user-config",
            "-m",
            self.model,
            "-c",
            "shell_environment_policy.inherit=none",
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "--json",
            "--cd",
            str(workspace),
            "-o",
            str(output_path),
            scenario.fixed_prompt,
        ]
        try:
            agent = self._run(command, workspace, self.timeout)
            codex_thread_id, usage = self._codex_metadata(agent.stdout)
            status = self._run(["git", "status", "--porcelain"], workspace)
            changed = bool(status.stdout.strip())
            tests = self._run(
                [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
                workspace,
                90,
            )
            ok = agent.returncode == 0 and changed and tests.returncode == 0
            if ok:
                self._run(["git", "add", "."], workspace)
                self._run(["git", "commit", "-qm", f"Demo execution {job_id}"], workspace)
                commit = self._run(["git", "rev-parse", "--short", "HEAD"], workspace).stdout.strip()
            else:
                commit = None
            test_summary = _redact(((tests.stdout or "") + "\n" + (tests.stderr or ""))[-1600:])
            final_output = output_path.read_text(errors="replace") if output_path.exists() else ""
            summary = _redact(final_output or (agent.stdout or agent.stderr or "")[-1600:])
            if agent.returncode == 0 and not changed:
                summary = f"no_verifiable_change: {summary}"[:1600]
            return ExecutionResult(
                ok=ok,
                status="completed" if ok else "failed",
                job_id=job_id,
                commit=commit,
                tests=test_summary,
                summary=summary,
                latency_ms=(perf_counter() - started) * 1000,
                model_requested=self.model,
                codex_thread_id=codex_thread_id,
                usage=usage,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                False,
                "timeout",
                job_id,
                None,
                "not_completed",
                "La ejecución alcanzó el timeout seguro.",
                (perf_counter() - started) * 1000,
            )
        finally:
            output_path.unlink(missing_ok=True)


class RemoteDevDemoService:
    def __init__(
        self,
        registry: DemoRegistry,
        coordination: CoordinationGateway,
        executor: ScenarioExecutor,
        media_processor: LocalMediaProcessor,
    ) -> None:
        self.registry = registry
        self.coordination = coordination
        self.executor = executor
        self.media_processor = media_processor

    def create_session(self) -> dict[str, Any]:
        session, token = self.registry.create()
        self.registry.add_event(
            session,
            "session_created",
            actor="ralfia",
            tool="identity:ephemeral",
            detail="Identidad DEMO aislada; sin acceso a datos privados ni producción.",
        )
        return {
            "ok": True,
            "session_id": session.session_id,
            "actor_id": session.actor_id,
            "session_token": token,
            "expires_at": session.expires_at,
            "coordination_mode": self.coordination.mode,
            "scenarios": [asdict(item) for item in SCENARIOS.values()],
        }

    async def submit(
        self,
        session_id: str,
        token: str,
        *,
        request_id: str,
        scenario_id: str,
        message: str,
        media: bytes | None = None,
        media_type: str | None = None,
    ) -> dict[str, Any]:
        started = perf_counter()
        session = self.registry.require(session_id, token)
        if len(session.actions) >= MAX_ACTIONS_PER_SESSION:
            raise PermissionError("demo_session_action_limit_reached")
        request_id = str(request_id or "").strip()[:100]
        if not request_id:
            raise ValueError("demo_request_id_required")
        if request_id in session.idempotency:
            action = session.actions[session.idempotency[request_id]]
            return {"ok": True, "idempotent": True, "action": self._public_action(action)}
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            raise ValueError("demo_scenario_not_allowed")
        clean_message = str(message or "").strip()[:MAX_MESSAGE_CHARS]
        message_id = _safe_id("wamid_demo", 8)
        correlation_id = f"demo-{sha256(f'{session_id}:{request_id}:{scenario_id}'.encode()).hexdigest()[:16]}"
        self.registry.add_event(
            session,
            "message_received",
            actor=session.actor_id,
            tool="whatsapp_transport_emulator",
            latency_ms=(perf_counter() - started) * 1000,
            detail=clean_message or "Mensaje multimedia recibido",
            evidence={"message_id": message_id, "correlation_id": correlation_id},
        )
        self.registry.add_event(
            session,
            "identity_verified",
            actor="ralfia-auth",
            tool="same-session-token+hmac",
            detail="Identidad efímera verificada; scopes mínimos aplicados.",
        )
        media_result: MediaResult | None = None
        if media is not None:
            media_started = perf_counter()
            media_result = self.media_processor.process(media, media_type or "")
            self.registry.add_event(
                session,
                "media_processed",
                actor="local-media",
                tool=media_result.provider,
                latency_ms=(perf_counter() - media_started) * 1000,
                detail="Contenido derivado marcado como no confiable; no controla el executor.",
                evidence={"checksum": media_result.checksum, "provider": media_result.provider},
            )
        mcp_started = perf_counter()
        task = await self.coordination.create_task(scenario, correlation_id)
        self.registry.add_event(
            session,
            "ops_task_created",
            actor="mcp-coordination",
            tool=self.coordination.mode,
            latency_ms=(perf_counter() - mcp_started) * 1000,
            detail=f"Tarea asignada a {scenario.agent}; ejecución aún bloqueada por checkpoint humano.",
            evidence={"task_id": task["task_id"], "correlation_id": correlation_id},
        )
        action_id = _safe_id("action", 7)
        checkpoint = secrets.token_urlsafe(12)
        action = {
            "action_id": action_id,
            "request_id": request_id,
            "message_id": message_id,
            "correlation_id": correlation_id,
            "task_id": task["task_id"],
            "scenario_id": scenario_id,
            "agent": scenario.agent,
            "status": "awaiting_approval",
            "checkpoint_hash": sha256(checkpoint.encode()).hexdigest(),
            "created_at": _now(),
            "media": asdict(media_result) if media_result else None,
            "scopes": list(scenario.scopes),
            "allowed_tools": list(scenario.allowed_tools),
        }
        session.actions[action_id] = action
        session.idempotency[request_id] = action_id
        self.registry.add_event(
            session,
            "human_checkpoint_required",
            actor="policy-engine",
            status="awaiting_approval",
            tool="approval-gate",
            detail="La misma sesión debe confirmar antes de ejecutar Codex.",
        )
        public = self._public_action(action)
        public["checkpoint"] = checkpoint
        return {"ok": True, "idempotent": False, "action": public, "snapshot": self.registry.snapshot(session)}

    async def approve(self, session_id: str, token: str, action_id: str, checkpoint: str) -> dict[str, Any]:
        session = self.registry.require(session_id, token)
        action = session.actions.get(action_id)
        if not action:
            raise ValueError("demo_action_not_found")
        if action["status"] != "awaiting_approval":
            return {"ok": action["status"] == "completed", "idempotent": True, "action": self._public_action(action)}
        supplied = sha256(str(checkpoint or "").encode()).hexdigest()
        if not hmac.compare_digest(action["checkpoint_hash"], supplied):
            raise PermissionError("demo_checkpoint_invalid")
        scenario = SCENARIOS[action["scenario_id"]]
        action["status"] = "running"
        self.registry.add_event(
            session,
            "human_checkpoint_approved",
            actor=session.actor_id,
            tool="approval-gate",
            detail="Aprobación ligada a la misma identidad efímera.",
        )
        await self.coordination.start_task(action["task_id"])
        self.registry.add_event(
            session,
            "agent_started",
            actor=scenario.agent,
            status="running",
            tool="codex-cli" if scenario.agent == "codex" else "mcp-inbox",
            detail="Executor limitado al workspace sintético y herramientas permitidas.",
        )
        result = self.executor.run(session.session_id, scenario)
        action.update(
            status="completed" if result.ok else "failed",
            job_id=result.job_id,
            commit=result.commit,
            tests=result.tests,
            summary=result.summary,
            latency_ms=round(result.latency_ms, 2),
            model_requested=result.model_requested,
            codex_thread_id=result.codex_thread_id,
            usage=result.usage,
            finished_at=_now(),
        )
        evidence = {
            "status": "PASS" if result.ok else "FAIL",
            "job_id": result.job_id,
            "commit": result.commit or "none",
            "tests": result.tests,
            "model_requested": result.model_requested or "not_reported",
            "codex_thread_id": result.codex_thread_id or "not_reported",
            "usage": result.usage,
        }
        await self.coordination.finish_task(action["task_id"], ok=result.ok, evidence=evidence)
        self.registry.add_event(
            session,
            "agent_completed" if result.ok else "agent_failed",
            actor=scenario.agent,
            status=action["status"],
            tool="codex-cli",
            latency_ms=result.latency_ms,
            detail=result.summary,
            evidence=evidence,
        )
        self.registry.add_event(
            session,
            "response_ready",
            actor="ralfia",
            status=action["status"],
            tool="same-chat-response",
            detail=(
                f"Trabajo {result.job_id} completado; pruebas: {result.tests}"
                if result.ok
                else f"Trabajo {result.job_id} no completado: {result.status}"
            ),
        )
        return {"ok": result.ok, "idempotent": False, "action": self._public_action(action), "snapshot": self.registry.snapshot(session)}

    def snapshot(self, session_id: str, token: str) -> dict[str, Any]:
        return self.registry.snapshot(self.registry.require(session_id, token))

    @staticmethod
    def _public_action(action: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in action.items()
            if key not in {"checkpoint_hash", "prompt", "raw_media"}
        }
