#!/usr/bin/env bash
#
# TAS environment setup for macOS and Linux.
# Installs the recon tools and the wordlists. After it finishes you run each
# tool directly (subfinder, httpx, nuclei, ...). Installs nothing that touches
# a target.
#
# Usage:
#   ./setup.sh            install tools and wordlists
#   ./setup.sh --tools    tools only
#   ./setup.sh --words    wordlists only
#   ./setup.sh -y         assume yes to prerequisite install prompts
#
set -u

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WL="$REPO_DIR/wordlists"
BIN_DIR="$HOME/.local/bin"
OS="$(uname -s)"
mkdir -p "$BIN_DIR"

DO_TOOLS=1
DO_WORDS=1
ASSUME_YES=0
for a in "$@"; do
  case "$a" in
    --tools) DO_WORDS=0 ;;
    --words) DO_TOOLS=0 ;;
    -y|--yes) ASSUME_YES=1 ;;
  esac
done

say()  { printf '\n[*] %s\n' "$1"; }
ok()   { printf '  [OK] %s\n' "$1"; }
no()   { printf '  [--] %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

# make freshly installed user-space binaries visible within this run
export PATH="$BIN_DIR:$PATH"

# sudo only when needed and available
SUDO=""
[ "$(id -u)" -ne 0 ] && have sudo && SUDO="sudo"

# detect a package manager
PKG=""
if [ "$OS" = "Darwin" ]; then have brew && PKG="brew"
elif have apt-get; then PKG="apt"
elif have dnf; then PKG="dnf"
elif have pacman; then PKG="pacman"
fi

ask() {  # prompt, returns 0 for yes
  [ "$ASSUME_YES" = 1 ] && return 0
  [ -t 0 ] || return 1           # non-interactive, do not assume yes
  printf '      %s [y/N] ' "$1"
  read -r ans
  case "$ans" in [yY]|[yY][eE][sS]) return 0 ;; *) return 1 ;; esac
}

pkg_name() {  # manager generic -> package name(s)
  case "$1" in
    brew)   case "$2" in go) echo go;; python3) echo python3;; pipx) echo pipx;; git) echo git;; curl) echo curl;; esac ;;
    apt)    case "$2" in go) echo golang-go;; python3) echo "python3 python3-pip python3-venv";; pipx) echo pipx;; git) echo git;; curl) echo curl;; esac ;;
    dnf)    case "$2" in go) echo golang;; python3) echo "python3 python3-pip";; pipx) echo pipx;; git) echo git;; curl) echo curl;; esac ;;
    pacman) case "$2" in go) echo go;; python3) echo "python python-pip";; pipx) echo python-pipx;; git) echo git;; curl) echo curl;; esac ;;
  esac
}

pkg_install() {  # generic name
  local p; p="$(pkg_name "$PKG" "$1")"
  if [ -z "$p" ]; then no "no package mapping for $1 with $PKG"; return 1; fi
  printf '      installing %s via %s\n' "$1" "$PKG"
  case "$PKG" in
    brew)   brew install $p ;;
    apt)    $SUDO apt-get update -y && $SUDO apt-get install -y $p ;;
    dnf)    $SUDO dnf install -y $p ;;
    pacman) $SUDO pacman -S --noconfirm $p ;;
    *) return 1 ;;
  esac
}

require() {  # cmd  why
  local cmd="$1" why="$2"
  if have "$cmd"; then ok "$cmd present"; return 0; fi
  no "$cmd not found. $why"
  # pipx has a reliable pip fallback that needs no package manager
  if [ "$cmd" = pipx ] && have python3; then
    if ask "Install pipx now?"; then
      python3 -m pip install --user pipx >/dev/null 2>&1 && python3 -m pipx ensurepath >/dev/null 2>&1
      have pipx && { ok "pipx installed"; return 0; }
    fi
  fi
  if [ -z "$PKG" ]; then no "no package manager detected, install $cmd manually"; return 1; fi
  if ask "Install $cmd now via $PKG?"; then
    pkg_install "$cmd" && have "$cmd" && { ok "$cmd installed"; return 0; }
    no "$cmd install failed"
    return 1
  fi
  no "skipped $cmd"
  return 1
}

# ---------------------------------------------------------------- preflight --
say "Preflight (checks requirements, offers to install missing ones)"
[ -n "$PKG" ] && ok "package manager: $PKG" || no "no package manager detected (brew/apt/dnf/pacman). Missing tools must be installed by hand"
require curl    "needed to download wordlists and installers"
require git     "needed by some installs and updates"
require go      "needed to build subfinder, httpx, nuclei and the rest of the Go tools"
require python3 "needed for arjun, wafw00f, s3scanner, cloud_enum"
require pipx    "isolated installs of the Python tools (pip --user is the fallback)"

# recompute Go bin dir now that Go may have just been installed
GOBIN="$(go env GOBIN 2>/dev/null)"
[ -z "${GOBIN:-}" ] && GOBIN="$(go env GOPATH 2>/dev/null)/bin"
[ -n "$GOBIN" ] && export PATH="$GOBIN:$PATH"
case ":$PATH:" in *":$BIN_DIR:"*) ok "$BIN_DIR on PATH" ;; *) no "$BIN_DIR not on PATH (see end of run)" ;; esac
[ -n "$GOBIN" ] && { case ":$PATH:" in *":$GOBIN:"*) ok "$GOBIN on PATH" ;; *) no "$GOBIN not on PATH (see end of run)" ;; esac; }

# ------------------------------------------------------------------ go tools -
goget() {  # name  package
  if have "$1"; then ok "$1 already installed"; return; fi
  if have go; then
    printf '  installing %s\n' "$1"
    if GOBIN="$GOBIN" go install "$2" >/dev/null 2>&1; then ok "$1"; else no "$1 go install failed (is Go 1.21+? distro Go can be too old, see https://go.dev/dl)"; fi
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
  goget mapcidr    github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest
  goget hakip2host github.com/hakluke/hakip2host@latest

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
