"""Content / directory discovery with feroxbuster (throttled, recursive).

Throttle: --threads and --rate-limit. Uses the content wordlist from config.
Runs against each live URL (or the target).
"""
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, warn

NAME = "content"
HELP = "directory/content discovery (feroxbuster)"


def add_args(parser):
    parser.add_argument("--depth", type=int, default=2, help="recursion depth (default 2)")
    parser.add_argument("--wordlist", help="override content wordlist path")


def run(ctx):
    src = ctx.input_file("live")
    targets = read_lines(src) if src else [ctx.target
                                           if ctx.target.startswith("http") else f"https://{ctx.target}"]
    wl = getattr(ctx.args, "wordlist", None) or ctx.wordlist("content")
    from pathlib import Path
    if not Path(wl).exists():
        warn(f"content wordlist missing: {wl} (run: python tas.py install --wordlists)")
        return
    out = ctx.out(NAME, "feroxbuster.jsonl")
    cmd = [tool_bin(ctx, "feroxbuster"), "--silent", "--json",
           "--threads", ctx.threads, "--rate-limit", ctx.rate_limit,
           "--depth", getattr(ctx.args, "depth", 2),
           "-w", wl, "--output", out]
    # feroxbuster takes repeated -u, or --stdin
    if len(targets) == 1:
        cmd += ["-u", targets[0]]
        rc = run_tool(cmd + tool_extra(ctx, "feroxbuster"))
    else:
        import subprocess, sys
        from ..common import have, info
        if not have(tool_bin(ctx, "feroxbuster")):
            warn("feroxbuster not found, skipping")
            return
        info("$ feroxbuster --stdin (one line per live URL)")
        rc = subprocess.run(cmd + ["--stdin"] + tool_extra(ctx, "feroxbuster"),
                            input="\n".join(targets), text=True).returncode
    if rc is not None:
        ctx.set("content", out)
        good(f"{NAME}: results -> {out}")
