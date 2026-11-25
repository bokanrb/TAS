"""Active DNS: permutation + wordlist bruteforce, then resolution (dnsx, alterx).

Active = sends DNS queries that ultimately reach the target's name servers.
Produces resolved live hostnames and a JSON of DNS records (incl. CNAMEs,
which the takeover stage consumes).
"""
import os
from ..common import run as run_tool, tool_bin, tool_extra, read_lines, good, warn, info

NAME = "dns_active"
HELP = "active DNS bruteforce + resolution (dnsx + alterx)"


def add_args(parser):
    parser.add_argument("--no-brute", action="store_true",
                        help="resolve known subdomains only, skip wordlist bruteforce")
    parser.add_argument("--no-permute", action="store_true",
                        help="skip alterx permutation of known subdomains")


def run(ctx):
    sd = ctx.stage_dir(NAME)
    known = ctx.input_file("subdomains")  # from dns_passive, or --input
    candidates = sd / "candidates.txt"
    seen = set()

    def add(lines):
        for l in lines:
            if l and l not in seen:
                seen.add(l)

    if known:
        add(read_lines(known))

    # permutations of known subdomains
    if known and not getattr(ctx.args, "no_permute", False):
        perm = sd / "permutations.txt"
        if run_tool([tool_bin(ctx, "alterx"), "-silent", "-l", known, "-o", perm]) is not None:
            add(read_lines(perm))

    # wordlist bruteforce candidates: <word>.<target>
    if not getattr(ctx.args, "no_brute", False) and not os.path.exists(ctx.target):
        wl = ctx.wordlist("dns")
        if wl.exists():
            add(f"{w}.{ctx.target}" for w in read_lines(wl))
        else:
            warn(f"DNS wordlist missing: {wl} (run: python tas.py install --wordlists)")

    if not seen:
        add(read_lines(ctx.target_file()))
    candidates.write_text("\n".join(sorted(seen)) + "\n")
    info(f"{NAME}: {len(seen)} candidate names to resolve")

    resolved = ctx.out(NAME, "resolved.txt")
    recs = ctx.out(NAME, "dns_records.jsonl")
    cmd = [tool_bin(ctx, "dnsx"), "-silent", "-l", candidates,
           "-rl", ctx.rate_limit, "-t", ctx.threads,
           "-a", "-cname", "-resp", "-j", "-o", recs]
    cmd += tool_extra(ctx, "dnsx")
    if run_tool(cmd) is not None:
        # also a plain resolved host list
        plain = [tool_bin(ctx, "dnsx"), "-silent", "-l", candidates, "-rl", ctx.rate_limit, "-t", ctx.threads]
        run_tool(plain, stdout_to=resolved)
        ctx.set("resolved", resolved)
        ctx.set("dns_records", recs)
        good(f"{NAME}: {len(read_lines(resolved))} resolved -> {resolved}")
