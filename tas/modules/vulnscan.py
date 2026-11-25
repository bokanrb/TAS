"""Vulnerability scanning with nuclei (curated, throttled).

Defaults are deliberately conservative. Config appends -duc -ni (no auto update
check, no interactsh). Pick templates with --tags or --templates. A broad run
is noisy and slow, so curate what you actually need.
"""
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, warn

NAME = "vulnscan"
HELP = "template vuln scan (nuclei), curate your templates"


def add_args(parser):
    parser.add_argument("--tags", help="nuclei -tags (e.g. exposure,misconfig,cve)")
    parser.add_argument("--templates", help="path to a curated template dir/file (-t)")
    parser.add_argument("--severity", default="medium,high,critical",
                        help="nuclei -severity (default medium,high,critical)")


def run(ctx):
    src = ctx.input_file("live", "urls")
    if not src:
        warn(f"{NAME}: no live URLs. Run httpprobe first or pass --input")
        return
    out = ctx.out(NAME, "nuclei.jsonl")
    cmd = [tool_bin(ctx, "nuclei"), "-silent", "-l", src,
           "-rl", ctx.rate_limit, "-c", ctx.threads,
           "-severity", getattr(ctx.args, "severity", "medium,high,critical"),
           "-jsonl", "-o", out]
    if getattr(ctx.args, "tags", None):
        cmd += ["-tags", ctx.args.tags]
    if getattr(ctx.args, "templates", None):
        cmd += ["-t", ctx.args.templates]
    cmd += tool_extra(ctx, "nuclei")  # -duc -ni from config
    if run_tool(cmd) is not None:
        ctx.set("vulns", out)
        good(f"{NAME}: {len(read_lines(out))} findings -> {out}")
