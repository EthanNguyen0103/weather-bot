#!/usr/bin/env python3
"""
Send Weather Alerts & Reply to @Mentions for TTC (Tan Thuan Tower) & FPT Software TP.HCM
in MS Teams External Chat using a Free Personal @outlook.com Account.

Can run 24/7 on Free Cloud (Hugging Face Spaces / Render / Koyeb / GitHub Actions)
without needing Power Automate or your local PC!
"""

import argparse
import base64
import hashlib
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from weather_bot import LOCATIONS, fetch_all_locations

SESSION_FILE = Path(__file__).parent / "teams_session.json"
LAST_REPLIED_FILE = Path(__file__).parent / ".last_replied_msg"

# Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Trigger keywords/names when someone tags or asks the bot in chat
BOT_TRIGGERS = ["@weather", "weather b", "weather bot", "!weather"]


def start_health_server() -> None:
    """Start a tiny HTTP server on $PORT (default 7860) so Free Cloud hosts (HF Spaces, Render, Koyeb) stay alive."""
    port = int(os.environ.get("PORT", "7860"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Teams Weather Bot (TTC & FPT Software) is running 24/7!\n")

        def log_message(self, format, *args):
            pass  # Silence HTTP health check logs

    server = HTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"🌐 Cloud health-check server listening on port {port}")


def format_multi_location_message(results: list, triggered_by: str = "") -> str:
    """Format a combined weather update for TTC & FPT Software TP.HCM."""
    any_alert = any(r["analysis"]["is_alert"] for r in results)
    title_prefix = "⚠️ WEATHER ALERT" if any_alert else "🌤️ Weather Update"

    header = f"{title_prefix} — TTC & FPT Software TP.HCM"
    if triggered_by:
        header += f" ({triggered_by})"

    lines = [header, ""]

    for item in results:
        loc_name = item["name"]
        map_url = item["map_url"]
        a = item["analysis"]
        badge = "⚠️ Rain/Alert" if a["is_alert"] else "✅ Clear"

        lines.append(f"📍 {loc_name} ({badge}) — {map_url}")
        lines.append(
            f"   Now: {a['current_icon']} {a['current_desc']} | "
            f"{a['current_temp']}°C (Feels like {a['feels_like']}°C) | "
            f"💧 {a['humidity']}% | 💨 {a['wind']} km/h"
        )
        if a["upcoming_alerts"]:
            lines.append("   ☔ Upcoming Bad Weather (Next 6h):")
            for alert in a["upcoming_alerts"][:3]:
                clean = alert.replace("**", "")
                lines.append(f"     • {clean}")

        lines.append("   🕒 Next 6 Hours Forecast:")
        for r in a["forecast_rows"]:
            lines.append(
                f"     • {r['time']}: {r['condition']} | {r['temp']} | ☔ {r['rain_prob']} ({r['precip']})"
            )
        lines.append("")

    return "\n".join(lines)


def filter_locations_from_query(text: str) -> list:
    """If the user specifically asked for 'ttc' or 'fpt', filter to that location; otherwise return both."""
    lower = text.lower()
    want_ttc = "ttc" in lower or "tan thuan" in lower or "tân thuận" in lower
    want_fpt = "fpt" in lower or "f-town" in lower or "ftown" in lower
    if want_ttc and not want_fpt:
        return [loc for loc in LOCATIONS if "TTC" in loc["name"]]
    if want_fpt and not want_ttc:
        return [loc for loc in LOCATIONS if "FPT" in loc["name"]]
    return LOCATIONS


def is_vitamin_sea_command(msg_text: str) -> bool:
    """Check if a chat message requests !vitaminSea."""
    lower = msg_text.lower().strip()
    if "🌊 vitamin" in lower or "tiếp thêm năng lượng code" in lower:
        return False
    return any(cmd in lower for cmd in ["!vitaminsea", "/vitaminsea", "!vitamin", "!girl"])


def is_bot_mentioned(msg_text: str, bot_name: str) -> bool:
    """Check if a chat message tags the bot or contains a weather trigger keyword."""
    lower = msg_text.lower().strip()
    if "🌤️ weather update" in lower or "⚠️ weather alert" in lower or "🕒 next 6 hours forecast:" in lower:
        return False
    if bot_name and bot_name.lower() in lower:
        return True
    return any(trig in lower for trig in BOT_TRIGGERS)


VOZ_THREAD_URL = "https://voz.vn/t/no-sex-vitamin-gai-xinh-moi-ngay-cho-doi-mat-sang-khoe-dep.783806"
SEEN_PHOTOS_FILE = Path(__file__).parent / ".seen_vitamin_photos.txt"


def _load_seen_photos() -> set[str]:
    if SEEN_PHOTOS_FILE.exists():
        return set(line.strip() for line in SEEN_PHOTOS_FILE.read_text(encoding="utf-8").splitlines() if line.strip())
    return set()


def _record_seen_photo(url: str, img_bytes: bytes, seen: set[str]) -> None:
    img_hash = hashlib.sha256(img_bytes).hexdigest()[:24]
    seen.add(url)
    seen.add(img_hash)
    with SEEN_PHOTOS_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{url}\n{img_hash}\n")


def fetch_vitamin_sea_photo(context=None) -> tuple[bytes, str]:
    """Fetch a unique, unseen random photo from the VOZ Vitamin Gái Xinh thread (783806) with multi-source fallbacks."""
    import json
    import random
    import urllib.request

    seen = _load_seen_photos()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://voz.vn/",
    }

    # 1. Primary source: VOZ Thread 783806 via Playwright browser tab (checks up to 3 random pages for an unseen photo)
    if context is not None:
        voz_page = None
        try:
            voz_page = context.new_page()
            for _attempt in range(3):
                random_page = random.randint(240, 360)
                target_url = f"{VOZ_THREAD_URL}/page-{random_page}"
                voz_page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                voz_page.wait_for_timeout(1500)

                img_urls = voz_page.evaluate(
                    """() => {
                        const raw = [];
                        document.querySelectorAll('.message-body .bbWrapper img').forEach(img => {
                            const u = img.getAttribute('data-url') || img.getAttribute('data-src') || img.getAttribute('src') || img.src || '';
                            if (u) raw.push(u);
                        });
                        document.querySelectorAll('.message-body .bbWrapper a.js-lbImage').forEach(a => {
                            const u = a.getAttribute('href') || '';
                            if (u) raw.push(u);
                        });
                        const resolved = raw.map(u => {
                            try { return new URL(u, document.baseURI).href; } catch (e) { return ''; }
                        });
                        return [...new Set(resolved.filter(u =>
                            u.startsWith('http')
                            && !u.includes('/smilies/')
                            && !u.includes('/avatars/')
                            && !u.includes('twemoji')
                            && !u.includes('reactions')
                            && !u.includes('data:image')
                            && !u.endsWith('.gif')
                            && !u.endsWith('.svg')
                        ))];
                    }"""
                )
                unseen_urls = [u for u in img_urls if u not in seen]
                if unseen_urls:
                    random.shuffle(unseen_urls)
                    for candidate_url in unseen_urls[:8]:
                        try:
                            resp = voz_page.request.get(
                                candidate_url, headers={"Referer": "https://voz.vn/"}, timeout=12000
                            )
                            if resp.ok:
                                body = resp.body()
                                img_hash = hashlib.sha256(body).hexdigest()[:24]
                                if len(body) > 15000 and img_hash not in seen:
                                    _record_seen_photo(candidate_url, body, seen)
                                    voz_page.close()
                                    return body, candidate_url
                        except Exception:
                            continue
        except Exception as e:
            print(f"Warning fetching from VOZ: {e}", file=sys.stderr)
        finally:
            if voz_page is not None and not voz_page.is_closed():
                try:
                    voz_page.close()
                except Exception:
                    pass

    # 2. Secondary source: Bing Images async search for VOZ / Vietnamese Vitamin Gái Xinh (works even when Cloudflare blocks VOZ)
    bing_queries = [
        "gai+xinh+viet+nam+voz+portrait",
        "vitamin+gai+xinh+viet+nam+trong+sang",
        "hot+girl+viet+nam+ao+dai+portrait",
        "gai+xinh+han+quoc+ulzzang+portrait",
    ]
    random.shuffle(bing_queries)
    for q in bing_queries[:2]:
        try:
            offset = random.randint(1, 80)
            bing_url = f"https://www.bing.com/images/async?q={q}&first={offset}&count=35&adlt=moderate"
            req = urllib.request.Request(
                bing_url,
                headers={"User-Agent": headers["User-Agent"], "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            candidates = re.findall(r"murl&quot;:&quot;(https://[^&]+?)&quot;", html, flags=re.IGNORECASE)
            unseen_candidates = [
                u for u in candidates
                if u not in seen and not u.lower().endswith((".gif", ".svg", ".webp"))
            ]
            random.shuffle(unseen_candidates)
            for candidate_url in unseen_candidates[:10]:
                try:
                    img_req = urllib.request.Request(candidate_url, headers={"User-Agent": headers["User-Agent"]})
                    with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                        ctype = img_resp.headers.get("Content-Type", "")
                        body = img_resp.read()
                        img_hash = hashlib.sha256(body).hexdigest()[:24]
                        if "image" in ctype and len(body) > 15000 and img_hash not in seen:
                            _record_seen_photo(candidate_url, body, seen)
                            return body, candidate_url
                except Exception:
                    continue
        except Exception:
            continue

    # 3. Tertiary source: Wallhaven API (SFW portrait / model photography)
    try:
        wh_url = "https://wallhaven.cc/api/v1/search?q=asian+girl&categories=001&purity=100&sorting=random"
        req = urllib.request.Request(wh_url, headers={"User-Agent": headers["User-Agent"]})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            random.shuffle(items)
            for item in items:
                candidate_url = item.get("path", "")
                if candidate_url and candidate_url not in seen:
                    img_req = urllib.request.Request(candidate_url, headers={"User-Agent": headers["User-Agent"]})
                    with urllib.request.urlopen(img_req, timeout=12) as img_resp:
                        body = img_resp.read()
                        img_hash = hashlib.sha256(body).hexdigest()[:24]
                        if len(body) > 15000 and img_hash not in seen:
                            _record_seen_photo(candidate_url, body, seen)
                            return body, candidate_url
    except Exception:
        pass

    raise RuntimeError("Could not fetch a new unseen Vitamin photo.")


def _send_image_in_page(page, img_bytes: bytes, caption: str) -> None:
    """Paste an image directly into the Teams chat compose box and click the Send button."""
    compose = page.locator('[role="textbox"][contenteditable="true"]').first
    compose.click(timeout=20000)

    # Discard any stuck leftover draft in the compose box first
    try:
        discard = page.locator('[data-tid="newMessageCommands-discard-draft"]')
        if discard.count() > 0 and discard.first.is_visible():
            discard.first.click(timeout=3000)
            page.wait_for_timeout(800)
            compose.click(timeout=10000)
    except Exception:
        pass

    b64_img = base64.b64encode(img_bytes).decode("ascii")
    # Dispatch a synthetic paste event with image/jpeg File in DataTransfer
    compose.evaluate(
        """(el, b64) => {
            const bin = atob(b64);
            const arr = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
            const file = new File([arr], "vitamin_sea.jpg", { type: "image/jpeg" });
            const dt = new DataTransfer();
            dt.items.add(file);
            const evt = new ClipboardEvent("paste", {
                bubbles: true,
                cancelable: true,
                clipboardData: dt,
            });
            el.dispatchEvent(evt);
        }""",
        b64_img,
    )
    # Wait for Teams Web CKEditor to attach the inlineimage blob
    page.wait_for_timeout(3500)
    compose.click(timeout=10000)
    page.keyboard.insert_text(caption)
    page.wait_for_timeout(500)

    # When an inline image is present, Teams Web requires clicking newMessageCommands-send (or Ctrl+Enter) instead of plain Enter
    send_btn = page.locator('[data-tid="newMessageCommands-send"]')
    if send_btn.count() > 0:
        send_btn.first.click(timeout=10000)
    else:
        page.keyboard.press("Control+Enter")
        page.keyboard.press("Enter")
    page.wait_for_timeout(3000)


def _send_text_in_page(page, message: str) -> None:
    """Type a multi-line message into the active Teams compose box and press Enter."""
    compose = page.locator('[role="textbox"][contenteditable="true"]').first
    compose.click(timeout=20000)
    for i, line in enumerate(message.split("\n")):
        if i > 0:
            page.keyboard.press("Shift+Enter")
        if line:
            page.keyboard.insert_text(line)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)


def _get_latest_chat_message(page, chat_name: str = "") -> tuple[str, str]:
    """Scroll to the bottom of the Teams chat and return (msg_hash, msg_text) of the newest message."""
    # 1. Scroll virtualized chat list and all scrollable ancestors to the bottom so Teams mounts the newest message
    try:
        page.evaluate(
            """() => {
                document.querySelectorAll('[data-tid*="message-pane"], [data-tid*="virtual"], [role="log"], .fui-Chat').forEach(el => {
                    el.scrollTop = el.scrollHeight;
                });
                const msgs = document.querySelectorAll('[data-tid="chat-pane-message"], .fui-ChatMessage__body');
                if (msgs.length > 0) {
                    const last = msgs[msgs.length - 1];
                    last.scrollIntoView({ block: 'end' });
                    let p = last.parentElement;
                    while (p) {
                        if (p.scrollHeight > p.clientHeight) {
                            p.scrollTop = p.scrollHeight;
                        }
                        p = p.parentElement;
                    }
                }
                const jumpBtn = document.querySelector('[data-tid*="jump-to-bottom"], [data-tid*="new-messages"], button[aria-label*="new message"]');
                if (jumpBtn) jumpBtn.click();
            }"""
        )
    except Exception:
        pass

    pane_text = ""
    pane_count = 0
    selectors = [
        '[data-tid="chat-pane-message"]',
        '[data-tid="messageBodyContent"]',
        '.fui-ChatMessage__body',
    ]
    for sel in selectors:
        loc = page.locator(sel)
        count = loc.count()
        if count > 0:
            pane_count = count
            pane_text = loc.nth(count - 1).inner_text(timeout=5000).strip()
            if pane_text:
                break

    # 2. Check the left sidebar chat preview (which ALWAYS updates in real time on every new message, including our bot's own reply!)
    sidebar_text = ""
    if chat_name:
        try:
            items = page.locator('[role="treeitem"]')
            for i in range(min(items.count(), 12)):
                t = items.nth(i).inner_text(timeout=2000).strip()
                if chat_name.lower() in t.lower():
                    lines = [
                        ln.strip()
                        for ln in t.splitlines()
                        if ln.strip()
                        and ln.strip().lower() != "unread"
                        and not re.match(r"^(\d{1,2}:\d{2}(\s*[AP]M)?|just now|yesterday)$", ln.strip(), flags=re.IGNORECASE)
                    ]
                    for idx, ln in enumerate(lines):
                        if chat_name.lower() in ln.lower():
                            # Take the message preview line immediately following the chat title
                            preview_lines = lines[idx + 1 : idx + 2]
                            sidebar_text = " ".join(preview_lines).strip()
                            break
                    if sidebar_text:
                        break
        except Exception:
            pass

    # Always prefer sidebar_text when available so that when the bot replies ("You: 🌊 Vitamin..."),
    # msg_hash changes to the bot's reply hash, allowing the very next !girl command to be detected as new!
    if sidebar_text:
        msg_hash = hashlib.sha256(f"sidebar:{sidebar_text}".encode("utf-8")).hexdigest()[:16]
        return msg_hash, sidebar_text

    if pane_text:
        msg_hash = hashlib.sha256(f"{pane_count}:{pane_text}".encode("utf-8")).hexdigest()[:16]
        return msg_hash, pane_text

    return "", ""


def export_compact_secret() -> str:
    """Keep all Teams auth/session keys and only strip large non-chat caches so it fits in GitHub Secrets (<47 KB)."""
    import gzip
    import json

    if not SESSION_FILE.exists():
        print(f"ERROR: {SESSION_FILE} not found. Run --login first.", file=sys.stderr)
        sys.exit(1)

    skip_substrings = (
        "CDLSupportedResolvers",
        "policy-cache",
        "previousLoaderDiagnostics",
        "pendingSettingsForMigration",
        "M365COPILOTAPP",
        "m365copilotapp",
        "AUGLOOP",
        "augloop",
        "CONSENTSERVICE",
        "consentservice",
        "LIVEPROFILECARD",
        "liveprofilecard",
    )
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    slim_data = {
        "cookies": data.get("cookies", []),
        "origins": [
            {
                "origin": o["origin"],
                "localStorage": [
                    x
                    for x in o.get("localStorage", [])
                    if not any(s in x["name"] for s in skip_substrings)
                ],
            }
            for o in data.get("origins", [])
        ],
    }
    raw_bytes = json.dumps(slim_data, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw_bytes, compresslevel=9)
    b64_str = base64.b64encode(compressed).decode("ascii")

    out_path = SESSION_FILE.parent / "teams_session_b64.txt"
    out_path.write_text(b64_str, encoding="utf-8")
    print(f"✅ Generated compact secret ({len(b64_str)} chars, <48 KB limit)!")
    print(f"📄 Saved to: {out_path}")
    return b64_str


def save_login_session() -> None:
    """Open browser once so you can log in with your free @outlook.com Weather Bot account."""
    from playwright.sync_api import sync_playwright

    print("Opening browser to https://teams.live.com ...")
    print("1. Log in with your free @outlook.com Weather Bot account.")
    print("2. Click into your target Group Chat so it is open on screen.")
    print("3. Come back to this terminal and press ENTER to save the session.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://teams.live.com")
        input("\n>>> Press ENTER here AFTER you have clicked into your Teams chat... ")
        context.storage_state(path=str(SESSION_FILE))
        browser.close()

    print(f"\n✅ Saved raw session to {SESSION_FILE}")
    export_compact_secret()


def _ensure_session_file() -> None:
    import gzip

    env_b64 = os.environ.get("TEAMS_SESSION_B64", "").strip()
    if env_b64:
        raw = base64.b64decode(env_b64)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        SESSION_FILE.write_bytes(raw)
    if not SESSION_FILE.exists():
        print("ERROR: Session file not found. Run `python3 teams_web_sender.py --login` once first.", file=sys.stderr)
        sys.exit(1)


def _open_target_chat(page, chat_name: str) -> None:
    """Wait for Teams Web to load and select chat_name (or use the already-open active chat from session)."""
    print("⏳ Waiting for Teams Web interface to load...")
    page.wait_for_timeout(8000)

    if chat_name:
        try:
            page.get_by_text(chat_name, exact=False).first.click(timeout=15000)
            print(f"✅ Clicked chat matching '{chat_name}'")
            page.wait_for_timeout(2000)
            return
        except Exception:
            print(f"ℹ️ Could not find chat title '{chat_name}' in sidebar; checking if chat compose box is already open...")

    # Check if compose box is already active (Teams remembers last open chat 19:1ed6928a...@thread.v2 in localStorage!)
    compose = page.locator('[role="textbox"][contenteditable="true"]')
    if compose.count() > 0:
        print("✅ Active chat compose box is already open!")
        return

    # Otherwise click the first chat item in the left sidebar
    first_chat = page.locator('[role="treeitem"], [data-tid*="chat-list-item"]').first
    first_chat.click(timeout=15000)
    page.wait_for_timeout(2000)
    print("✅ Clicked first chat in sidebar!")


def send_via_teams_web(chat_name: str, message: str) -> None:
    """Use saved @outlook.com session in headless Chromium to post message in Teams chat."""
    from playwright.sync_api import sync_playwright

    _ensure_session_file()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        page.goto("https://teams.live.com", wait_until="domcontentloaded", timeout=60000)

        _open_target_chat(page, chat_name)
        _send_text_in_page(page, message)

        context.storage_state(path=str(SESSION_FILE))
        browser.close()
        print(f"✅ Successfully sent TTC & FPT Software weather alert to chat!")


def listen_for_mentions(
    chat_name: str,
    bot_name: str,
    one_shot: bool = False,
    poll_interval: int = 3,
    start_server: bool = True,
    max_minutes: int = 0,
    headless: bool = True,
) -> None:
    """Watch the Teams chat 24/7: reply to @mentions AND auto-send rain alerts during work hours."""
    from playwright.sync_api import sync_playwright

    _ensure_session_file()
    if not one_shot and start_server:
        start_health_server()

    last_replied = LAST_REPLIED_FILE.read_text().strip() if LAST_REPLIED_FILE.exists() else ""
    # Initialize to current time so starting --listen doesn't immediately trigger a redundant commute check
    last_auto_alert_ts = time.time()
    last_vitamin_ts = 0.0
    vitamin_cooldown_sec = int(os.environ.get("VITAMIN_COOLDOWN_SEC", "15"))
    start_ts = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            storage_state=str(SESSION_FILE),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://teams.live.com", wait_until="domcontentloaded", timeout=60000)
        _open_target_chat(page, chat_name)

        print(
            f"👂 Listening for @mentions ('{bot_name}', !weather, !girl, !vitaminSea)..."
            if not one_shot
            else f"🔍 Checking for new @mentions..."
        )
        _, initial_msg = _get_latest_chat_message(page, chat_name)
        print(f"💬 Latest message currently visible in chat: {initial_msg[:120]!r}")

        while True:
            try:
                # 1. Check if someone typed !vitaminSea / !girl or tagged @Weather Bot in the chat
                msg_hash, msg_text = _get_latest_chat_message(page, chat_name)
                if msg_hash and msg_hash != last_replied:
                    if is_vitamin_sea_command(msg_text):
                        elapsed = time.time() - last_vitamin_ts
                        if elapsed < vitamin_cooldown_sec:
                            wait_left = int(vitamin_cooldown_sec - elapsed)
                            print(f"[{datetime.now(VN_TZ).isoformat()}] ⏳ Anti-spam cooldown active ({wait_left}s left), ignoring !girl.")
                            last_replied = msg_hash
                            LAST_REPLIED_FILE.write_text(last_replied)
                        else:
                            print(f"[{datetime.now(VN_TZ).isoformat()}] 🌊 Detected !girl / !vitaminSea command: {msg_text!r}")
                            last_replied = msg_hash
                            LAST_REPLIED_FILE.write_text(last_replied)
                            img_bytes, img_url = fetch_vitamin_sea_photo(context)
                            caption = "🌊 Vitamin Gái Xinh VOZ tiếp thêm năng lượng code cho anh em! ✨"
                            _send_image_in_page(page, img_bytes, caption)
                            last_vitamin_ts = time.time()
                            # Update last_replied to our sent reply so the next !girl from the same user has a new msg_hash
                            new_hash, _ = _get_latest_chat_message(page, chat_name)
                            if new_hash:
                                last_replied = new_hash
                                LAST_REPLIED_FILE.write_text(last_replied)
                            print(f"[{datetime.now(VN_TZ).isoformat()}] ✅ Sent VOZ photo ({img_url})!")
                    elif is_bot_mentioned(msg_text, bot_name):
                        print(f"[{datetime.now(VN_TZ).isoformat()}] 🔔 Detected bot tag: {msg_text!r}")
                        last_replied = msg_hash
                        LAST_REPLIED_FILE.write_text(last_replied)
                        locs = filter_locations_from_query(msg_text)
                        results = fetch_all_locations(locs)
                        reply = format_multi_location_message(results, triggered_by="On-demand reply")
                        _send_text_in_page(page, reply)
                        new_hash, _ = _get_latest_chat_message(page, chat_name)
                        if new_hash:
                            last_replied = new_hash
                            LAST_REPLIED_FILE.write_text(last_replied)
                        print(f"[{datetime.now(VN_TZ).isoformat()}] ✅ Replied with live weather!")
                    else:
                        # Update last_replied when a normal message or our own bot reply becomes the latest message
                        last_replied = msg_hash
                        LAST_REPLIED_FILE.write_text(last_replied)

                # 2. Automatic rain check during commute hours (07:00-08:30 and 16:00-17:30 VN time, Mon-Fri)
                now_vn = datetime.now(VN_TZ)
                is_weekday = now_vn.weekday() < 5
                is_commute_window = (7 <= now_vn.hour <= 8) or (16 <= now_vn.hour <= 17)
                if not one_shot and is_weekday and is_commute_window and (time.time() - last_auto_alert_ts > 4 * 3600):
                    last_auto_alert_ts = time.time()
                    results = fetch_all_locations(LOCATIONS)
                    if any(r["analysis"]["is_alert"] for r in results):
                        alert_msg = format_multi_location_message(results, triggered_by="Commute Rain Alert")
                        _send_text_in_page(page, alert_msg)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[{datetime.now(VN_TZ).isoformat()}] Warning during poll: {e}", file=sys.stderr)

            if one_shot:
                break
            if max_minutes > 0 and (time.time() - start_ts) >= max_minutes * 60:
                print(f"⏱️ Reached {max_minutes} minutes limit; exiting cleanly for next scheduled cloud run.")
                break
            time.sleep(poll_interval)

        context.storage_state(path=str(SESSION_FILE))
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Send TTC & FPT Software Weather Alert & Reply to @Mentions")
    parser.add_argument("--login", action="store_true", help="Log in once interactively to save session")
    parser.add_argument("--export-secret", action="store_true", help="Export compact <48KB base64 secret from existing teams_session.json")
    parser.add_argument("--chat-name", default=os.environ.get("TEAMS_CHAT_NAME", "Bảo vệ Ép (backup)"), help="Name of the Teams Group Chat")
    parser.add_argument("--bot-name", default=os.environ.get("TEAMS_BOT_NAME", "Weather B"), help="Display name of your bot account when @mentioned")
    parser.add_argument("--listen", action="store_true", help="Continuously watch chat and reply immediately when someone tags @Weather Bot")
    parser.add_argument("--headed", action="store_true", help="Show browser window while listening (for local debugging)")
    parser.add_argument("--max-minutes", type=int, default=0, help="Stop listener cleanly after N minutes (for GitHub Actions)")
    parser.add_argument("--check-mentions", action="store_true", help="Check once if the latest message tagged @Weather Bot and reply")
    parser.add_argument("--force", action="store_true", help="Send even if weather is clear at both locations")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted message without sending")
    args = parser.parse_args()

    if args.login:
        save_login_session()
        return

    if args.export_secret:
        export_compact_secret()
        return

    if args.dry_run:
        results = fetch_all_locations(LOCATIONS)
        print(format_multi_location_message(results))
        return

    if args.listen or args.check_mentions:
        listen_for_mentions(
            args.chat_name,
            args.bot_name,
            one_shot=args.check_mentions,
            max_minutes=args.max_minutes,
            headless=not args.headed,
        )
        return

    results = fetch_all_locations(LOCATIONS)
    any_alert = any(r["analysis"]["is_alert"] for r in results)

    if not any_alert and not args.force:
        print("Weather is clear at both TTC and FPT Software TP.HCM. No alert sent.")
        return

    msg = format_multi_location_message(results)
    send_via_teams_web(args.chat_name, msg)


if __name__ == "__main__":
    main()
