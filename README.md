# TAS, Target Attack Surface

A recon and enumeration environment. One setup script installs a curated set of
tools and wordlists. After that you run each tool directly, however you like.
There is no wrapper or launcher, just the tools on your PATH and the wordlists
in one place.

> For authorized testing only. Test only assets you own or have written
> permission to test. See `docs/SCOPE.md`.

## Prerequisites

Install these first. The setup script checks for them and reports what is
missing.

| Requirement | Why |
|---|---|
| Go 1.21+ | builds the ProjectDiscovery suite, ffuf and jsluice via `go install` |
| git | used by some installs and updates |
| Python 3.9+ | for arjun, wafw00f, s3scanner and cloud_enum |
| pipx | isolated installs of the Python tools (pip --user is the fallback) |
| curl | downloads wordlists and release installers |

On macOS, Homebrew is used for trufflehog and feroxbuster when present.
Optional per tool: nmap, and Npcap (Windows) or root (macOS/Linux) for naabu
SYN scans. The default naabu connect scan needs neither.

## Install

```
# macOS / Linux
./setup.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Scope flags: `--tools` / `-Tools` install tools only, `--words` / `-Words`
install wordlists only.

After install, make sure your Go bin dir (`~/go/bin` or
`%USERPROFILE%\go\bin`) and `~/.local/bin` are on PATH, then check a few:

```
subfinder -version
httpx -version
nuclei -version
```

## What gets installed

| Area | Tools |
|---|---|
| Passive subdomains | subfinder |
| Active DNS | dnsx, alterx |
| Port scan | naabu |
| HTTP probe and fingerprint | httpx, tlsx, cdncheck, wafw00f |
| Crawl and URLs | katana, urlfinder |
| JS and secrets | jsluice, trufflehog |
| Content discovery | feroxbuster, ffuf |
| Parameter discovery | arjun |
| Vulnerability templates | nuclei |
| Cloud and buckets | cloud_enum, s3scanner |
| Engine queries | uncover |

## Wordlists

Installed under `wordlists/`:

```
wordlists/dns/subdomains.txt                 subdomain names for dnsx bruteforce
wordlists/content/raft-medium-directories.txt  directory discovery
wordlists/content/raft-medium-files.txt         file discovery
wordlists/params/parameters.txt              parameter names for arjun/ffuf
wordlists/resolvers/resolvers.txt            trusted DNS resolvers for dnsx
wordlists/passwords/rockyou.txt              passwords (credential use only)
```

Grow these over time. `rockyou` is tracked with Git LFS, see
`wordlists/README.md`.

## Using the tools

See `docs/CHEATSHEET.md` for example commands per tool and how they chain, and
`docs/API-KEYS.md` for enabling passive sources (subfinder, uncover).
