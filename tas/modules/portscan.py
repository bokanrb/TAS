"""Port scanning with naabu (throttled), optional nmap service scan on hits.

naabu throttling: -rate (packets/sec) and -c (concurrency). Connect scan
(-scan-type c) needs no root or Npcap. SYN scan needs privileges.
Note: web targets are commonly limited to 80 and 443. Only widen ports when
the target's rules allow it.
"""
from ..common import run, tool_bin, tool_extra, read_lines, have, good, info, warn

NAME = "portscan"
HELP = "port scan with throttle (naabu), optional nmap on open ports"


def add_args(parser):
    parser.add_argument("--ports", default="80,443",
                        help="ports or range (default 80,443, e.g. top-100 or 1-65535)")
    parser.add_argument("--syn", action="store_true",
                        help="SYN scan (needs root or Npcap), default is connect scan")
    parser.add_argument("--nmap", action="store_true",
                        help="run nmap -sV on discovered host:port pairs")


def run(ctx):
    src = ctx.input_file("resolved", "subdomains") or ctx.target_file()
    out = ctx.out(NAME, "ports.txt")
    ports = getattr(ctx.args, "ports", "80,443")

    cmd = [tool_bin(ctx, "naabu"), "-silent", "-l", src,
           "-c", ctx.threads, "-rate", ctx.rate_limit,
           "-scan-type", "s" if getattr(ctx.args, "syn", False) else "c",
           "-o", out]
    if ports in ("top-100", "top-1000", "full"):
        cmd += {"top-100": ["-top-ports", "100"], "top-1000": ["-top-ports", "1000"],
                "full": ["-p", "-"]}[ports]
    else:
        cmd += ["-p", ports]
    cmd += tool_extra(ctx, "naabu")
    if run(cmd) is not None:
        ctx.set("ports", out)
        good(f"{NAME}: {len(read_lines(out))} open host:port -> {out}")

    if getattr(ctx.args, "nmap", False) and read_lines(out):
        if not have("nmap"):
            warn("nmap not installed, skipping the service scan")
            return
        info(f"{NAME}: nmap -sV on discovered ports (slow)")
        run(["nmap", "-sV", "--open", "-Pn", "-iL", out, "-oN", ctx.out(NAME, "nmap.txt")],
            check_tool=False)
