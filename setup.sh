#!/usr/bin/env bash
#
# TAS environment setup for macOS and Linux.
# Installs the recon tools and the wordlists. After it finishes you run each
# tool directly (subfinder, httpx, nuclei, ...). This script installs nothing
# that touches a target.
#
# Usage:
#   ./setup.sh            install tools and wordlists
#   ./setup.sh --tools    tools only
#   ./setup.sh --words    wordlists only
#
set -u

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WL="$REPO_DIR/wordlists"
BIN_DIR="$HOME/.local/bin"
OS="$(uname -s)"
mkdir -p "$BIN_DIR"

DO_TOOLS=1
DO_WORDS=1
case "${1:-}" in
  --tools) DO_WORDS=0 ;;
  --words) DO_TOOLS=0 ;;
esac

say()  { printf '\n[*] %s\n' "$1"; }
ok()   { printf '  [OK] %s\n' "$1"; }
no()   { printf '  [--] %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

GOBIN="$(go env GOBIN 2>/dev/null)"
[ -z "${GOBIN:-}" ] && GOBIN="$(go env GOPATH 2>/dev/null)/bin"

# ---------------------------------------------------------------- preflight --
say "Preflight"
have go      && ok "go $(go version | awk '{print $3}')" || no "go not found. Install from https://go.dev/dl (needed for most tools)"
have git     && ok "git present" || no "git not found. Install git"
have python3 && ok "python3 $(python3 -V 2>&1 | awk '{print $2}')" || no "python3 not found (needed for arjun, wafw00f, s3scanner, cloud_enum)"
have pipx    && ok "pipx present" || no "pipx not found. Falling back to pip --user (brew install pipx, or python3 -m pip install --user pipx)"
case ":$PATH:" in *":$BIN_DIR:"*) ok "$BIN_DIR on PATH" ;; *) no "$BIN_DIR not on PATH (see end of run)" ;; esac
case ":$PATH:" in *":$GOBIN:"*) ok "$GOBIN on PATH" ;; *) no "$GOBIN not on PATH (see end of run)" ;; esac

# ------------------------------------------------------------------ go tools -
goget() {  # name  package
  if have "$1"; then ok "$1 already installed"; return; fi
  if have go; then
    printf '  installing %s\n' "$1"
    if GOBIN="$GOBIN" go install "$2" >/dev/null 2>&1; then ok "$1"; else no "$1 go install failed"; fi
  else
    no "$1 skipped (go missing)"
  fi
}

if [ "$DO_TOOLS" = 1 ]; then
  say "Go tools"
  goget subfinder github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
  goget dnsx      github.com/projectdiscovery/dnsx/cmd/dnsx@latest
  goget alterx    github.com/projectdiscovery/alterx/cmd/alterx@latest
  goget naabu     github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
  goget httpx     github.com/projectdiscovery/httpx/cmd/httpx@latest
  goget tlsx      github.com/projectdiscovery/tlsx/cmd/tlsx@latest
  goget cdncheck  github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest
  goget katana    github.com/projectdiscovery/katana/cmd/katana@latest
  goget urlfinder github.com/projectdiscovery/urlfinder/cmd/urlfinder@latest
  goget nuclei    github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
  goget uncover   github.com/projectdiscovery/uncover/cmd/uncover@latest
  goget ffuf      github.com/ffuf/ffuf/v2@latest
  goget jsluice   github.com/BishopFox/jsluice/cmd/jsluice@latest

  # --- trufflehog and feroxbuster: brew on mac, official installer otherwise ---
  say "trufflehog and feroxbuster"
  if have trufflehog; then ok "trufflehog already installed"
  elif [ "$OS" = "Darwin" ] && have brew; then
    brew install trufflehog >/dev/null 2>&1 && ok "trufflehog (brew)" || no "trufflehog brew install failed"
  else
    if curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b "$BIN_DIR" >/dev/null 2>&1; then
      ok "trufflehog -> $BIN_DIR"
    else
      no "trufflehog failed. Grab a binary from github.com/trufflesecurity/trufflehog/releases"
    fi
  fi
  if have feroxbuster; then ok "feroxbuster already installed"
  elif [ "$OS" = "Darwin" ] && have brew; then
    brew install feroxbuster >/dev/null 2>&1 && ok "feroxbuster (brew)" || no "feroxbuster brew install failed"
  else
    if ( cd "$BIN_DIR" && curl -sSL https://raw.githubusercontent.com/epi052/feroxbuster/main/install-nix.sh | bash ) >/dev/null 2>&1; then
      ok "feroxbuster -> $BIN_DIR"
    else
      no "feroxbuster failed. Grab a binary from github.com/epi052/feroxbuster/releases"
    fi
  fi

  # --- python tools ---
  pyget() {  # name  spec
    if have "$1"; then ok "$1 already installed"; return; fi
    if have pipx; then
      pipx install "$2" >/dev/null 2>&1 && ok "$1 (pipx)" || no "$1 pipx install failed"
    elif have python3; then
      python3 -m pip install --user --upgrade "$2" >/dev/null 2>&1 && ok "$1 (pip --user)" || no "$1 pip install failed"
    else
      no "$1 skipped (python3 missing)"
    fi
  }
  say "Python tools"
  pyget arjun arjun
  pyget wafw00f wafw00f
  pyget s3scanner s3scanner
  if have cloud_enum; then ok "cloud_enum already installed"
  elif have pipx; then
    pipx install "git+https://github.com/initstring/cloud_enum.git" >/dev/null 2>&1 && ok "cloud_enum (pipx)" || no "cloud_enum pipx install failed"
  else
    no "cloud_enum needs pipx: pipx install git+https://github.com/initstring/cloud_enum.git"
  fi

  # --- nuclei templates ---
  say "nuclei templates"
  if have nuclei; then
    nuclei -update-templates >/dev/null 2>&1 && ok "nuclei templates updated" || no "template update failed (run: nuclei -update-templates)"
  else
    no "nuclei not installed, skipping templates"
  fi
fi

# ----------------------------------------------------------------- wordlists -
dl() {  # url  dest
  if [ -s "$2" ]; then ok "$(basename "$2") present"; return; fi
  mkdir -p "$(dirname "$2")"
  if curl -sSL "$1" -o "$2"; then ok "$(basename "$2")"; else no "failed $(basename "$2")"; fi
}

if [ "$DO_WORDS" = 1 ]; then
  say "Wordlists"
  SL="https://raw.githubusercontent.com/danielmiessler/SecLists/master"
  dl "$SL/Discovery/DNS/subdomains-top1million-110000.txt" "$WL/dns/subdomains.txt"
  dl "$SL/Discovery/Web-Content/raft-medium-directories.txt" "$WL/content/raft-medium-directories.txt"
  dl "$SL/Discovery/Web-Content/raft-medium-files.txt" "$WL/content/raft-medium-files.txt"
  dl "$SL/Discovery/Web-Content/burp-parameter-names.txt" "$WL/params/parameters.txt"
  dl "https://raw.githubusercontent.com/trickest/resolvers/main/resolvers.txt" "$WL/resolvers/resolvers.txt"

  if [ -s "$WL/passwords/rockyou.txt" ]; then
    ok "rockyou present"
  else
    mkdir -p "$WL/passwords"
    if dl "$SL/Passwords/Leaked-Databases/rockyou.txt.tar.gz" "$WL/passwords/rockyou.txt.tar.gz" \
       && tar xzf "$WL/passwords/rockyou.txt.tar.gz" -C "$WL/passwords" >/dev/null 2>&1; then
      rm -f "$WL/passwords/rockyou.txt.tar.gz"
      ok "rockyou extracted"
    else
      no "rockyou fetch failed"
    fi
  fi
fi

# ---------------------------------------------------------------------- done -
say "Done"
printf 'Wordlists live under %s\n' "$WL"
printf 'If a tool shows as not found, add these to your shell profile and reopen the shell:\n'
printf '  export PATH="%s:%s:$PATH"\n' "$BIN_DIR" "$GOBIN"
printf 'Verify with, for example:  subfinder -version   httpx -version   nuclei -version\n'
printf 'API keys for passive sources go in your subfinder and uncover configs. See docs/API-KEYS.md\n'
