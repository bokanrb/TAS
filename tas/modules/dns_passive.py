"""Passive subdomain enumeration with subfinder.

Passive means third party data sources only. It does not touch the target.
API keys (if configured in config/provider-config.yaml) add more sources.
"""
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, info

NAME = "dns_passive"
HELP = "passive subdomain enumeration (subfinder)"


def add_args(parser):
    parser.add_argument("--all-sources", action="store_true",
                        help="use all subfinder sources (-all), slower")


def run(ctx):
    import os
    out = ctx.out(NAME, "subdomains.txt")
    cmd = [tool_bin(ctx, "subfinder"), "-silent", "-rl", ctx.rate_limit, "-o", out]
    if getattr(ctx.args, "all_sources", False):
        cmd.append("-all")
    # subfinder takes -d domain, or -dL file
    if os.path.exists(ctx.target):
        cmd += ["-dL", ctx.target]
    else:
        cmd += ["-d", ctx.target]
    cmd += tool_extra(ctx, "subfinder")
    rc = run_tool(cmd)
    if rc is not None:
        ctx.set("subdomains", out)
        good(f"{NAME}: {len(read_lines(out))} subdomains -> {out}")
