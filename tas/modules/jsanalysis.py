"""JS / content analysis: jsluice (URLs+secrets from JS) + trufflehog (secrets).

Operates on URLs already collected by crawl. jsluice needs the JS fetched, so
it reads the URL list and fetches, or analyses local files via --input.
trufflehog scans for verified secrets.
"""
from ..common import run, tool_bin, tool_extra, read_lines, good, info, have, warn

NAME = "jsanalysis"
HELP = "extract endpoints/secrets from JS (jsluice + trufflehog)"


def run(ctx):
    urls = ctx.input_file("urls", "live")
    if not urls:
        warn(f"{NAME}: no URL list. Run crawl first or pass --input")
        return
    js = [u for u in read_lines(urls) if u.split("?")[0].endswith(".js")]
    jsfile = ctx.out(NAME, "js_urls.txt")
    jsfile.write_text("\n".join(js) + "\n")
    info(f"{NAME}: {len(js)} JS URLs")

    # jsluice reads URLs on stdin: `jsluice urls -R <url>` / `jsluice secrets`.
    # Simplest portable path: feed the JS URL list to jsluice retrieve mode.
    if have(tool_bin(ctx, "jsluice")) and js:
        out = ctx.out(NAME, "jsluice.jsonl")
        # jsluice format <files>. We pass URLs via -R where supported.
        run([tool_bin(ctx, "jsluice"), "urls", "-R", jsfile] + tool_extra(ctx, "jsluice"),
            stdout_to=out)
        ctx.set("js_endpoints", out)
        good(f"{NAME}: jsluice endpoints -> {out}")

    # trufflehog over the crawled URLs' host (filesystem/ git modes also available)
    if have(tool_bin(ctx, "trufflehog")):
        sec = ctx.out(NAME, "secrets.jsonl")
        # scan a local export dir if provided via --input dir, otherwise note guidance
        info(f"{NAME}: run trufflehog on fetched JS or repos. See docs/USAGE.md")
        run([tool_bin(ctx, "trufflehog"), "filesystem", str(jsfile.parent),
             "--json", "--no-update"] + tool_extra(ctx, "trufflehog"), stdout_to=sec)
        ctx.set("secrets", sec)
