# Wordlists

Fetched by `./setup.sh --words` (or `setup.ps1 -Words`) from public mirrors.
Grow these over time. That is the point.

| Path | Used by | Seeded from |
|---|---|---|
| `dns/subdomains.txt` | dnsx bruteforce | SecLists `subdomains-top1million-110000` |
| `content/raft-medium-directories.txt` | feroxbuster, ffuf | SecLists raft directories |
| `content/raft-medium-files.txt` | feroxbuster, ffuf | SecLists raft files |
| `params/parameters.txt` | arjun, ffuf | SecLists `burp-parameter-names` |
| `resolvers/resolvers.txt` | dnsx | trickest/resolvers |
| `passwords/rockyou.txt` | password and credential use only | SecLists rockyou |

## rockyou and password lists

`passwords/` holds password dictionaries such as rockyou. These are for
password and credential attacks only. Never use them for DNS or directory
discovery, since they are the wrong kind of list and very large.

Large files here are tracked with Git LFS (see `.gitattributes`). Install LFS
once with `git lfs install`. The `passwords/*.txt` pattern is already tracked.

Only commit password lists built from public sources. Never commit a credential
recovered from a target, since that is confidential data and does not belong in
the repo.
