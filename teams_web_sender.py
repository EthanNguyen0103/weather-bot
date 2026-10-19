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
BOT_TRIGGERS = ["@weather", "weather bot", "!weather", "/weather", "thời tiết", "thoi tiet"]


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
            pass  # Silence HTTP health check logs

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
            f"   Now: {a['current_icon']} {a['current_desc']} | "
            f"{a['current_temp']}°C (Feels like {a['feels_like']}°C) | "
            f"💧 {a['humidity']}% | 💨 {a['wind']} km/h"
        )
        if a["upcoming_alerts"]:
            lines.append("   ☔ Upcoming Bad Weather (Next 6h):")
            for alert in a["upcoming_alerts"][:3]:
                clean = alert.replace("**", "")
                lines.append(f"     • {clean}")

        lines.append("   🕒 Next 6 Hours Forecast:")
        for r in a["forecast_rows"]:
            lines.append(
                f"     • {r['time']}: {r['condition']} | {r['temp']} | ☔ {r['rain_prob']} ({r['precip']})"
            )
        lines.append("")

    lines.append("🔔 Tip: Tag @Weather Bot (or type !weather, !weather ttc, !weather fpt) anytime for a live update!")
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
    if "🌊 vitamin sea" in lower:
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


def fetch_vitamin_sea_photo() -> tuple[bytes, str]:
    """Fetch a random beach/summer portrait photo (bytes + source URL) without requiring an API key."""
    import json
    import random
    import urllib.request

    queries = [
        "asian+woman+beach+summer+portrait",
        "korean+girl+beach+vacation+portrait",
        "vietnam+beach+girl+summer+portrait",
        "fashion+model+beach+sunset+portrait",
    ]
    q = random.choice(queries)
    page_num = random.randint(1, 5)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/125.0.0.0 Safari/537.36"}

    img_url = ""
    # 1. Try Unsplash public JSON search
    try:
        search_url = f"https://unsplash.com/napi/search/photos?query={q}&per_page=20&page={page_num}"
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                chosen = random.choice(results)
                img_url = chosen.get("urls", {}).get("regular", "")
    except Exception:
        pass

    # 2. Fallback to Wallhaven SFW People/Beach search
    if not img_url:
        try:
            wh_url = "https://wallhaven.cc/api/v1/search?q=beach+girl&categories=001&purity=100&sorting=random"
            req = urllib.request.Request(wh_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("data", [])
                if results:
                    img_url = random.choice(results).get("path", "")
        except Exception:
            pass

    if not img_url:
        raise RuntimeError("Could not fetch a Vitamin Sea photo URL.")

    img_req = urllib.request.Request(img_url, headers=headers)
    with urllib.request.urlopen(img_req, timeout=15) as resp:
        return resp.read(), img_url


def _send_image_in_page(page, img_bytes: bytes, caption: str) -> None:
    """Paste an image directly into the Teams chat compose box and send it inline with a caption."""
    compose = page.locator('[role="textbox"][contenteditable="true"]').first
    compose.click(timeout=20000)

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
    # Wait for Teams Web to upload & attach the pasted image thumbnail
    page.wait_for_timeout(4500)
    page.keyboard.insert_text(caption)
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


def _get_latest_chat_message(page) -> tuple[str, str]:
    """Return (msg_hash, msg_text) of the most recent message in the currently open Teams chat."""
    selectors = [
        '[data-tid="chat-pane-message"]',
        '[data-tid="messageBodyContent"]',
        '.fui-ChatMessage__body',
    ]
    for sel in selectors:
        loc = page.locator(sel)
        count = loc.count()
        if count > 0:
            last_text = loc.nth(count - 1).inner_text(timeout=5000).strip()
            if last_text:
                msg_hash = hashlib.sha256(last_text.encode("utf-8")).hexdigest()[:16]
                return msg_hash, last_text
    return "", ""


def export_compact_secret() -> str:
    """Strip temporary React cache keys and gzip-compress teams_session.json so it easily fits in GitHub Secrets (<22 KB)."""
    import gzip
    import json

    if not SESSION_FILE.exists():
        print(f"ERROR: {SESSION_FILE} not found. Run --login first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    slim_data = {
        "cookies": data.get("cookies", []),
        "origins": [
            {
                "origin": o["origin"],
                "localStorage": [
                    x
                    for x in o.get("localStorage", [])
                    if not x["name"].startswith("tmp.") and "|accesstoken|" not in x["name"]
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
    print(f"✅ Generated compact secret ({len(b64_str)} chars, down from ~229,000 chars)!")
    print(f"📄 Saved to: {out_path}")
    return b64_str


def save_login_session() -> None:
    """Open browser once so you can log in with your free @outlook.com Weather Bot account."""
    from playwright.sync_api import sync_playwright

    print("Opening browser to https://teams.live.com ...")
1.     print("Log in with your free @outlook.com Weather Bot account.
")
    print("2. Wait until your Teams chat list finishes loading.")
    print("3. Come back to this terminal and press ENTER to save the session.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://teams.live.com")
        input("\n>>> Press ENTER here AFTER Teams chats have loaded in the browser... ")
        context.storage_state(path=str(SESSION_FILE))
        browser.close()

    print(f"\n✅ Saved raw session to {SESSION_FILE}")
    export_compact_secret()


def _ensure_session_file() -> None:
    import gzip

    env_b64 = os.environ.get("TEAMS_SESSION_B64", "").strip()
    if env_b64:
        raw = base64.b64decode(env_b64)
        # Automatically decompress if gzipped (starts with 0x1f 0x8b)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        SESSION_FILE.write_bytes(raw)
    if not SESSION_FILE.exists():
        print("ERROR: Session file not found. Run `python3 teams_web_sender.py --login` once first.", file=sys.stderr)
        sys.exit(1)


def send_via_teams_web(chat_name: str, message: str) -> None:
    """Use saved @outlook.com session in headless Chromium to post message in Teams chat."""
    from playwright.sync_api import sync_playwright

    _ensure_session_file()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        page.goto("https://teams.live.com", wait_until="domcontentloaded", timeout=60000)

        page.get_by_text(chat_name, exact=False).first.click(timeout=45000)
        _send_text_in_page(page, message)

        context.storage_state(path=str(SESSION_FILE))
        browser.close()
        print(f"✅ Successfully sent TTC & FPT Software weather alert to chat '{chat_name}'!")


def listen_for_mentions(
    chat_name: str,
    bot_name: str,
    one_shot: bool = False,
    poll_interval: int = 8,
    start_server: bool = True,
    max_minutes: int = 0,
) -> None:
    """Watch the Teams chat 24/7: reply to @mentions AND auto-send rain alerts during work hours."""
    from playwright.sync_api import sync_playwright

    _ensure_session_file()
    if not one_shot and start_server:
        start_health_server()

    last_replied = LAST_REPLIED_FILE.read_text().strip() if LAST_REPLIED_FILE.exists() else ""
    last_auto_alert_ts = 0.0
    start_ts = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        page.goto("https://teams.live.com", wait_until="domcontentloaded", timeout=60000)
        page.get_by_text(chat_name, exact=False).first.click(timeout=45000)
        page.wait_for_timeout(3000)

        print(
            f"👂 Listening for @mentions ('{bot_name}', !weather) + rain alerts in '{chat_name}'..."
            if not one_shot
            else f"🔍 Checking for new @mentions in chat '{chat_name}'..."
        )

        while True:
            try:
                # 1. Check if someone typed !vitaminSea or tagged @Weather Bot in the chat
                msg_hash, msg_text = _get_latest_chat_message(page)
                if msg_hash and msg_hash != last_replied:
                    if is_vitamin_sea_command(msg_text):
                        print(f"[{datetime.now(VN_TZ).isoformat()}] 🌊 Detected !vitaminSea command: {msg_text!r}")
                        img_bytes, img_url = fetch_vitamin_sea_photo()
                        caption = "🌊 Vitamin Sea tiếp thêm năng lượng code cho anh em! 🏖️✨"
                        _send_image_in_page(page, img_bytes, caption)
                        last_replied = msg_hash
                        LAST_REPLIED_FILE.write_text(last_replied)
                        print(f"[{datetime.now(VN_TZ).isoformat()}] ✅ Sent Vitamin Sea photo ({img_url})!")
                    elif is_bot_mentioned(msg_text, bot_name):
                        print(f"[{datetime.now(VN_TZ).isoformat()}] 🔔 Detected bot tag: {msg_text!r}")
                        locs = filter_locations_from_query(msg_text)
                        results = fetch_all_locations(locs)
                        reply = format_multi_location_message(results, triggered_by="On-demand reply")
                        _send_text_in_page(page, reply)

                        last_replied = msg_hash
                        LAST_REPLIED_FILE.write_text(last_replied)
                        print(f"[{datetime.now(VN_TZ).isoformat()}] ✅ Replied with live weather!")

                # 2. Automatic rain check during commute hours (07:00-08:30 and 16:00-17:30 VN time, Mon-Fri)
                now_vn = datetime.now(VN_TZ)
                is_weekday = now_vn.weekday() < 5
                is_commute_window = (7 <= now_vn.hour <= 8) or (16 <= now_vn.hour <= 17)
                if not one_shot and is_weekday and is_commute_window and (time.time() - last_auto_alert_ts > 4 * 3600):
                    results = fetch_all_locations(LOCATIONS)
                    if any(r["analysis"]["is_alert"] for r in results):
                        alert_msg = format_multi_location_message(results, triggered_by="Commute Rain Alert")
                        _send_text_in_page(page, alert_msg)
                        last_auto_alert_ts = time.time()

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
    parser.add_argument("--export-secret", action="store_true", help="Export compact <22KB base64 secret from existing teams_session.json")
    parser.add_argument("--chat-name", default=os.environ.get("TEAMS_CHAT_NAME", ""), help="Name of the Teams Group Chat")
    parser.add_argument("--bot-name", default=os.environ.get("TEAMS_BOT_NAME", "Weather Bot"), help="Display name of your bot account when @mentioned")
    parser.add_argument("--listen", action="store_true", help="Continuously watch chat and reply immediately when someone tags @Weather Bot")
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

    if not args.chat_name:
        print("ERROR: Please specify --chat-name 'Your Chat Name' or set TEAMS_CHAT_NAME", file=sys.stderr)
        sys.exit(1)

    if args.listen or args.check_mentions:
        listen_for_mentions(
            args.chat_name,
            args.bot_name,
            one_shot=args.check_mentions,
            max_minutes=args.max_minutes,
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