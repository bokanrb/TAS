"""Crawling + passive URL collection: katana (active) + urlfinder (passive).

katana crawls live sites (honours rate/depth). urlfinder pulls known URLs from
archives/passive sources. Outputs a merged, de-duplicated URL list.
"""
from ..common import run, tool_bin, tool_extra, read_lines, good

NAME = "crawl"
HELP = "crawl live sites + passive URLs (katana + urlfinder)"


def add_args(parser):
    parser.add_argument("--depth", type=int, default=2, help="katana crawl depth (default 2)")
    parser.add_argument("--js-crawl", action="store_true",
                        help="enable katana JS endpoint parsing (-jc)")
    parser.add_argument("--no-passive", action="store_true", help="skip urlfinder")


def run(ctx):
    src = ctx.input_file("live", "resolved") or ctx.target_file()
    sd = ctx.stage_dir(NAME)
    kout = sd / "katana.txt"
    uout = sd / "urlfinder.txt"

    cmd = [tool_bin(ctx, "katana"), "-silent", "-list", src,
           "-d", getattr(ctx.args, "depth", 2),
           "-c", ctx.threads, "-rl", ctx.rate_limit, "-delay", ctx.delay_s(),
           "-o", kout]
    if getattr(ctx.args, "js_crawl", False):
        cmd.append("-jc")
    cmd += tool_extra(ctx, "katana")
    run(cmd)

    if not getattr(ctx.args, "no_passive", False):
        run([tool_bin(ctx, "urlfinder"), "-silent", "-list", src, "-o", uout]
            + tool_extra(ctx, "urlfinder"))

    merged = sorted(set(read_lines(kout)) | set(read_lines(uout)))
    out = ctx.out(NAME, "urls.txt")
    out.write_text("\n".join(merged) + "\n")
    ctx.set("urls", out)
    good(f"{NAME}: {len(merged)} unique URLs -> {out}")
