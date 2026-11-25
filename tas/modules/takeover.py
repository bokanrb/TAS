"""Subdomain takeover detection with nuclei takeover templates.

Feeds the resolved host list (ideally with CNAMEs from dns_active) to nuclei's
takeover template set. A hit still needs manual confirmation and the DNS and
CNAME chain recorded as evidence.
"""
from ..common import run, tool_bin, tool_extra, read_lines, good, warn

NAME = "takeover"
HELP = "subdomain takeover checks (nuclei -tags takeover)"


def run(ctx):
    src = ctx.input_file("resolved", "subdomains", "live")
    if not src:
        warn(f"{NAME}: no host list. Run the dns stages first or pass --input")
        return
    out = ctx.out(NAME, "takeover.jsonl")
    cmd = [tool_bin(ctx, "nuclei"), "-silent", "-l", src,
           "-tags", "takeover", "-rl", ctx.rate_limit, "-c", ctx.threads,
           "-jsonl", "-o", out]
    cmd += tool_extra(ctx, "nuclei")
    if run(cmd) is not None:
        ctx.set("takeover", out)
        n = len(read_lines(out))
        (good if n else warn)(f"{NAME}: {n} potential takeover(s) -> {out}")
