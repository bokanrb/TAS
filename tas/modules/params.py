"""Parameter discovery with Arjun. ffuf is available as a fuzzer too.

Arjun finds hidden query/body params on endpoints. Throttle via --stable and
its delay. Reads live URLs (or crawl output).
"""
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, warn, info

NAME = "params"
HELP = "hidden parameter discovery (arjun)"


def add_args(parser):
    parser.add_argument("--urls-from", choices=["live", "urls"], default="live",
                        help="which upstream list to test (default live)")


def run(ctx):
    src = ctx.input_file(getattr(ctx.args, "urls_from", "live"), "live", "urls")
    if not src:
        warn(f"{NAME}: no input URLs. Run httpprobe or crawl first, or pass --input")
        return
    out = ctx.out(NAME, "arjun.json")
    cmd = [tool_bin(ctx, "arjun"), "-i", src, "-oJ", out,
           "-t", ctx.threads, "--stable"]
    # Arjun delay is in seconds between requests
    cmd += ["-d", str(ctx.delay_ms / 1000)]
    cmd += tool_extra(ctx, "arjun")
    if run_tool(cmd) is not None:
        ctx.set("params", out)
        good(f"{NAME}: parameters -> {out}")
    else:
        info("arjun missing. Alternative: ffuf with a params wordlist (see docs/USAGE.md)")
