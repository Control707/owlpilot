#!/bin/sh
# One-time setup for OwlPilot on macOS or Linux. Run from the repository root:
#   ./scripts/setup.sh
# Installs everything inside this folder: It (into .tools/it), a Python venv (.venv),
# and a browser for D2L sign-in. It does not change your shell profile or install a login service.
set -eu
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
IT_VERSION="v0.1.45"
IT_HOME="$ROOT/.tools/it"
export IT_HOME

say() { printf '\n==> %s\n' "$1"; }

say "Checking prerequisites"
command -v python3 >/dev/null || { echo "python3 is required (3.11+)."; exit 1; }
command -v curl >/dev/null || { echo "curl is required."; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python 3.11 or newer is required."; exit 1; }

if [ ! -x "$IT_HOME/bin/it" ]; then
  say "Installing It $IT_VERSION into .tools/it (project-local, PATH unchanged)"
  mkdir -p .tools/downloads
  curl -fsSL "https://github.com/Aaryan-Kapoor/it/releases/download/$IT_VERSION/install.sh" -o .tools/downloads/install-it.sh
  IT_INSTALL_NO_PATH=1 IT_INSTALL_PLAIN=1 IT_VERSION="$IT_VERSION" sh .tools/downloads/install-it.sh </dev/null
else
  say "It already installed in .tools/it"
fi

if [ ! -f "$IT_HOME/installation.json" ] || ! "$IT_HOME/bin/it" whoami >/dev/null 2>&1; then
  say "Setting up It on this machine (no agent add-ons, no background service)"
  "$IT_HOME/bin/it" setup --none --no-service --name "OwlPilot-$(hostname -s 2>/dev/null || echo local)" || true
fi

say "Turning off It usage reporting and update checks"
"$IT_HOME/bin/it" telemetry off >/dev/null 2>&1 || true
"$IT_HOME/bin/it" updates off >/dev/null 2>&1 || true

say "Creating Python environment (.venv)"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

say "Installing a browser for D2L sign-in"
# d2l-cli falls back to an installed Chrome or Edge, so this download is optional.
.venv/bin/python -m playwright install chromium || echo "Skipped; D2L sign-in will use your installed Chrome or Edge."

say "Choosing your school (any D2L Brightspace school)"
if .venv/bin/d2l --json setup --show | grep -q '"lms_host": "http'; then
  echo "Already configured: $(.venv/bin/d2l --json setup --show | sed -n 's/.*"lms_host": "\(.*\)".*/\1/p')"
elif [ -n "${OWLPILOT_SCHOOL:-}" ]; then
  .venv/bin/python -m owlpilot.d2l setup --school "$OWLPILOT_SCHOOL"
elif [ -n "${D2L_HOST:-${OWLPILOT_D2L_URL:-}}" ]; then
  .venv/bin/python -m owlpilot.d2l setup --host "${D2L_HOST:-$OWLPILOT_D2L_URL}"
else
  echo "Skipped. Pick your school in OwlPilot → Settings, or run:  .venv/bin/d2l setup"
fi

cat <<EOF

Setup complete. Next:

  1. Start OwlPilot (keep this running):   ./scripts/start.sh
  2. Pair your browser (once per browser):  IT_HOME="\$PWD/.tools/it" .tools/it/bin/it site
  3. Open OwlPilot:                         http://localhost:4700/p/owlpilot
  4. Settings -> choose your school -> "Sign in to D2L"

Optional, to use OwlPilot on your phone or another computer: install Tailscale, sign in, then
Settings -> "Use on any screen" (or: .venv/bin/python -m owlpilot.remote on).

EOF
