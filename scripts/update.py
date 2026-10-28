#!/usr/bin/env python3
"""Fetch IPTV sources, merge and write output/live.m3u and output/live.txt."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "config" / "sources.txt"
OUT_DIR = ROOT / "output"
OUT_M3U = OUT_DIR / "live.m3u"
OUT_TXT = OUT_DIR / "live.txt"

USER_AGENT = (
    "Mozilla/5.0 (compatible; IPTV-Aggregator/1.0; +https://github.com/baogj/tv)"
)
TIMEOUT = 30


def load_source_urls(path: Path) -> list[str]:
    urls: list[str] = []
    if not path.is_file():
        print(f"ERROR: sources file not found: {path}", file=sys.stderr)
        return urls
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        charset = "utf-8"
        ctype = resp.headers.get_content_charset()
        if ctype:
            charset = ctype
        return raw.decode(charset, errors="replace")


def parse_playlist(text: str) -> list[tuple[str, str]]:
    """Return list of (name, url). Supports M3U and simple name,url TXT."""
    channels: list[tuple[str, str]] = []
    lines = [ln.strip() for ln in text.splitlines()]
    # Drop BOM / empty leading
    while lines and not lines[0]:
        lines.pop(0)

    is_m3u = bool(lines) and (
        lines[0].upper().startswith("#EXTM3U")
        or any(ln.upper().startswith("#EXTINF") for ln in lines[:20])
    )

    if is_m3u:
        name: str | None = None
        for ln in lines:
            if not ln:
                continue
            upper = ln.upper()
            if upper.startswith("#EXTINF"):
                # #EXTINF:-1 attrs...,Name
                if "," in ln:
                    name = ln.split(",", 1)[1].strip() or "未命名"
                else:
                    name = "未命名"
                continue
            if ln.startswith("#"):
                continue
            if name is None:
                name = "未命名"
            channels.append((name, ln))
            name = None
        return channels

    # TXT: name,url  (also tolerate name,url with http(s) on right)
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        if "," not in ln:
            continue
        # Split on last comma before URL-like token, or first comma
        m = re.match(r"^(.+?),\s*(https?://\S+|rtmp://\S+|rtsp://\S+|.+)$", ln)
        if not m:
            continue
        n, u = m.group(1).strip(), m.group(2).strip()
        if n and u:
            channels.append((n, u))
    return channels


def main() -> int:
    urls = load_source_urls(SOURCES_FILE)
    if not urls:
        print("No source URLs in config/sources.txt")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_M3U.write_text("#EXTM3U\n", encoding="utf-8")
        OUT_TXT.write_text("", encoding="utf-8")
        return 0

    seen: set[str] = set()
    merged: list[tuple[str, str]] = []
    ok = 0
    fail = 0

    for src in urls:
        print(f"Fetching: {src}")
        try:
            text = fetch(src)
            parsed = parse_playlist(text)
            added = 0
            for name, stream in parsed:
                key = stream.strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append((name.strip() or "未命名", key))
                added += 1
            print(f"  OK — {len(parsed)} parsed, {added} new")
            ok += 1
        except Exception as exc:  # noqa: BLE001 — continue other sources
            print(f"  FAIL — {exc}")
            fail += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    m3u_lines = ["#EXTM3U"]
    txt_lines: list[str] = []
    for name, stream in merged:
        m3u_lines.append(f"#EXTINF:-1,{name}")
        m3u_lines.append(stream)
        txt_lines.append(f"{name},{stream}")

    OUT_M3U.write_text("\n".join(m3u_lines) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(txt_lines) + ("\n" if txt_lines else ""), encoding="utf-8")

    print(
        f"Done: sources ok={ok} fail={fail}; channels={len(merged)}; "
        f"wrote {OUT_M3U.relative_to(ROOT)} and {OUT_TXT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
