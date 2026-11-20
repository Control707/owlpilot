"""Remote access through Tailscale: open OwlPilot on your phone, tablet, TV or another computer.

OwlPilot does not run its own server. It asks It, which hosts the page, to answer your tailnet:
`it network tailscale` reaches devices signed in to *your* Tailscale account only, never the open
internet or the café Wi-Fi, and `it https on` adds an https address through Tailscale. Every new
screen still has to be paired with It before it can see anything.

  python -m owlpilot.remote status     what is reachable from where (JSON)
  python -m owlpilot.remote on         answer your tailnet (and over https when Tailscale allows)
  python -m owlpilot.remote off        back to this computer only
  python -m owlpilot.remote pair       print a one-time pairing link that works from another device
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

from .core import IT_BINARY, IT_HOME, OwlPilotError

PAGE_PATH = "/p/owlpilot"
TAILSCALE_APP = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


def _run(args, timeout=60):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                              env={**os.environ, "IT_HOME": str(IT_HOME)})
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def _json(proc):
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None


def _error(proc):
    for line in (proc.stderr or "").splitlines():
        try:
            err = json.loads(line).get("error") or {}
        except (json.JSONDecodeError, AttributeError):
            continue
        return {"code": err.get("code", "error"), "message": err.get("message", ""), "hint": err.get("hint", "")}
    text = (proc.stderr or proc.stdout or "").strip().splitlines()
    return {"code": "error", "message": text[-1][:300] if text else "failed", "hint": ""}


def it(*args):
    return _run([str(IT_BINARY), *args])


def tailscale_binary():
    return shutil.which("tailscale") or (TAILSCALE_APP if os.path.exists(TAILSCALE_APP) else None)


def tailscale_status():
    """Installed / signed in / this machine's tailnet name. Never returns keys or other peers."""
    binary = tailscale_binary()
    if not binary:
        return {"installed": False, "running": False}
    data = _json(_run([binary, "status", "--json"], timeout=15)) or {}
    me = data.get("Self") or {}
    return {"installed": True, "running": data.get("BackendState") == "Running",
            "state": data.get("BackendState", "unknown"),
            "host": (me.get("DNSName") or "").rstrip("."), "ips": [ip for ip in me.get("TailscaleIPs") or [] if ":" not in ip][:1]}


def _addresses(raw):
    """`it network --json` lists addresses as strings or objects; keep http(s) URLs only."""
    urls = []
    for item in raw or []:
        value = item if isinstance(item, str) else (item.get("url") or item.get("address") or "") if isinstance(item, dict) else ""
        if value and "://" not in value:
            value = "http://" + value
        if value.startswith(("http://", "https://")) and value not in urls:
            urls.append(value.rstrip("/"))
    return urls


def status():
    net = _json(it("network", "--json")) or {}
    https = _json(it("https", "--json")) or {}
    ts = tailscale_status()
    base = _addresses(net.get("addresses"))
    if https.get("https") and ts.get("host"):
        secure = f"https://{ts['host']}"
        if secure not in base:
            base.insert(0, secure)
    mode = "off"
    if net.get("network"):
        mode = net.get("mode") or ("tailscale" if base and all(_is_tailnet(u, ts) for u in base) else "network")
    return {"mode": mode, "https": bool(https.get("https")), "funnel": net.get("funnel", "unknown"),
            "urls": [u + PAGE_PATH for u in base], "tailscale": ts}


def _is_tailnet(url, ts):
    host = urlsplit(url).hostname or ""
    return host.endswith(".ts.net") or host == ts.get("host") or host in ts.get("ips", []) or host.startswith("100.")


def enable():
    ts = tailscale_status()
    if not ts["installed"]:
        raise OwlPilotError("Tailscale is not installed on this computer. Install it from https://tailscale.com/download and sign in, then try again.")
    if not ts["running"]:
        raise OwlPilotError("Tailscale is installed but not signed in or not running. Open Tailscale, sign in, then try again.")
    proc = it("network", "tailscale", "--json")
    if proc.returncode != 0:
        err = _error(proc)
        raise OwlPilotError(f"{err['message']} {err['hint']}".strip())
    https = it("https", "on", "--json")  # optional: needs HTTPS certificates enabled for the tailnet
    result = status()
    if https.returncode != 0:
        result["httpsError"] = _error(https)["message"][:200]
    return result


def disable():
    it("https", "off", "--json")
    proc = it("network", "off", "--json")
    if proc.returncode != 0:
        err = _error(proc)
        raise OwlPilotError(err["message"] or "Could not turn remote access off.")
    return status()


def pair_link():
    """One-time pairing link rewritten to this machine's tailnet address so another device can open it.

    The secret is the part after '#'; it is single-use and expires quickly. Do not store or log it.
    """
    current = status()
    if current["mode"] == "off" or not current["urls"]:
        raise OwlPilotError("Remote access is off. Run `python -m owlpilot.remote on` first.")
    data = _json(it("site", "--no-open", "--json")) or {}
    link = data.get("url") or ""
    if "#" not in link:
        raise OwlPilotError("It did not return a pairing link. Is It running?")
    remote = urlsplit(current["urls"][0])
    parts = urlsplit(link)
    return urlunsplit((remote.scheme, remote.netloc, parts.path, parts.query, parts.fragment))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else "status"
    try:
        if command == "status":
            print(json.dumps(status(), indent=2))
        elif command == "on":
            result = enable()
            print(json.dumps(result, indent=2))
            print("\nRemote access is on for your tailnet. Next, pair each new device once:\n"
                  "  .venv/bin/python -m owlpilot.remote pair", file=sys.stderr)
        elif command == "off":
            print(json.dumps(disable(), indent=2))
        elif command == "pair":
            link = pair_link()
            print(link)
            print("\nOpen this link on the other device (it must be signed in to the same Tailscale account).\n"
                  "It works once and expires in a few minutes. Then open OwlPilot at the same address + /p/owlpilot.",
                  file=sys.stderr)
        else:
            print(__doc__, file=sys.stderr)
            return 2
        return 0
    except OwlPilotError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
