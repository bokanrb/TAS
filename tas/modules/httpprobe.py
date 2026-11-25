"""HTTP probing and fingerprinting: httpx (core) + tlsx + cdncheck + wafw00f.

Produces the live URL list every later web stage depends on.
Default ports 80 and 443 only. Widen with --ports when you are allowed to.
"""
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, info

NAME = "httpprobe"
HELP = "HTTP probe + tech/TLS/CDN/WAF fingerprint (httpx, tlsx, cdncheck, wafw00f)"


def add_args(parser):
    parser.add_argument("--ports", default="80,443",
                        help="ports for httpx (default 80,443)")


def _input(ctx):
    return ctx.input_file("resolved", "subdomains") or ctx.target_file()


def run(ctx):
    src = _input(ctx)
    live = ctx.out(NAME, "live.txt")
    hjson = ctx.out(NAME, "httpx.jsonl")

    cmd = [tool_bin(ctx, "httpx"), "-silent", "-l", src,
           "-ports", getattr(ctx.args, "ports", "80,443"),
           "-threads", ctx.threads, "-rl", ctx.rate_limit, "-delay", ctx.delay_s(),
           "-td", "-title", "-sc", "-ip", "-json", "-o", hjson]
    cmd += tool_extra(ctx, "httpx")
    if run_tool(cmd) is not None:
        # plain live URL list for downstream stages
        run_tool([tool_bin(ctx, "httpx"), "-silent", "-l", src,
             "-ports", getattr(ctx.args, "ports", "80,443"),
             "-threads", ctx.threads, "-rl", ctx.rate_limit], stdout_to=live)
        ctx.set("live", live)
        ctx.set("httpx_json", hjson)
        good(f"{NAME}: {len(read_lines(live))} live endpoints -> {live}")

    # TLS SANs can reveal extra hostnames
    run_tool([tool_bin(ctx, "tlsx"), "-silent", "-l", src, "-san", "-cn", "-json",
         "-o", ctx.out(NAME, "tls.jsonl")] + tool_extra(ctx, "tlsx"))

    # CDN/WAF IP classification
    if run_tool([tool_bin(ctx, "cdncheck"), "-silent", "-resp", "-j",
            "-o", ctx.out(NAME, "cdncheck.jsonl")] + tool_extra(ctx, "cdncheck"),
           ) is not None:
        pass

    # WAF fingerprint on live URLs (wafw00f reads one target or stdin)
    live_urls = read_lines(live)
    if live_urls:
        waf = ctx.out(NAME, "wafw00f.json")
        run_tool([tool_bin(ctx, "wafw00f"), *live_urls[:50], "-f", "json", "-o", waf]
            + tool_extra(ctx, "wafw00f"))
        info(f"{NAME}: WAF fingerprint on up to 50 live URLs -> {waf}")
