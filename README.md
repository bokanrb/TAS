# TAS, Target Attack Surface

A thin, modular recon and enumeration orchestrator. Each stage is a small wrapper around a best in class tool. Run one stage at a time, or chain them all.

- **Cross platform.** Pure Python orchestrator that behaves the same on macOS, Linux and Windows. No parallel bash and PowerShell scripts to maintain.
- **Modular.** `tas <stage> <target>` runs one stage. `tas all <target>` runs the whole pipeline and feeds each stage's output into the next.
- **Throttled by default.** Conservative rate (4 threads, 500 ms delay, 5 req/s). Override per run or in config.

> This tool is for authorized testing only. Test only assets you own or have explicit written permission to test. See `docs/SCOPE.md`.

## Install

```
# macOS / Linux
./install/install.sh
# Windows
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

Make sure your Go bin dir (`~/go/bin` or `%USERPROFILE%\go\bin`) is on PATH, then check:

```
python tas.py doctor
```

## Usage

```
python tas.py list                       # show stages in order
python tas.py dns_passive example.com    # one stage
python tas.py httpprobe hosts.txt        # a stage on a file of hosts
python tas.py all example.com            # full pipeline
python tas.py all example.com --only dns_passive,dns_active,httpprobe
python tas.py all example.com --skip cloud,portscan
python tas.py vulnscan example.com --tags exposure,misconfig --severity high,critical
```

Results land in `output/<target>/<stage>/`. Rate overrides are `--threads N`, `--delay MS` and `--rate N`.

See `docs/USAGE.md` for per stage flags and `docs/API-KEYS.md` for passive source keys.

## Stages

| # | Stage | Tool(s) |
|---|---|---|
| 1 | `dns_passive` | subfinder |
| 2 | `dns_active` | dnsx, alterx |
| 3 | `httpprobe` | httpx, tlsx, cdncheck, wafw00f |
| 4 | `portscan` | naabu (plus nmap) |
| 5 | `crawl` | katana, urlfinder |
| 6 | `jsanalysis` | jsluice, trufflehog |
| 7 | `content` | feroxbuster |
| 8 | `params` | arjun (plus ffuf) |
| 9 | `vulnscan` | nuclei |
| 10 | `takeover` | nuclei (takeover templates) |
| 11 | `cloud` | cloud_enum, s3scanner |

## Layout

```
tas.py              entry point
tas/cli.py          argument parsing and pipeline runner
tas/common.py       Context, config, tool execution
tas/modules/*.py    one file per stage
config/config.yaml  rate limits, wordlist paths, per tool flags
install/            cross platform installer
wordlists/          DNS, content, params, passwords (grow these)
output/             per run results (git ignored)
```
