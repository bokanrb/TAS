# Passive source API keys

You do not need a custom script to query passive sources. subfinder and uncover read their own key files. Add keys to enable more sources. Without keys, subfinder still uses its keyless sources.

## subfinder

Edit `~/.config/subfinder/provider-config.yaml` (created on first run):

```
shodan: [KEY]
censys: [TOKEN_ID:SECRET]
github: [PAT]
gitlab: [TOKEN]
virustotal: [KEY]
securitytrails: [KEY]
chaos: [KEY]
```

If a source host is unreachable on your network it just errors and subfinder moves on to the next one.

## uncover

Set env vars or `~/.config/uncover/provider-config.yaml` with `SHODAN_API_KEY`, `CENSYS_API_ID`, `CENSYS_API_SECRET`, `FOFA_EMAIL`, `FOFA_KEY`.

```
uncover -shodan 'org:"Example"' -silent
uncover -q 'ssl:"example.com"' -e shodan,censys -silent
```

## Keep keys out of git

Key files live outside the repo in the tool config dirs. If you keep a copy here, put it in `config/provider-config.yaml`, which is git ignored.
