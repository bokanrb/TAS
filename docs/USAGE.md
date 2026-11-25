# Usage notes

## Data flow between stages

In `tas all`, each stage publishes an artifact that later stages read:

```
dns_passive -> subdomains
dns_active  -> resolved, dns_records   (reads subdomains)
httpprobe   -> live, httpx_json        (reads resolved or subdomains)
portscan    -> ports                   (reads resolved or subdomains)
crawl       -> urls                    (reads live)
jsanalysis  -> js_endpoints, secrets   (reads urls or live)
content     -> content                 (reads live)
params      -> params                  (reads live or urls)
vulnscan    -> vulns                    (reads live)
takeover    -> takeover                 (reads resolved or subdomains)
cloud       -> cloud_assets             (reads --keyword or target)
```

Run a stage on its own and it resolves input in this order: explicit `--input FILE`, then the upstream artifact if present in the output dir, then the target itself.

## Per stage flags

- `dns_passive --all-sources` uses all subfinder sources, slower.
- `dns_active --no-brute --no-permute` resolves known names only.
- `httpprobe --ports 80,443` is the default. Widen only when you are allowed to.
- `portscan --ports top-100|top-1000|full|<spec> --syn --nmap`.
- `crawl --depth 2 --js-crawl --no-passive`.
- `content --depth 2 --wordlist PATH`.
- `params --urls-from live|urls`.
- `vulnscan --tags ... --templates PATH --severity ...`.
- `cloud --keyword acme`.

## Throttling

Global flags are `--threads`, `--delay` (ms) and `--rate` (req/s), or edit `config/config.yaml`. Defaults are deliberately low. Test the real rate on a box you own before pointing a stage at any engagement, and raise limits only when the target's rules allow it.

## ffuf as a fallback fuzzer

The `params` and `content` stages lean on arjun and feroxbuster, but ffuf covers anything with a `FUZZ` keyword:

```
ffuf -u https://host/FUZZ -w wordlists/content/raft-medium-directories.txt -t 4 -rate 5
ffuf -u 'https://host/api?FUZZ=1' -w wordlists/params/parameters.txt -t 4 -rate 5
```

## jsanalysis and trufflehog

jsluice and trufflehog work best on files you already fetched. Export the JS you care about to a folder and point trufflehog at it with `trufflehog filesystem ./js --json`. For a repository use `trufflehog git <url>`.
