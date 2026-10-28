#!/usr/bin/env python3
"""Fetch IPTV sources, merge and write output/live.m3u and output/live.txt.

默认保持源原样：不去重、保留原始顺序、保留 #EXTINF 属性（tvg-id / tvg-logo /
group-title 等）以及 #EXTVLCOPT / #KODIPROP 等附加行，并沿用源 #EXTM3U 头部属性
（如 x-tvg-url）。
"""

from __future__ import annotations

import re
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# ===== 配置 =====
DEDUPE = False  # True = 按流地址去重（保留首次出现）；False = 保持原样
TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; IPTV-Aggregator/1.0; +https://github.com/baogj/tv)"
)
DEFAULT_GROUP = "未分组"
# ================

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "config" / "sources.txt"
OUT_DIR = ROOT / "output"
OUT_M3U = OUT_DIR / "live.m3u"
OUT_TXT = OUT_DIR / "live.txt"

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


@dataclass
class Entry:
    name: str
    url: str
    group: str | None = None
    extinf: str | None = None  # original #EXTINF line (None for TXT sources)
    extra: list[str] = field(default_factory=list)  # #EXTVLCOPT, #KODIPROP, ...


def load_source_urls(path: Path) -> list[str]:
    if not path.is_file():
        print(f"ERROR: sources file not found: {path}", file=sys.stderr)
        return []
    urls = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace").lstrip("\ufeff")


def parse_m3u(lines: list[str]) -> tuple[dict[str, str], list[Entry]]:
    header: dict[str, str] = {}
    entries: list[Entry] = []
    extinf: str | None = None
    extra: list[str] = []
    grp_tag: str | None = None
    for ln in lines:
        if not ln:
            continue
        up = ln.upper()
        if up.startswith("#EXTM3U"):
            header.update(dict(ATTR_RE.findall(ln)))
            continue
        if up.startswith("#EXTINF"):
            extinf, extra, grp_tag = ln, [], None
            continue
        if up.startswith("#EXTGRP:"):
            grp_tag = ln.split(":", 1)[1].strip()
            extra.append(ln)
            continue
        if ln.startswith("#"):
            if extinf is not None:
                extra.append(ln)  # #EXTVLCOPT / #KODIPROP etc.
            continue
        # stream URL line
        if extinf is not None:
            name = extinf.split(",", 1)[1].strip() if "," in extinf else ""
            attrs = dict(ATTR_RE.findall(extinf.split(",", 1)[0]))
            group = attrs.get("group-title") or grp_tag
        else:
            name, group = "", None
        entries.append(Entry(name or "未命名", ln, group, extinf, extra))
        extinf, extra, grp_tag = None, [], None
    return header, entries


def parse_txt(lines: list[str]) -> list[Entry]:
    entries: list[Entry] = []
    group: str | None = None
    for ln in lines:
        if not ln or ln.startswith("#") or "," not in ln:
            continue
        name, url = (s.strip() for s in ln.split(",", 1))
        if url == "#genre#":
            group = name
            continue
        if name and url:
            entries.append(Entry(name, url, group))
    return entries


def parse_playlist(text: str) -> tuple[dict[str, str], list[Entry]]:
    lines = [ln.strip() for ln in text.splitlines()]
    head = [ln for ln in lines if ln][:20]
    if head and (head[0].upper().startswith("#EXTM3U")
                 or any(l.upper().startswith("#EXTINF") for l in head)):
        return parse_m3u(lines)
    return {}, parse_txt(lines)


def build_extinf(e: Entry) -> str:
    if e.extinf:
        return e.extinf
    attr = f' group-title="{e.group}"' if e.group else ""
    return f"#EXTINF:-1{attr},{e.name}"


def main() -> int:
    urls = load_source_urls(SOURCES_FILE)
    header: dict[str, str] = {}
    epg_urls: list[str] = []
    merged: list[Entry] = []
    seen: set[str] = set()
    ok = fail = 0

    for src in urls:
        print(f"Fetching: {src}")
        try:
            h, entries = parse_playlist(fetch(src))
        except Exception as exc:  # noqa: BLE001 — continue other sources
            print(f"  FAIL — {exc}")
            fail += 1
            continue
        ok += 1
        for k, v in h.items():
            if k.lower() in ("x-tvg-url", "url-tvg"):
                for u in v.split(","):
                    u = u.strip()
                    if u and u not in epg_urls:
                        epg_urls.append(u)
            else:
                header.setdefault(k, v)
        added = 0
        for e in entries:
            if DEDUPE:
                if e.url in seen:
                    continue
                seen.add(e.url)
            merged.append(e)
            added += 1
        print(f"  OK — {len(entries)} parsed, {added} added")

    if epg_urls:
        header["x-tvg-url"] = ",".join(epg_urls)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    head_line = "#EXTM3U" + "".join(f' {k}="{v}"' for k, v in header.items())
    m3u = [head_line]
    for e in merged:
        m3u.append(build_extinf(e))
        m3u.extend(e.extra)
        m3u.append(e.url)
    OUT_M3U.write_text("\n".join(m3u) + "\n", encoding="utf-8")

    # TXT: "分组,#genre#" 格式；分组按首次出现顺序，组内保持原始顺序
    txt: list[str] = []
    if any(e.group for e in merged):
        groups: dict[str, list[Entry]] = {}
        for e in merged:
            groups.setdefault(e.group or DEFAULT_GROUP, []).append(e)
        for g, items in groups.items():
            txt.append(f"{g},#genre#")
            txt.extend(f"{e.name},{e.url}" for e in items)
    else:
        txt = [f"{e.name},{e.url}" for e in merged]
    OUT_TXT.write_text("\n".join(txt) + ("\n" if txt else ""), encoding="utf-8")

    print(
        f"Done: sources ok={ok} fail={fail}; channels={len(merged)} "
        f"(dedupe={'on' if DEDUPE else 'off'}); "
        f"wrote {OUT_M3U.relative_to(ROOT)} and {OUT_TXT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
