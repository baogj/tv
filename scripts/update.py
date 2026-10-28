#!/usr/bin/env python3
"""原样镜像直播源：下载原始字节并原封不动写入 output/，不做任何解析或修改。

- 第 1 个源 -> output/live.m3u，第 2 个 -> output/source2.m3u，依此类推
- 仅在 HTTP 200 且内容非空时写入；失败则保留上一次的文件
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

TIMEOUT = 60
USER_AGENT = "Mozilla/5.0 (compatible; IPTV-Mirror/1.0; +https://github.com/baogj/tv)"

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "config" / "sources.txt"
OUT_DIR = ROOT / "output"


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


def out_path(index: int) -> Path:
    return OUT_DIR / ("live.m3u" if index == 1 else f"source{index}.m3u")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return resp.read()


def main() -> int:
    urls = load_source_urls(SOURCES_FILE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for i, url in enumerate(urls, start=1):
        dest = out_path(i)
        print(f"[{i}] {url} -> {dest.relative_to(ROOT)}")
        try:
            data = fetch_bytes(url)
            if not data:
                raise RuntimeError("empty body")
        except Exception as exc:  # noqa: BLE001 — keep previous file
            print(f"  FAIL — {exc} (kept previous file)")
            fail += 1
            continue
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        print(f"  OK — {len(data)} bytes, sha256={hashlib.sha256(data).hexdigest()}")
        ok += 1
    print(f"Done: sources ok={ok} fail={fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
