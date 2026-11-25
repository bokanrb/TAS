# TAS environment setup for Windows (PowerShell 5+).
# Installs the recon tools and the wordlists. After it finishes you run each
# tool directly (subfinder, httpx, nuclei, ...). Installs nothing that touches
# a target.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#   ... -Tools        tools only
#   ... -Words        wordlists only
#   ... -Yes          assume yes to prerequisite install prompts

param([switch]$Tools, [switch]$Words, [switch]$Yes)

$ErrorActionPreference = "Continue"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WL = Join-Path $RepoDir "wordlists"
$BinDir = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$DoTools = -not $Words
$DoWords = -not $Tools

function Say($m) { Write-Host "`n[*] $m" }
function OK($m)  { Write-Host "  [OK] $m" }
function No($m)  { Write-Host "  [--] $m" }
function Have($c) { return [bool](Get-Command $c -ErrorAction SilentlyContinue) }

function Refresh-Path {
  $m = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
  $u = [System.Environment]::GetEnvironmentVariable("Path", "User")
  $env:PATH = "$m;$u;$BinDir"
}
Refresh-Path

$PkgMgr = if (Have winget) { "winget" } elseif (Have choco) { "choco" } elseif (Have scoop) { "scoop" } else { "" }

function Confirm-Install($msg) {
  if ($Yes) { return $true }
  $a = Read-Host "      $msg [y/N]"
  return ($a -match '^(y|yes)$')
}

function Install-Pkg($generic) {
  switch ($PkgMgr) {
    "winget" {
      $id = @{ go = "GoLang.Go"; python = "Python.Python.3.12"; git = "Git.Git" }[$generic]
      if (-not $id) { No "no winget id for $generic"; return }
      & winget install -e --id $id --accept-source-agreements --accept-package-agreements
    }
    "choco" {
      $p = @{ go = "golang"; python = "python"; git = "git" }[$generic]
      & choco install $p -y
    }
    "scoop" {
      $p = @{ go = "go"; python = "python"; git = "git" }[$generic]
      & scoop install $p
    }
    default { No "no package manager detected, install $generic manually" }
  }
  Refresh-Path
}

function Require($cmd, $generic, $why) {
  if (Have $cmd) { OK "$cmd present"; return }
  No "$cmd not found. $why"
  if ($generic -eq "pipx" -and (Have python)) {
    if (Confirm-Install "Install pipx now?") {
      & python -m pip install --user pipx | Out-Null
      & python -m pipx ensurepath 2>$null | Out-Null
      Refresh-Path
      if (Have pipx) { OK "pipx installed"; return }
    }
  }
  if (-not $PkgMgr) { No "no package manager (winget/choco/scoop), install $cmd manually"; return }
  if (Confirm-Install "Install $cmd now via $PkgMgr?") {
    Install-Pkg $generic
    if (Have $cmd) { OK "$cmd installed" } else { No "$cmd install failed (you may need to open a new shell)" }
  }
  else { No "skipped $cmd" }
}

# ---------------------------------------------------------------- preflight --
Say "Preflight (checks requirements, offers to install missing ones)"
if ($PkgMgr) { OK "package manager: $PkgMgr" } else { No "no package manager detected (winget/choco/scoop). Missing tools must be installed by hand" }
Require git    git    "needed by some installs and updates"
Require go     go     "needed to build subfinder, httpx, nuclei and the rest of the Go tools"
Require python python "needed for arjun, wafw00f, s3scanner, cloud_enum"
Require pipx   pipx   "isolated installs of the Python tools (pip --user is the fallback)"

$GoBin = (& go env GOBIN 2>$null)
if (-not $GoBin) { $gp = (& go env GOPATH 2>$null); if ($gp) { $GoBin = Join-Path $gp "bin" } }
if ($GoBin) { $env:PATH = "$GoBin;$env:PATH" }
if ($env:PATH -split ';' -contains $BinDir) { OK "$BinDir on PATH" } else { No "$BinDir not on PATH (see end of run)" }
if ($GoBin -and ($env:PATH -split ';' -contains $GoBin)) { OK "$GoBin on PATH" } else { No "$GoBin not on PATH (see end of run)" }

# ------------------------------------------------------- GitHub release asset -
function Install-Release($name, $repo) {
  if (Have $name) { OK "$name already installed"; return }
  try {
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers @{ "User-Agent" = "tas-setup" }
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { @("arm64", "aarch64") } else { @("amd64", "x86_64") }
    $asset = $rel.assets | Where-Object {
      $n = $_.name.ToLower()
      ($n -match "windows|win") -and ($arch | Where-Object { $n -match $_ }) -and ($n -match "\.zip$|\.tar\.gz$")
    } | Select-Object -First 1
    if (-not $asset) { No "$name no matching Windows asset. See github.com/$repo/releases"; return }
    $tmp = Join-Path $env:TEMP $asset.name
    Write-Host "  downloading $($asset.name)"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmp -UseBasicParsing
    $ext = Join-Path $env:TEMP ("tas_" + $name)
    Remove-Item -Recurse -Force $ext -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $ext | Out-Null
    if ($asset.name -match "\.zip$") { Expand-Archive -Path $tmp -DestinationPath $ext -Force }
    else { tar -xzf $tmp -C $ext }
    $bin = Get-ChildItem -Recurse -Path $ext -Filter "$name.exe" | Select-Object -First 1
    if (-not $bin) { $bin = Get-ChildItem -Recurse -Path $ext -Filter "$name" | Select-Object -First 1 }
    if ($bin) { Copy-Item $bin.FullName (Join-Path $BinDir "$name.exe") -Force; OK "$name -> $BinDir" }
    else { No "$name binary not found inside archive" }
  } catch { No "$name failed: $_. See github.com/$repo/releases" }
}

if ($DoTools) {
  Say "Go tools"
  function GoGet($name, $pkg) {
    if (Have $name) { OK "$name already installed"; return }
    if (Have go) { Write-Host "  installing $name"; $env:GOBIN = $GoBin; & go install $pkg 2>$null; if (Have $name) { OK $name } else { No "$name go install failed" } }
    else { No "$name skipped (go missing)" }
  }
  GoGet subfinder "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
  GoGet dnsx      "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
  GoGet alterx    "github.com/projectdiscovery/alterx/cmd/alterx@latest"
  GoGet naabu     "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
  GoGet httpx     "github.com/projectdiscovery/httpx/cmd/httpx@latest"
  GoGet tlsx      "github.com/projectdiscovery/tlsx/cmd/tlsx@latest"
  GoGet cdncheck  "github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest"
  GoGet katana    "github.com/projectdiscovery/katana/cmd/katana@latest"
  GoGet urlfinder "github.com/projectdiscovery/urlfinder/cmd/urlfinder@latest"
  GoGet nuclei    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
  GoGet uncover   "github.com/projectdiscovery/uncover/cmd/uncover@latest"
  GoGet ffuf      "github.com/ffuf/ffuf/v2@latest"
  GoGet jsluice   "github.com/BishopFox/jsluice/cmd/jsluice@latest"

  Say "trufflehog and feroxbuster"
  Install-Release "trufflehog" "trufflesecurity/trufflehog"
  Install-Release "feroxbuster" "epi052/feroxbuster"

  Say "Python tools"
  function PyGet($name, $spec) {
    if (Have $name) { OK "$name already installed"; return }
    if (Have pipx) { & pipx install $spec 2>$null; if (Have $name) { OK "$name (pipx)" } else { No "$name pipx install failed" } }
    elseif (Have python) { & python -m pip install --user --upgrade $spec 2>$null; OK "$name (pip --user)" }
    else { No "$name skipped (python missing)" }
  }
  PyGet arjun arjun
  PyGet wafw00f wafw00f
  PyGet s3scanner s3scanner
  if (Have cloud_enum) { OK "cloud_enum already installed" }
  elseif (Have pipx) { & pipx install "git+https://github.com/initstring/cloud_enum.git" 2>$null; if (Have cloud_enum) { OK "cloud_enum (pipx)" } else { No "cloud_enum pipx install failed" } }
  else { No "cloud_enum needs pipx: pipx install git+https://github.com/initstring/cloud_enum.git" }

  Say "nuclei templates"
  if (Have nuclei) { & nuclei -update-templates 2>$null; OK "nuclei templates updated" } else { No "nuclei not installed, skipping templates" }
}

# ----------------------------------------------------------------- wordlists -
function Dl($url, $dest) {
  if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 0)) { OK ((Split-Path $dest -Leaf) + " present"); return }
  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  try { Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing; OK (Split-Path $dest -Leaf) }
  catch { No ("failed " + (Split-Path $dest -Leaf)) }
}

if ($DoWords) {
  Say "Wordlists"
  $SL = "https://raw.githubusercontent.com/danielmiessler/SecLists/master"
  Dl "$SL/Discovery/DNS/subdomains-top1million-110000.txt" (Join-Path $WL "dns\subdomains.txt")
  Dl "$SL/Discovery/Web-Content/raft-medium-directories.txt" (Join-Path $WL "content\raft-medium-directories.txt")
  Dl "$SL/Discovery/Web-Content/raft-medium-files.txt" (Join-Path $WL "content\raft-medium-files.txt")
  Dl "$SL/Discovery/Web-Content/burp-parameter-names.txt" (Join-Path $WL "params\parameters.txt")
  Dl "https://raw.githubusercontent.com/trickest/resolvers/main/resolvers.txt" (Join-Path $WL "resolvers\resolvers.txt")

  $rock = Join-Path $WL "passwords\rockyou.txt"
  if ((Test-Path $rock) -and ((Get-Item $rock).Length -gt 0)) { OK "rockyou present" }
  else {
    $tgz = Join-Path $WL "passwords\rockyou.txt.tar.gz"
    Dl "$SL/Passwords/Leaked-Databases/rockyou.txt.tar.gz" $tgz
    if (Test-Path $tgz) { tar -xzf $tgz -C (Join-Path $WL "passwords"); Remove-Item $tgz -Force; OK "rockyou extracted" }
  }
}

# ---------------------------------------------------------------------- done -
Say "Done"
Write-Host "Wordlists live under $WL"
Write-Host "If a tool shows as not found, add these to PATH (then open a new shell):"
Write-Host "  $BinDir"
Write-Host "  $GoBin"
Write-Host "Set the user PATH with:  setx PATH `"$BinDir;$GoBin;%PATH%`""
Write-Host "API keys for passive sources go in your subfinder and uncover configs. See docs/API-KEYS.md"
