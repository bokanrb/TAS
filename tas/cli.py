"""Command-line interface.

Each recon stage is a module in tas/modules/ exposing:
    NAME, HELP, run(ctx)        # required
    add_args(parser)            # optional, for stage-specific flags

`tas <stage> <target>` runs one stage. `tas all <target>` runs the whole
pipeline in order, feeding each stage's output into the next.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .common import Context, load_config, stage_banner, info, warn, err, good, have
from .modules import (
    dns_passive, dns_active, portscan, httpprobe, crawl,
    jsanalysis, content, params, vulnscan, takeover, cloud,
)

# Pipeline order. `tas all` runs these top to bottom.
PIPELINE = [
    dns_passive, dns_active, httpprobe, portscan, crawl,
    jsanalysis, content, params, vulnscan, takeover, cloud,
]
MODULES = {m.NAME: m for m in PIPELINE}


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("target", help="domain (example.com) or a file of targets/hosts/URLs")
    p.add_argument("-o", "--output", help="output root dir (default: output/<target>)")
    p.add_argument("-c", "--config", help="path to config.yaml")
    p.add_argument("-i", "--input", help="explicit input file for this stage (overrides upstream)")
    p.add_argument("--threads", type=int, help="override concurrency")
    p.add_argument("--delay", type=int, help="override per-request delay (ms)")
    p.add_argument("--rate", type=int, help="override requests/second cap")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tas", description="Target Attack Surface, modular recon toolset")
    ap.add_argument("--version", action="version", version=f"TAS {__version__}")
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    for name, mod in MODULES.items():
        sp = sub.add_parser(name, help=mod.HELP)
        _add_common(sp)
        if hasattr(mod, "add_args"):
            mod.add_args(sp)

    ap_all = sub.add_parser("all", help="run the full pipeline in order")
    _add_common(ap_all)
    ap_all.add_argument("--only", help="comma-separated stages to run (default: all)")
    ap_all.add_argument("--skip", help="comma-separated stages to skip")

    sub.add_parser("list", help="list available stages in pipeline order")

    sp_doc = sub.add_parser("doctor", help="check which tools are installed")
    sp_doc.add_argument("-c", "--config", help="path to config.yaml")

    sp_inst = sub.add_parser("install", help="install/update the underlying tools")
    sp_inst.add_argument("rest", nargs=argparse.REMAINDER,
                         help="passed to install/install.py")
    return ap


def _make_ctx(args) -> Context:
    cfg = load_config(getattr(args, "config", None))
    label = Path(args.target).stem if Path(args.target).exists() else args.target
    label = label.replace("/", "_").replace(":", "_")
    root = Path(args.output) if args.output else Path(cfg["output_dir"]) / label
    return Context(args.target, root, cfg, args)


def _run_stage(mod, ctx) -> None:
    stage_banner(mod.NAME)
    try:
        mod.run(ctx)
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001
        err(f"stage '{mod.NAME}' errored: {e}")


def cmd_all(args) -> int:
    ctx = _make_ctx(args)
    only = set(s.strip() for s in args.only.split(",")) if args.only else None
    skip = set(s.strip() for s in args.skip.split(",")) if args.skip else set()
    info(f"target: {ctx.target}")
    info(f"output: {ctx.outdir}")
    info(f"rate: {ctx.threads} threads, {ctx.delay_ms}ms delay, {ctx.rate_limit} req/s cap")
    for mod in PIPELINE:
        if only and mod.NAME not in only:
            continue
        if mod.NAME in skip:
            info(f"skipping {mod.NAME}")
            continue
        _run_stage(mod, ctx)
    good(f"done. results under {ctx.outdir}")
    return 0


def cmd_single(name, args) -> int:
    ctx = _make_ctx(args)
    info(f"target: {ctx.target}  output: {ctx.outdir}")
    _run_stage(MODULES[name], ctx)
    good(f"done. results under {ctx.outdir}")
    return 0


def cmd_list() -> int:
    print("Pipeline order:")
    for i, mod in enumerate(PIPELINE, 1):
        print(f"  {i:>2}. {mod.NAME:<12} {mod.HELP}")
    return 0


def cmd_doctor(args) -> int:
    cfg = load_config(getattr(args, "config", None))
    tools = cfg.get("tools", {})
    missing = []
    print("Tool status:")
    for key, meta in tools.items():
        b = (meta or {}).get("bin", key)
        ok = have(b)
        print(f"  [{'OK ' if ok else '-- '}] {key:<12} ({b})")
        if not ok:
            missing.append(key)
    if missing:
        warn(f"{len(missing)} missing: {', '.join(missing)}")
        warn("install with: python tas.py install")
    else:
        good("all tools present")
    return 0


def cmd_install(args) -> int:
    import subprocess
    script = Path(__file__).resolve().parent.parent / "install" / "install.py"
    return subprocess.run([sys.executable, str(script), *args.rest]).returncode


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.command:
        build_parser().print_help()
        return 1
    if args.command == "all":
        return cmd_all(args)
    if args.command == "list":
        return cmd_list()
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "install":
        return cmd_install(args)
    if args.command in MODULES:
        return cmd_single(args.command, args)
    err(f"unknown command: {args.command}")
    return 1
