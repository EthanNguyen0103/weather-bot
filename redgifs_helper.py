#!/usr/bin/env python3
"""
RedGifs helper for MS Teams bot:
Fetch and search GIFs from redgifs.com and convert to lightweight animated GIFs for Teams.
Supports:
  !gif
  !gif random
  !gif -s "keyword"
  !gif -s keyword
  !gif keyword
"""

import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEEN_PHOTOS_FILE = Path(__file__).parent / ".seen_vitamin_photos.txt"
GIFENC_FILE = Path(__file__).parent / "gifenc.esm.js"

# Cache temporary token for 1 hour
_TOKEN_CACHE = {"token": "", "expires_at": 0.0}

POPULAR_RANDOM_TAGS = [
    "hot", "dance", "cosplay", "asian", "kpop", "anime", "cute", "model",
    "fitness", "beach", "bikini", "party", "funny", "art"
]


def _load_seen_photos() -> set[str]:
    if SEEN_PHOTOS_FILE.exists():
        return set(
            line.strip()
            for line in SEEN_PHOTOS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return set()


def _record_seen(key: str, data: bytes, seen: set[str]) -> None:
    data_hash = hashlib.sha256(data).hexdigest()[:24]
    seen.add(key)
    seen.add(data_hash)
    with SEEN_PHOTOS_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{key}\n{data_hash}\n")


def is_gif_command(msg_text: str) -> bool:
    """Check if message requests !gif or /gif."""
    lower = msg_text.lower().strip()
    if lower.startswith("🎬 redgifs") or "tiếp thêm năng lượng" in lower:
        return False
    return bool(re.search(r"(?:^|\s)[!/]gifs?\b", lower))


def parse_gif_command(msg_text: str) -> str:
    """
    Extract search keyword from !gif command.
    Returns keyword string, or empty string if random.
    """
    text = msg_text.strip()
    # 1. Check -s or --search flag
    m = re.search(
        r"(?:^|\s)(?:-s|--search)\s+[\"“'‘]?(.+?)[\"”'’]?\s*$",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        kw = m.group(1).strip()
        return "" if kw.lower() == "random" else kw[:60]

    # 2. Check "!gif keyword" (ignoring "!gif" or "!gif random")
    m = re.search(r"[!/]gifs?\s+(.+)$", text, flags=re.IGNORECASE)
    if m:
        kw = m.group(1).strip().strip("\"“”'")
        if kw.lower() in ("random", "", "-s", "--search"):
            return ""
        return kw[:60]

    return ""


def get_redgifs_token() -> str:
    """Get or refresh temporary RedGifs auth token."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    req = urllib.request.Request(
        "https://api.redgifs.com/v2/auth/temporary",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        token = data.get("token", "")
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expires_at"] = now + 3000  # 50 min
        return token


def _search_redgifs_api(keyword: str, page: int = 1, count: int = 20) -> list[dict]:
    """Search RedGifs API v2 with auth token."""
    token = get_redgifs_token()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
    }
    q = urllib.parse.quote_plus(keyword)
    order = random.choice(["trending", "top", "latest"])
    url = f"https://api.redgifs.com/v2/gifs/search?search_text={q}&order={order}&count={count}&page={page}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("gifs", [])


def _convert_video_to_gif(page, video_url: str) -> bytes:
    """Use browser context + gifenc to convert MP4 video frames into an animated GIF."""
    if not GIFENC_FILE.exists():
        raise FileNotFoundError(f"{GIFENC_FILE} not found.")

    lib_code = GIFENC_FILE.read_text(encoding="utf-8")
    gif_bytes_arr = page.evaluate(
        """async ({ libCode, videoUrl }) => {
            const blob = new Blob([libCode], { type: 'application/javascript' });
            const mod = await import(URL.createObjectURL(blob));
            const { GIFEncoder, quantize, applyPalette } = mod;

            const vResp = await fetch(videoUrl);
            const vBlob = await vResp.blob();
            const vUrl = URL.createObjectURL(vBlob);

            const video = document.createElement('video');
            video.src = vUrl;
            video.muted = true;
            video.playsInline = true;
            await new Promise((res, rej) => {
                video.onloadedmetadata = () => res();
                video.onerror = rej;
            });

            // Keep GIF size compact (~300KB-500KB) so Teams sends instantly
            const maxDim = 320;
            let w = video.videoWidth || 320, h = video.videoHeight || 240;
            if (w > maxDim || h > maxDim) {
                if (w > h) { h = Math.round(h * maxDim / w); w = maxDim; }
                else { w = Math.round(w * maxDim / h); h = maxDim; }
            }
            w = Math.floor(w / 2) * 2;
            h = Math.floor(h / 2) * 2;

            const canvas = document.createElement('canvas');
            canvas.width = w; canvas.height = h;
            const ctx = canvas.getContext('2d', { willReadFrequently: true });

            const duration = Math.min(video.duration || 2.5, 3.2);
            const numFrames = 12;
            const delay = Math.round((duration / numFrames) * 1000);

            const gif = GIFEncoder();
            let globalPalette = null;

            for (let i = 0; i < numFrames; i++) {
                const t = (i / numFrames) * duration;
                video.currentTime = t;
                await new Promise(r => { video.onseeked = () => r(); });
                ctx.drawImage(video, 0, 0, w, h);
                const imgData = ctx.getImageData(0, 0, w, h).data;
                if (!globalPalette) {
                    globalPalette = quantize(imgData, 128);
                }
                const indexed = applyPalette(imgData, globalPalette);
                gif.writeFrame(indexed, w, h, { palette: globalPalette, delay });
            }
            gif.finish();
            return Array.from(gif.bytes());
        }""",
        {"libCode": lib_code, "videoUrl": video_url},
    )
    return bytes(gif_bytes_arr)


def fetch_redgifs_gif(context, keyword: str = "") -> tuple[bytes, str, str]:
    """
    Fetch an unseen GIF from RedGifs matching `keyword` (or random trending tag if empty).
    Returns (gif_bytes, web_url, caption).
    """
    seen = _load_seen_photos()
    is_random = not keyword

    # If random, pick a random category/tag
    search_term = keyword if keyword else random.choice(POPULAR_RANDOM_TAGS)
    random_pages = list(range(1, 6))
    random.shuffle(random_pages)

    conv_page = context.new_page() if context else None
    try:
        for page_no in random_pages:
            try:
                gifs = _search_redgifs_api(search_term, page=page_no, count=25)
            except Exception as e:
                print(f"Warning searching RedGifs for '{search_term}': {e}", file=sys.stderr)
                continue

            if not gifs:
                continue

            random.shuffle(gifs)
            for g in gifs:
                gif_id = g.get("id", "")
                key_id = f"redgifs:{gif_id}"
                urls = g.get("urls", {})
                video_url = urls.get("sd") or urls.get("silent") or urls.get("hd")
                poster_url = urls.get("poster") or urls.get("thumbnail")
                web_url = urls.get("html") or f"https://www.redgifs.com/watch/{gif_id}"

                if not video_url and not poster_url:
                    continue
                if key_id in seen or (video_url and video_url in seen):
                    continue

                # Convert MP4 to animated GIF via Chromium
                gif_data = None
                if conv_page and video_url:
                    try:
                        gif_data = _convert_video_to_gif(conv_page, video_url)
                    except Exception as e:
                        print(f"Warning converting video to gif ({video_url}): {e}", file=sys.stderr)

                # Fallback to poster image if video conversion failed
                if not gif_data and poster_url:
                    try:
                        req = urllib.request.Request(poster_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            gif_data = resp.read()
                    except Exception:
                        continue

                if gif_data and len(gif_data) > 10000:
                    data_hash = hashlib.sha256(gif_data).hexdigest()[:24]
                    if data_hash not in seen:
                        _record_seen(key_id, gif_data, seen)
                        if is_random:
                            caption = f"🎬 RedGifs: '{search_term}' | ✨"
                        else:
                            caption = f"🎬 RedGifs: '{keyword}' | ✨"
                        return gif_data, web_url, caption
    finally:
        if conv_page is not None and not conv_page.is_closed():
            try:
                conv_page.close()
            except Exception:
                pass

    raise RuntimeError(f"No new unseen GIF found for '{keyword or search_term}'.")


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    test_kw = sys.argv[1] if len(sys.argv) > 1 else ""
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        b_data, url, cap = fetch_redgifs_gif(ctx, test_kw)
        print("Success!", cap, url, f"Size: {len(b_data)} bytes, Header: {b_data[:6]}")
        b.close()

