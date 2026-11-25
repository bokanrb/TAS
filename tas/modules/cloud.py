"""Cloud asset / bucket discovery: cloud_enum (multi-cloud) + s3scanner.

cloud_enum sweeps AWS, Azure and GCP for named assets from a keyword. s3scanner
validates and enumerates buckets. Only act on storage you are authorized to
test.
"""
import os
from ..common import run, tool_bin, tool_extra, good, info, have, warn

NAME = "cloud"
HELP = "cloud asset + bucket discovery (cloud_enum + s3scanner)"


def add_args(parser):
    parser.add_argument("--keyword", help="company/asset keyword (default: target label)")


def run(ctx):
    kw = getattr(ctx.args, "keyword", None) or (
        ctx.target if not os.path.exists(ctx.target) else "")
    if not kw:
        warn(f"{NAME}: pass --keyword for a target file")
        return
    base = kw.split(".")[0]

    if have(tool_bin(ctx, "cloud_enum")):
        out = ctx.out(NAME, "cloud_enum.txt")
        run([tool_bin(ctx, "cloud_enum"), "-k", base, "-k", kw, "-l", out]
            + tool_extra(ctx, "cloud_enum"))
        ctx.set("cloud_assets", out)
        good(f"{NAME}: cloud_enum -> {out}")
    else:
        warn("cloud_enum not found, skipping the cloud sweep")

    if have(tool_bin(ctx, "s3scanner")):
        out = ctx.out(NAME, "s3scanner.txt")
        run([tool_bin(ctx, "s3scanner"), "scan", "-bucket", base,
             "--json"] + tool_extra(ctx, "s3scanner"), stdout_to=out)
        info(f"{NAME}: s3scanner -> {out}")
