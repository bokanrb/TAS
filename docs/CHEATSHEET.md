# Cheatsheet

Example commands per tool. Adjust rate and threads to what the target allows.
Conservative defaults shown (low concurrency, a small delay). Paths assume you
run from the repo root so `wordlists/...` resolves.

## Passive subdomains

```
subfinder -d example.com -all -silent -o subs.txt
```

## Active DNS (bruteforce, permutations, resolution)

```
# permutations of known names
alterx -l subs.txt -o perms.txt

# bruteforce from the wordlist, then resolve, with trusted resolvers
dnsx -d example.com -w wordlists/dns/subdomains.txt -r wordlists/resolvers/resolvers.txt -silent -o resolved.txt

# resolve a known list and keep CNAMEs (useful for takeover checks)
dnsx -l subs.txt -a -cname -resp -r wordlists/resolvers/resolvers.txt -silent -j -o dns.jsonl
```

## Hostnames from an IP

```
# purpose-built: PTR, TLS SAN/CN, SPF from each IP
echo 1.2.3.4 | hakip2host

# expand a CIDR to IPs first, then resolve hostnames
echo 1.2.3.0/24 | mapcidr -silent | hakip2host

# alternatives already in the kit
echo 1.2.3.4 | dnsx -ptr -resp-only -silent      # reverse DNS only
echo 1.2.3.4 | tlsx -san -cn -silent             # names from the TLS cert
```

Reverse lookups on a CDN or shared host return many unrelated domains, so
confirm each is in scope. `cdncheck -l ips.txt -resp` flags CDN IPs first.

## HTTP probe and fingerprint

```
# default to web ports, tech detect, titles, status, json
httpx -l resolved.txt -ports 80,443 -td -title -sc -ip -json -o http.jsonl

# plain live URL list for the next stages
httpx -l resolved.txt -silent -o live.txt

# TLS SANs can reveal more hostnames
tlsx -l resolved.txt -san -cn -silent -o tls.txt

# is an IP behind a CDN or WAF
cdncheck -l ips.txt -resp

# WAF fingerprint
wafw00f https://example.com
```

## Port scan (throttled)

```
# connect scan, no root needed, rate limited
naabu -l resolved.txt -p 80,443 -scan-type c -rate 100 -c 25 -o ports.txt

# follow up with service/version detection on the hits
nmap -sV --open -Pn -iL ports.txt -oN nmap.txt
```

## Crawl and URLs

```
# active crawl, honour depth and rate
katana -list live.txt -d 2 -rl 50 -jc -o crawl.txt

# passive URLs from archives and sources
urlfinder -list live.txt -o passive.txt
```

## JS and secrets

```
# pull endpoints out of JS
jsluice urls -R js_urls.txt > endpoints.txt

# scan a local export dir or a git repo for verified secrets
trufflehog filesystem ./downloaded_js --json
trufflehog git https://github.com/org/repo --json
```

## Content and directory discovery

```
# feroxbuster, recursive, rate limited
feroxbuster -u https://example.com -w wordlists/content/raft-medium-directories.txt --threads 10 --rate-limit 50 --depth 2

# ffuf as a general fuzzer (dirs, vhosts, anything with FUZZ)
ffuf -u https://example.com/FUZZ -w wordlists/content/raft-medium-directories.txt -t 10 -rate 50
```

## Parameter discovery

```
arjun -u https://example.com/page -oJ params.json
arjun -i live.txt -oJ params.json          # many URLs from a file

# or fuzz a known param name list
ffuf -u 'https://example.com/api?FUZZ=1' -w wordlists/params/parameters.txt -t 10 -rate 50
```

## Vulnerability templates

```
# curate: pick tags, keep severity high, rate limit
nuclei -l live.txt -tags exposure,misconfig,cve -severity medium,high,critical -rl 50 -o nuclei.txt

# refresh templates
nuclei -update-templates
```

## Subdomain takeover

```
nuclei -l resolved.txt -tags takeover -o takeover.txt
```

## Cloud and buckets

```
cloud_enum -k example -k example.com
s3scanner scan -bucket example
```

## Engine queries (needs API keys)

```
uncover -shodan 'org:"Example"' -silent
uncover -q 'ssl:"example.com"' -e shodan,censys -silent
```

## A simple chain

```
subfinder -d example.com -all -silent -o subs.txt
dnsx -l subs.txt -silent -r wordlists/resolvers/resolvers.txt -o resolved.txt
httpx -l resolved.txt -silent -o live.txt
katana -list live.txt -d 2 -silent -o urls.txt
nuclei -l live.txt -tags exposure,misconfig -severity high,critical -o findings.txt
```
