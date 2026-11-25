#!/usr/bin/env python3
"""Cross-platform installer for the TAS toolchain (macOS + Windows + Linux).

Strategy:
  ProjectDiscovery tools go through `go install` if Go is present, otherwise a
  pdtm release binary from github.com. jsluice and trufflehog use `go install`.
  feroxbuster uses a GitHub release binary. arjun, wafw00f and s3scanner use
  pip. cloud_enum is a git clone. Wordlists come from raw.githubusercontent.com.

Each step is best effort and independent. A summary prints at the end with
manual instructions for anything that failed. Nothing here touches a target.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOPATH_BIN = Path(os.environ.get("GOBIN") or (Path(os.environ.get("GOPATH", Path.home() / "go")) / "bin"))

PD_TOOLS = {
    "subfinder": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "dnsx": "github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    "alterx": "github.com/projectdiscovery/alterx/cmd/alterx@latest",
    "naabu": "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
    "httpx": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "tlsx": "github.com/projectdiscovery/tlsx/cmd/tlsx@latest",
    "cdncheck": "github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest",
    "katana": "github.com/projectdiscovery/katana/cmd/katana@latest",
    "urlfinder": "github.com/projectdiscovery/urlfinder/cmd/urlfinder@latest",
    "nuclei": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "uncover": "github.com/projectdiscovery/uncover/cmd/uncover@latest",
}
GO_TOOLS = {
    "jsluice": "github.com/BishopFox/jsluice/cmd/jsluice@latest",
    "trufflehog": "github.com/trufflesecurity/trufflehog/v3@latest",
}
PIP_TOOLS = ["arjun", "wafw00f", "s3scanner"]

WORDLISTS = {
    "dns/subdomains.txt":
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt",
    "content/raft-medium-directories.txt":
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-directories.txt",
    "content/raft-medium-files.txt":
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-files.txt",
    "params/parameters.txt":
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/burp-parameter-names.txt",
}

results: list[tuple[str, bool, str]] = []


def record(name, ok, note=""):
    results.append((name, ok, note))
    tag = "OK " if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f"  {note}" if note else ""))


def have(b):
    return shutil.which(b) is not None


def sh(cmd, env=None):
    print("  $ " + " ".join(cmd))
    return subprocess.run(cmd, env=env).returncode == 0


def install_go_tool(name, pkg):
    if have(name):
        record(name, True, "already on PATH")
        return
    if not have("go"):
        record(name, False, "needs Go. Install Go or use pdtm binaries")
        return
    ok = sh(["go", "install", "-v", pkg])
    if ok and not have(name) and GOPATH_BIN.exists():
        note = f"installed to {GOPATH_BIN}, add it to PATH"
        record(name, True, note)
    else:
        record(name, ok)


def install_pd():
    print("\n[*] ProjectDiscovery suite")
    for name, pkg in PD_TOOLS.items():
        install_go_tool(name, pkg)


def install_go_extras():
    print("\n[*] Other Go tools")
    for name, pkg in GO_TOOLS.items():
        install_go_tool(name, pkg)


def install_pip():
    print("\n[*] Python tools (pip)")
    for name in PIP_TOOLS:
        if have(name):
            record(name, True, "already on PATH")
            continue
        ok = sh([sys.executable, "-m", "pip", "install", "--user", "--upgrade", name])
        record(name, ok)


def install_cloud_enum():
    print("\n[*] cloud_enum (git clone)")
    dest = REPO / "install" / "vendor" / "cloud_enum"
    if dest.exists():
        record("cloud_enum", True, f"already cloned at {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    ok = sh(["git", "clone", "--depth", "1",
             "https://github.com/initstring/cloud_enum.git", str(dest)])
    record("cloud_enum", ok, f"run via {dest}/cloud_enum.py, add a wrapper to PATH")


def install_feroxbuster():
    print("\n[*] feroxbuster")
    if have("feroxbuster"):
        record("feroxbuster", True, "already on PATH")
        return
    record("feroxbuster", False,
           "install from a GitHub release binary for your OS: "
           "https://github.com/epi052/feroxbuster/releases  (or `brew install feroxbuster`)")


def fetch_wordlists():
    print("\n[*] Wordlists")
    wl_root = REPO / "wordlists"
    for rel, url in WORDLISTS.items():
        dest = wl_root / rel
        if dest.exists() and dest.stat().st_size > 0:
            record(rel, True, "already present")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            print(f"  downloading {rel}")
            urllib.request.urlretrieve(url, dest)
            record(rel, dest.stat().st_size > 0)
        except Exception as e:  # noqa: BLE001
            record(rel, False, str(e))


def summary():
    print("\n" + "=" * 60)
    ok = sum(1 for _, s, _ in results if s)
    print(f"Summary: {ok}/{len(results)} steps OK")
    failed = [(n, note) for n, s, note in results if not s]
    if failed:
        print("\nNeeds attention:")
        for n, note in failed:
            print(f"  - {n}: {note}")
    print(f"\nTip: ensure {GOPATH_BIN} is on your PATH, then run: python tas.py doctor")


def main():
    ap = argparse.ArgumentParser(description="Install the TAS toolchain")
    ap.add_argument("--wordlists", action="store_true", help="only fetch wordlists")
    ap.add_argument("--tools", action="store_true", help="only install tools")
    args = ap.parse_args()
    print(f"TAS installer. {platform.system()} {platform.machine()}, python {sys.version.split()[0]}")

    do_tools = not args.wordlists or args.tools
    do_wl = not args.tools or args.wordlists

    if do_tools:
        install_pd()
        install_go_extras()
        install_pip()
        install_cloud_enum()
        install_feroxbuster()
    if do_wl:
        fetch_wordlists()
    summary()


if __name__ == "__main__":
    main()
