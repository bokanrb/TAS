#!/usr/bin/env python3
"""Cross platform installer for the TAS toolchain (macOS, Linux, Windows).

How each tool is installed:
  ProjectDiscovery suite and jsluice use `go install` (needs Go).
  trufflehog and feroxbuster are fetched as release binaries from GitHub,
  matched to this OS and CPU by querying the releases API (no guessed names).
  arjun, wafw00f and s3scanner install with pipx if present, else pip --user.
  cloud_enum is cloned and installed as a package (pipx if present, else pip).
  Wordlists download from raw.githubusercontent.com.

Every step is best effort and independent. A summary prints at the end with
manual instructions for anything that failed. Nothing here touches a target.

Run `python install/install.py` for everything, `--wordlists` for lists only,
`--tools` for tools only, or `--check` to only run the preflight check.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
BIN_DIR = HOME / ".local" / "bin"   # where release binaries land (also pipx's dir)
GOPATH_BIN = Path(os.environ.get("GOBIN") or (Path(os.environ.get("GOPATH", HOME / "go")) / "bin"))
IS_WINDOWS = platform.system() == "Windows"
EXE = ".exe" if IS_WINDOWS else ""

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
}
# Release binaries fetched from GitHub (repo and the binary name inside the archive)
RELEASE_TOOLS = {
    "trufflehog": "trufflesecurity/trufflehog",
    "feroxbuster": "epi052/feroxbuster",
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
    print(f"  [{'OK  ' if ok else 'FAIL'}] {name}" + (f"  {note}" if note else ""))


def have(b):
    return shutil.which(b) is not None


def sh(cmd):
    print("  $ " + " ".join(str(c) for c in cmd))
    try:
        return subprocess.run([str(c) for c in cmd]).returncode == 0
    except FileNotFoundError:
        return False


# ------------------------------------------------------------- platform ------
def platform_tokens():
    """Return (os_tokens, arch_tokens) used to match a release asset."""
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    if sysname == "darwin":
        os_tokens = ["darwin", "macos", "apple", "osx"]
    elif sysname == "linux":
        os_tokens = ["linux"]
    elif sysname == "windows":
        os_tokens = ["windows", "win"]
    else:
        os_tokens = [sysname]
    if machine in ("arm64", "aarch64"):
        arch_tokens = ["arm64", "aarch64"]
    elif machine in ("x86_64", "amd64", "x64"):
        arch_tokens = ["amd64", "x86_64", "x64"]
    else:
        arch_tokens = [machine]
    return os_tokens, arch_tokens


# -------------------------------------------------------------- download -----
def http_get(url, binary=True):
    req = urllib.request.Request(url, headers={"User-Agent": "tas-installer"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read() if binary else r.read().decode()


def github_latest_assets(repo):
    data = json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest", binary=False))
    return data["tag_name"], [(a["name"], a["browser_download_url"]) for a in data["assets"]]


def pick_asset(assets, os_tokens, arch_tokens):
    bad = (".sha256", ".txt", ".pem", ".sig", ".asc", ".deb", ".rpm", ".msi", ".pkg")
    pref = (".tar.gz", ".tgz", ".zip")
    cands = []
    for name, url in assets:
        low = name.lower()
        if any(low.endswith(b) or b + "." in low for b in bad):
            continue
        if not any(a in low for a in arch_tokens):
            continue
        if not any(o in low for o in os_tokens):
            continue
        score = next((len(pref) - i for i, e in enumerate(pref) if low.endswith(e)), 0)
        cands.append((score, name, url))
    cands.sort(reverse=True)
    return (cands[0][1], cands[0][2]) if cands else (None, None)


def extract_binary(archive_bytes, name, bin_name, dest):
    """Extract bin_name (or bin_name.exe) from a .tar.gz/.zip in memory to dest."""
    wanted = {bin_name.lower(), (bin_name + ".exe").lower()}
    dest.parent.mkdir(parents=True, exist_ok=True)
    if name.lower().endswith((".tar.gz", ".tgz")):
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
            for m in tf.getmembers():
                if Path(m.name).name.lower() in wanted:
                    with tf.extractfile(m) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out)
                    return True
    elif name.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            for n in zf.namelist():
                if Path(n).name.lower() in wanted:
                    with zf.open(n) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out)
                    return True
    return False


# --------------------------------------------------------------- go ----------
def install_go_tool(name, pkg):
    if have(name):
        record(name, True, "already on PATH")
        return
    if not have("go"):
        record(name, False, "needs Go. Install Go, then re run this")
        return
    ok = sh(["go", "install", "-v", pkg])
    if ok and not have(name) and GOPATH_BIN.exists():
        record(name, True, f"installed to {GOPATH_BIN}, make sure it is on PATH")
    else:
        record(name, ok)


# -------------------------------------------------------- release binaries ---
def install_release_tool(name, repo):
    if have(name):
        record(name, True, "already on PATH")
        return
    try:
        tag, assets = github_latest_assets(repo)
        os_tokens, arch_tokens = platform_tokens()
        asset_name, url = pick_asset(assets, os_tokens, arch_tokens)
        if not url:
            record(name, False, f"no matching {tag} asset for this OS/CPU. See github.com/{repo}/releases")
            return
        print(f"  downloading {asset_name}")
        blob = http_get(url, binary=True)
        dest = BIN_DIR / (name + EXE)
        if extract_binary(blob, asset_name, name, dest):
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            record(name, True, f"installed to {dest}")
        else:
            record(name, False, f"binary not found inside {asset_name}")
    except Exception as e:  # noqa: BLE001
        record(name, False, f"{e}. Manual: github.com/{repo}/releases")


# ------------------------------------------------------------- python --------
def install_python_tool(name, spec=None):
    spec = spec or name
    if have(name):
        record(name, True, "already on PATH")
        return
    if have("pipx"):
        record(name, sh(["pipx", "install", spec]))
    else:
        ok = sh([sys.executable, "-m", "pip", "install", "--user", "--upgrade", spec])
        record(name, ok, "" if ok else "pip --user failed, consider installing pipx")


def install_cloud_enum():
    if have("cloud_enum"):
        record("cloud_enum", True, "already on PATH")
        return
    dest = REPO / "install" / "vendor" / "cloud_enum"
    if not dest.exists():
        if not sh(["git", "clone", "--depth", "1",
                   "https://github.com/initstring/cloud_enum.git", str(dest)]):
            record("cloud_enum", False, "git clone failed")
            return
    install_python_tool("cloud_enum", str(dest))


# ------------------------------------------------------------ wordlists ------
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
            dest.write_bytes(http_get(url, binary=True))
            record(rel, dest.stat().st_size > 0)
        except Exception as e:  # noqa: BLE001
            record(rel, False, str(e))


# ------------------------------------------------------------- preflight -----
def preflight():
    print("[*] Preflight")
    ok = True
    pyver = sys.version_info
    py_ok = pyver >= (3, 9)
    record(f"python {pyver.major}.{pyver.minor}", py_ok, "" if py_ok else "need Python 3.9 or newer")
    ok &= py_ok
    for tool, why in [("git", "needed for cloud_enum and updates"),
                      ("go", "needed for subfinder/httpx/nuclei and the rest of the Go tools")]:
        present = have(tool)
        record(tool, present, "" if present else f"not found. {why}")
        ok &= present or tool == "go"  # go is strongly recommended, not strictly fatal
    if not have("pipx"):
        record("pipx", False, "not found. pip --user will be used instead (pipx is cleaner)")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    on_path = str(BIN_DIR) in os.environ.get("PATH", "")
    record(f"PATH has {BIN_DIR}", on_path, "" if on_path else "add this dir to PATH for installed tools")
    return ok


def summary():
    print("\n" + "=" * 64)
    ok = sum(1 for _, s, _ in results if s)
    print(f"Summary: {ok}/{len(results)} steps OK")
    failed = [(n, note) for n, s, note in results if not s]
    if failed:
        print("\nNeeds attention:")
        for n, note in failed:
            print(f"  - {n}: {note}")
    print(f"\nMake sure {BIN_DIR} and {GOPATH_BIN} are on PATH, then: python tas.py doctor")


def main():
    ap = argparse.ArgumentParser(description="Install the TAS toolchain")
    ap.add_argument("--wordlists", action="store_true", help="only fetch wordlists")
    ap.add_argument("--tools", action="store_true", help="only install tools")
    ap.add_argument("--check", action="store_true", help="only run the preflight check")
    args = ap.parse_args()
    print(f"TAS installer. {platform.system()} {platform.machine()}, python {sys.version.split()[0]}")

    preflight()
    if args.check:
        summary()
        return

    do_tools = not args.wordlists or args.tools
    do_wl = not args.tools or args.wordlists

    if do_tools:
        print("\n[*] ProjectDiscovery suite and jsluice (go install)")
        for name, pkg in {**PD_TOOLS, **GO_TOOLS}.items():
            install_go_tool(name, pkg)
        print("\n[*] Release binaries (trufflehog, feroxbuster)")
        for name, repo in RELEASE_TOOLS.items():
            install_release_tool(name, repo)
        print("\n[*] Python tools")
        for name in PIP_TOOLS:
            install_python_tool(name)
        install_cloud_enum()
    if do_wl:
        fetch_wordlists()
    summary()


if __name__ == "__main__":
    main()
