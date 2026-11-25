# Wordlists

Fetched by `python tas.py install --wordlists` from public mirrors. Grow these over time. That is the point.

| Dir | Used by | Seeded from |
|---|---|---|
| `dns/` | dns_active | SecLists `subdomains-top1million-110000` |
| `content/` | content (feroxbuster) | SecLists `raft-medium-directories`, `raft-medium-files` |
| `params/` | params (arjun or ffuf) | SecLists `burp-parameter-names` |
| `passwords/` | password and credential use only | your own `rockyou.txt` |

## rockyou and password lists

`passwords/` holds password dictionaries such as rockyou. These are for password and credential attacks only. Never use them for DNS or directory discovery, since they are the wrong kind of list and very large.

Large files here are tracked with Git LFS (see `.gitattributes`). Install LFS once with `git lfs install`. The `passwords/*.txt` pattern is already tracked.

Only commit password lists built from public sources. Never commit a credential recovered from a target, since that is confidential data and does not belong in the repo.
