#!/usr/bin/env python3
"""Local-only CLI for Lennox S40 (and S30/E30 LAN) thermostats.

Uses the reverse-engineered lennoxs30api library over HTTPS on the LAN.
No cloud credentials. No password. Self-signed TLS is expected.

Config (env or defaults):
  LENNOX_IP       thermostat IP or mDNS name (required; or pass --ip)
  LENNOX_APP_ID   unique client id (default mapp…827200)
  LENNOX_TIMEOUT  seconds (default: 90)

Commands:
  status
  mode <off|cool|heat|auto> [--zone N|name]
  cool <F> [--zone N|name]
  heat <F> [--zone N|name]
  fan <auto|on|circulate> [--zone N|name]
  away <on|off>
  discover   print mDNS / quick Connect probe help
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from typing import Optional

# Prefer the dedicated venv's site-packages when invoked via wrapper,
# but also work if deps are already importable.
try:
    from lennoxs30api.s30api_async import s30api_async
except ImportError:
    print(
        "lennoxs30api not installed. Use the wrapper at ~/.local/bin/lennox-s40\n"
        "or: ~/.local/share/lennox-s40/venv/bin/pip install lennoxs30api aiohttp pytz",
        file=sys.stderr,
    )
    sys.exit(2)

# No baked-in home IP. Prefer LENNOX_IP, then mDNS via discover, else fail closed.
DEFAULT_IP = os.environ.get("LENNOX_IP", "").strip()
DEFAULT_APP_ID = os.environ.get(
    "LENNOX_APP_ID", "mapp079372367644467046827200"
)  # unique vs phone app / HA; override if multiple clients
DEFAULT_TIMEOUT = int(os.environ.get("LENNOX_TIMEOUT", "90"))
POLL_MAX = int(os.environ.get("LENNOX_POLL_MAX", "80"))


def resolve_host(host: str) -> str:
    """Return IP if host is a name; leave dotted quads alone."""
    if all(p.isdigit() for p in host.split(".")) and host.count(".") == 3:
        return host
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        raise SystemExit(f"Cannot resolve host {host!r}: {e}") from e


async def connect(ip: str, app_id: str) -> s30api_async:
    api = s30api_async(
        username="",
        password="",
        app_id=app_id,
        ip_address=ip,
        protocol="https",
        pii_message_logs=False,
        message_debug_logging=False,
        timeout=DEFAULT_TIMEOUT,
        long_poll_delay=6,
    )
    await api.serverConnect()
    return api


async def pump_until_ready(api: s30api_async):
    system = api.getSystem("LCC")
    await api.subscribe(system)
    for i in range(POLL_MAX):
        try:
            await api.messagePump()
        except Exception as e:
            # S40 occasionally resets the stack; one reconnect usually recovers
            if i % 15 == 0:
                try:
                    await api.serverConnect()
                    await api.subscribe(system)
                except Exception:
                    pass
            continue
        active = [z for z in system.zone_list if getattr(z, "temperature", None) is not None]
        if system.name and active:
            return system
    return system


def pick_zone(system, zone_arg: Optional[str]):
    zones = list(system.zone_list)
    active = [z for z in zones if getattr(z, "temperature", None) is not None]
    if not zones:
        raise SystemExit("No zones discovered yet")
    if zone_arg is None:
        if not active:
            raise SystemExit("No active zones with temperature data")
        return active[0]
    # numeric id
    if zone_arg.isdigit():
        zid = int(zone_arg)
        for z in zones:
            if getattr(z, "id", None) == zid:
                return z
        raise SystemExit(f"No zone with id={zid}")
    # name match (case-insensitive)
    needle = zone_arg.lower()
    for z in zones:
        if (getattr(z, "name", None) or "").lower() == needle:
            return z
    for z in zones:
        if needle in (getattr(z, "name", None) or "").lower():
            return z
    raise SystemExit(f"No zone matching {zone_arg!r}")


def zone_dict(z) -> dict:
    return {
        "id": getattr(z, "id", None),
        "name": getattr(z, "name", None),
        "temperature_F": getattr(z, "temperature", None),
        "humidity_pct": getattr(z, "humidity", None),
        "mode": getattr(z, "systemMode", None),
        "heat_setpoint_F": getattr(z, "hsp", None),
        "cool_setpoint_F": getattr(z, "csp", None),
        "single_setpoint_F": getattr(z, "sp", None),
        "fan": getattr(z, "fanMode", None),
        "humidity_mode": getattr(z, "humidityMode", None),
        "active": getattr(z, "temperature", None) is not None,
    }


def system_dict(system) -> dict:
    return {
        "name": system.name,
        "product": system.productType,
        "serial": system.serialNumber,
        "software": system.softwareVersion,
        "outdoor_temp_F": system.outdoorTemperature,
        "indoor_unit": system.indoorUnitType,
        "outdoor_unit": system.outdoorUnitType,
        "manual_away": system.manualAwayMode,
        "wifi_ip": system.wifi_ip,
        "wifi_ssid": system.wifi_ssid,
        "wifi_rssi": system.wifi_rssi,
        "alert": system.alert,
        "temp_unit": system.temperatureUnit,
        "single_setpoint_mode": system.single_setpoint_mode,
        "zones": [zone_dict(z) for z in system.zone_list],
    }


MODE_MAP = {
    "off": "off",
    "cool": "cool",
    "heat": "heat",
    "auto": "heat and cool",
    "heat_cool": "heat and cool",
    "heat-cool": "heat and cool",
    "heat and cool": "heat and cool",
}


def require_ip(args) -> str:
    ip = (getattr(args, "ip", None) or DEFAULT_IP or "").strip()
    if not ip:
        raise SystemExit(
            "No thermostat IP. Set LENNOX_IP, pass --ip, or run: lennox-s40 discover"
        )
    return resolve_host(ip)


async def cmd_status(args) -> int:
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        print(json.dumps(system_dict(system), indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def cmd_mode(args) -> int:
    mode = MODE_MAP.get(args.mode.lower())
    if mode is None:
        raise SystemExit(f"Unknown mode {args.mode!r}; use off|cool|heat|auto")
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        z = pick_zone(system, args.zone)
        await z.setHVACMode(mode)
        # brief refresh
        for _ in range(5):
            await api.messagePump()
        print(json.dumps({"ok": True, "zone": zone_dict(z), "mode": mode}, indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def cmd_cool(args) -> int:
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        z = pick_zone(system, args.zone)
        await z.perform_setpoint(r_csp=float(args.temp_f))
        for _ in range(5):
            await api.messagePump()
        print(json.dumps({"ok": True, "zone": zone_dict(z)}, indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def cmd_heat(args) -> int:
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        z = pick_zone(system, args.zone)
        await z.perform_setpoint(r_hsp=float(args.temp_f))
        for _ in range(5):
            await api.messagePump()
        print(json.dumps({"ok": True, "zone": zone_dict(z)}, indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def cmd_fan(args) -> int:
    fan = args.fan.lower()
    if fan not in {"auto", "on", "circulate"}:
        raise SystemExit("fan must be auto|on|circulate")
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        z = pick_zone(system, args.zone)
        await z.setFanMode(fan)
        for _ in range(5):
            await api.messagePump()
        print(json.dumps({"ok": True, "zone": zone_dict(z), "fan": fan}, indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def cmd_away(args) -> int:
    on = args.state.lower() in {"on", "1", "true", "yes"}
    ip = require_ip(args)
    api = await connect(ip, args.app_id)
    try:
        system = await pump_until_ready(api)
        await system.setManualAwayMode(on)
        for _ in range(5):
            await api.messagePump()
        print(json.dumps({"ok": True, "manual_away": system.manualAwayMode}, indent=2))
        return 0
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


def _mdns_s40_hosts() -> list[str]:
    """Best-effort mDNS: dns-sd -Z dump looking for Lennox-S40 / icomfort4."""
    import re
    import subprocess

    hosts: list[str] = []
    try:
        p = subprocess.run(
            ["dns-sd", "-Z", "_http._tcp", "local."],
            capture_output=True,
            text=True,
            timeout=6,
        )
        out = (p.stdout or "") + (p.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return hosts
    for m in re.finditer(r"Lennox-S40-[A-Za-z0-9]+\.local", out, re.I):
        h = m.group(0)
        if h not in hosts:
            hosts.append(h)
    return hosts


def cmd_discover(args) -> int:
    """Quick local discovery: mDNS + Connect probe. No personal defaults."""
    print("S40 advertises mDNS:")
    print("  hostname: Lennox-S40-<SERIAL>.local")
    print("  service:  _http._tcp  instance containing _icomfort4  port 443")
    print()
    print("Probe an IP:")
    print("  curl -k -s -o /dev/null -w '%{http_code}\\n' -X POST \\")
    print(f"    https://<IP>/Endpoints/{args.app_id}/Connect")
    print("  HTTP 200 or 204 = local API is live (self-signed cert expected).")
    print()

    candidates: list[str] = []
    if args.ip:
        candidates.append(args.ip)
    if DEFAULT_IP and DEFAULT_IP not in candidates:
        candidates.append(DEFAULT_IP)
    for h in _mdns_s40_hosts():
        if h not in candidates:
            candidates.append(h)

    if not candidates:
        print("No candidates (set LENNOX_IP or ensure S40 is on LAN with mDNS).")
        return 1

    ctx = ssl._create_unverified_context()
    found = 0
    for host in candidates:
        try:
            ip = resolve_host(host)
        except SystemExit as e:
            print(f"  {host}: resolve failed ({e})")
            continue
        url = f"https://{ip}/Endpoints/{args.app_id}/Connect"
        try:
            req = urllib.request.Request(url, method="POST", data=b"")
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                print(f"  {host} -> {ip}: Connect HTTP {resp.status}  (GOOD)")
                print(f"  export LENNOX_IP={ip}")
                found += 1
        except urllib.error.HTTPError as e:
            print(f"  {host} -> {ip}: Connect HTTP {e.code}")
        except Exception as e:
            print(f"  {host} -> {ip}: {type(e).__name__}: {e}")
    return 0 if found else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lennox-s40", description="Lennox S40 local LAN control")
    p.add_argument(
        "--ip",
        default=DEFAULT_IP or None,
        help="thermostat IP or mDNS name (or env LENNOX_IP)",
    )
    p.add_argument("--app-id", default=DEFAULT_APP_ID, help="unique client application id")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="read system + zone state")
    s.set_defaults(func=lambda a: asyncio.run(cmd_status(a)))

    s = sub.add_parser("mode", help="set HVAC mode")
    s.add_argument("mode", help="off|cool|heat|auto")
    s.add_argument("--zone", help="zone id or name (default: first active)")
    s.set_defaults(func=lambda a: asyncio.run(cmd_mode(a)))

    s = sub.add_parser("cool", help="set cool setpoint °F")
    s.add_argument("temp_f", type=float)
    s.add_argument("--zone", help="zone id or name")
    s.set_defaults(func=lambda a: asyncio.run(cmd_cool(a)))

    s = sub.add_parser("heat", help="set heat setpoint °F")
    s.add_argument("temp_f", type=float)
    s.add_argument("--zone", help="zone id or name")
    s.set_defaults(func=lambda a: asyncio.run(cmd_heat(a)))

    s = sub.add_parser("fan", help="set fan mode")
    s.add_argument("fan", help="auto|on|circulate")
    s.add_argument("--zone", help="zone id or name")
    s.set_defaults(func=lambda a: asyncio.run(cmd_fan(a)))

    s = sub.add_parser("away", help="manual away mode")
    s.add_argument("state", help="on|off")
    s.set_defaults(func=lambda a: asyncio.run(cmd_away(a)))

    s = sub.add_parser("discover", help="probe local S40 API")
    s.set_defaults(func=cmd_discover)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
