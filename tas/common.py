"""Shared helpers: config loading, the run Context, and tool execution.

Every module gets a Context and shells out through run()/run_capture() so that
behaviour (logging, missing-tool handling, output layout) is identical on macOS
and Windows.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent

# Defaults so the orchestrator works even if config.yaml or PyYAML is missing.
DEFAULTS = {
    "rate": {"threads": 4, "delay_ms": 500, "rate_limit": 5},
    "output_dir": "output",
    "wordlists": {
        "dns": "wordlists/dns/subdomains.txt",
        "content": "wordlists/content/raft-medium-directories.txt",
        "params": "wordlists/params/parameters.txt",
        "passwords": "wordlists/passwords/rockyou.txt",
    },
    "tools": {},
}

# ---------------------------------------------------------------- logging ----
_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def info(msg: str) -> None:
    print(_c("36", "[*] ") + msg)


def good(msg: str) -> None:
    print(_c("32", "[+] ") + msg)


def warn(msg: str) -> None:
    print(_c("33", "[!] ") + msg)


def err(msg: str) -> None:
    print(_c("31", "[x] ") + msg, file=sys.stderr)


def stage_banner(name: str) -> None:
    print(_c("35;1", f"\n=== {name} ==="))


# ----------------------------------------------------------------- config ----
def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> dict:
    cfg_path = Path(path) if path else REPO_ROOT / "config" / "config.yaml"
    data = {}
    if cfg_path.exists():
        if yaml is None:
            warn("PyYAML not installed, using default settings. `pip install -r requirements.txt`")
        else:
            data = yaml.safe_load(cfg_path.read_text()) or {}
    return _deep_merge(DEFAULTS, data)


# -------------------------------------------------------------- execution ----
def tool_bin(ctx, key: str) -> str:
    return (ctx.cfg.get("tools", {}).get(key) or {}).get("bin", key)


def tool_extra(ctx, key: str) -> list:
    return list((ctx.cfg.get("tools", {}).get(key) or {}).get("extra_args", []))


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def run(cmd: list, stdout_to: str | Path | None = None, check_tool: bool = True) -> int | None:
    """Run a command. Returns exit code, or None if the tool is missing.

    cmd[0] is the binary. If it is not on PATH we skip (so a full pipeline run
    keeps going) and tell the user how to install it.
    """
    cmd = [str(x) for x in cmd]
    if check_tool and not have(cmd[0]):
        warn(f"'{cmd[0]}' not found on PATH, skipping. Install with: python tas.py install")
        return None
    info("$ " + " ".join(cmd) + (f"  > {stdout_to}" if stdout_to else ""))
    try:
        if stdout_to:
            Path(stdout_to).parent.mkdir(parents=True, exist_ok=True)
            with open(stdout_to, "w") as fh:
                return subprocess.run(cmd, stdout=fh).returncode
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        warn("interrupted")
        raise
    except Exception as e:  # noqa: BLE001
        err(f"failed to run {cmd[0]}: {e}")
        return 1


# --------------------------------------------------------------- context -----
class Context:
    """Carries the run's state: target, output dir, config, and the artifacts
    (output files) each stage produces so later stages can consume them."""

    def __init__(self, target: str, outdir: Path, cfg: dict, args):
        self.target = target
        self.outdir = Path(outdir)
        self.cfg = cfg
        self.args = args
        self.artifacts: dict[str, Path] = {}
        self.outdir.mkdir(parents=True, exist_ok=True)

    # rate knobs (CLI overrides config)
    @property
    def threads(self) -> int:
        return int(getattr(self.args, "threads", None) or self.cfg["rate"]["threads"])

    @property
    def delay_ms(self) -> int:
        v = getattr(self.args, "delay", None)
        return int(v if v is not None else self.cfg["rate"]["delay_ms"])

    @property
    def rate_limit(self) -> int:
        return int(getattr(self.args, "rate", None) or self.cfg["rate"]["rate_limit"])

    def delay_s(self) -> str:
        return f"{self.delay_ms / 1000:.3f}"

    # paths
    def stage_dir(self, name: str) -> Path:
        p = self.outdir / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def out(self, name: str, filename: str) -> Path:
        return self.stage_dir(name) / filename

    def wordlist(self, key: str) -> Path:
        return REPO_ROOT / self.cfg["wordlists"][key]

    # artifacts
    def set(self, key: str, path: str | Path) -> None:
        self.artifacts[key] = Path(path)

    def get(self, *keys: str) -> Path | None:
        """First existing, non-empty artifact among keys."""
        for k in keys:
            p = self.artifacts.get(k)
            if p and Path(p).exists() and Path(p).stat().st_size > 0:
                return Path(p)
        return None

    def input_file(self, *artifact_keys: str) -> Path | None:
        """Resolve a stage's input: explicit --input wins, else an upstream
        artifact, else a one-line file containing the target."""
        inp = getattr(self.args, "input", None)
        if inp:
            p = Path(inp)
            if not p.exists():
                err(f"--input {inp} does not exist")
                return None
            return p
        art = self.get(*artifact_keys)
        if art:
            return art
        return None

    def target_file(self) -> Path:
        """A file containing the target (domain or the contents of a target file)."""
        p = self.out("_meta", "target.txt")
        tp = Path(self.target)
        if tp.exists():
            p.write_text(tp.read_text())
        else:
            p.write_text(self.target.strip() + "\n")
        return p


def read_lines(path: str | Path) -> list[str]:
    if not path or not Path(path).exists():
        return []
    return [ln.strip() for ln in Path(path).read_text(errors="ignore").splitlines() if ln.strip()]
