#!/usr/bin/env python3
"""
MS Teams Weather Alert Bot (No IT Admin Required)
Checks weather for ONLY 2 locations:
  1. TTC (Tan Thuan Tower, District 7, HCMC): https://maps.app.goo.gl/tmwUAMxbKQkgUkW76
  2. FPT Software TP.HCM (Saigon Hi-Tech Park, Thu Duc): https://maps.app.goo.gl/2VwrEjnVmk2TSabp7
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DEFAULT_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "YOUR_POWER_AUTOMATE_WEBHOOK_URL_HERE")

LOCATIONS = [
    {
        "name": "TTC (Tan Thuan Tower)",
        "lat": 10.7537535,
        "lon": 106.7312552,
        "map_url": "https://maps.app.goo.gl/tmwUAMxbKQkgUkW76",
    },
    {
        "name": "FPT Software TP.HCM",
        "lat": 10.8508885,
        "lon": 106.7983267,
        "map_url": "https://maps.app.goo.gl/2VwrEjnVmk2TSabp7",
    },
]

# Optional list of users to @mention in Teams Adaptive Card
MENTION_USERS = [
    # {"name": "Alice Nguyen", "email": "alice@company.com"},
]

# Rain / Bad weather thresholds
RAIN_PROB_THRESHOLD = 50       # % probability of precipitation in the next hours
RAIN_MM_THRESHOLD = 0.5        # mm of precipitation
HIGH_TEMP_THRESHOLD = 37.0     # °C extreme heat alert
HOURS_AHEAD_TO_CHECK = 6       # Check forecast for the next N hours

# WMO Weather interpretation codes (https://open-meteo.com/en/docs)
WMO_CODES = {
    0: ("Clear sky", "☀️", False),
    1: ("Mainly clear", "🌤️", False),
    2: ("Partly cloudy", "⛅", False),
    3: ("Overcast", "☁️", False),
    45: ("Foggy", "🌫️", False),
    48: ("Depositing rime fog", "🌫️", False),
    51: ("Light drizzle", "🌦️", True),
    53: ("Moderate drizzle", "🌦️", True),
    55: ("Dense drizzle", "🌧️", True),
    56: ("Light freezing drizzle", "🌧️", True),
    57: ("Dense freezing drizzle", "🌧️", True),
    61: ("Slight rain", "🌦️", True),
    63: ("Moderate rain", "🌧️", True),
    65: ("Heavy rain", "⛈️", True),
    66: ("Light freezing rain", "🌧️", True),
    67: ("Heavy freezing rain", "⛈️", True),
    71: ("Slight snow fall", "🌨️", True),
    73: ("Moderate snow fall", "❄️", True),
    75: ("Heavy snow fall", "❄️", True),
    80: ("Slight rain showers", "🌦️", True),
    81: ("Moderate rain showers", "🌧️", True),
    82: ("Violent rain showers", "⛈️", True),
    95: ("Thunderstorm", "⛈️", True),
    96: ("Thunderstorm with slight hail", "⛈️", True),
    99: ("Thunderstorm with heavy hail", "⛈️", True),
}


def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch current and hourly forecast from Open-Meteo (No API key needed)."""
    import time

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
        f"&hourly=temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m"
        f"&timezone=auto&forecast_days=2"
    )
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TeamsWeatherBot/1.0"})
            with urllib.request.urlopen(req, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def analyze_weather(data: dict, hours_ahead: int = HOURS_AHEAD_TO_CHECK) -> dict:
    """Analyze current and upcoming hourly weather for bad weather alerts."""
    current = data["current"]
    hourly = data["hourly"]
    curr_time_str = current["time"]

    curr_code = current.get("weather_code", 0)
    curr_desc, curr_icon, curr_is_bad = WMO_CODES.get(curr_code, ("Unknown", "🌡️", False))

    times = hourly["time"]
    start_idx = 0
    for idx, t in enumerate(times):
        if t >= curr_time_str:
            start_idx = idx
            break

    upcoming_alerts = []
    forecast_rows = []
    is_alert = curr_is_bad or current.get("temperature_2m", 0) >= HIGH_TEMP_THRESHOLD

    if curr_is_bad:
        upcoming_alerts.append(
            f"Current: **{curr_icon} {curr_desc}** ({current.get('precipitation', 0)} mm)"
        )

    for i in range(start_idx, min(start_idx + hours_ahead, len(times))):
        t_str = times[i].split("T")[1]
        temp = hourly["temperature_2m"][i]
        prob = hourly["precipitation_probability"][i] or 0
        precip = hourly["precipitation"][i] or 0.0
        w_code = hourly["weather_code"][i]
        desc, icon, code_bad = WMO_CODES.get(w_code, ("Unknown", "🌡️", False))

        row_bad = (
            code_bad
            or prob >= RAIN_PROB_THRESHOLD
            or precip >= RAIN_MM_THRESHOLD
            or temp >= HIGH_TEMP_THRESHOLD
        )
        if row_bad:
            is_alert = True
            upcoming_alerts.append(
                f"**{t_str}**: {icon} {desc} — Rain prob: **{prob}%** ({precip} mm), {temp}°C"
            )

        forecast_rows.append({
            "time": t_str,
            "temp": f"{temp}°C",
            "condition": f"{icon} {desc}",
            "rain_prob": f"{prob}%",
            "precip": f"{precip} mm",
        })

    return {
        "is_alert": is_alert,
        "current_temp": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "wind": current.get("wind_speed_10m"),
        "current_desc": curr_desc,
        "current_icon": curr_icon,
        "upcoming_alerts": upcoming_alerts,
        "forecast_rows": forecast_rows,
    }


def fetch_all_locations(locations: list = None) -> list:
    """Fetch and analyze weather for all configured locations."""
    if locations is None:
        locations = LOCATIONS
    results = []
    for loc in locations:
        raw = fetch_weather(loc["lat"], loc["lon"])
        analysis = analyze_weather(raw)
        results.append({
            "name": loc["name"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "map_url": loc["map_url"],
            "analysis": analysis,
        })
    return results


def build_multi_location_payload(results: list, mentions: list) -> dict:
    """Build combined Adaptive Card and HTML message for TTC & FPT Software."""
    any_alert = any(r["analysis"]["is_alert"] for r in results)
    mention_texts = []
    mention_entities = []
    for user in mentions:
        tag = f"<at>{user['name']}</at>"
        mention_texts.append(tag)
        mention_entities.append({
            "type": "mention",
            "text": tag,
            "mentioned": {
                "id": user["email"],
                "name": user["name"],
            },
        })

    header_color = "Attention" if any_alert else "Accent"
    title_prefix = "⚠️ WEATHER ALERT" if any_alert else "🌤️ Weather Update"

    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "color": header_color,
            "text": f"{title_prefix} — TTC & FPT Software",
            "wrap": True,
        }
    ]

    html_sections = [f"<h3>{title_prefix} — TTC &amp; FPT Software</h3>"]

    for item in results:
        loc_name = item["name"]
        map_url = item["map_url"]
        a = item["analysis"]
        status_badge = "⚠️ Alert" if a["is_alert"] else "✅ Clear"

        body.append({
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "text": f"📍 [{loc_name}]({map_url}) ({status_badge})",
            "wrap": True,
            "separator": True,
        })
        body.append({
            "type": "TextBlock",
            "text": (
                f"**Now:** {a['current_icon']} {a['current_desc']} | "
                f"**{a['current_temp']}°C** (Feels like {a['feels_like']}°C) | "
                f"💧 {a['humidity']}% | 💨 {a['wind']} km/h"
            ),
            "wrap": True,
        })

        if a["upcoming_alerts"]:
            alert_lines = "\n".join(f"- {al}" for al in a["upcoming_alerts"][:3])
            body.append({
                "type": "TextBlock",
                "color": "Attention",
                "text": f"☔ **Upcoming Bad Weather:**\n{alert_lines}",
                "wrap": True,
            })

        facts = [
            {
                "title": row["time"],
                "value": f"{row['condition']} | {row['temp']} | ☔ {row['rain_prob']} ({row['precip']})",
            }
            for row in a["forecast_rows"]
        ]
        body.append({"type": "FactSet", "facts": facts})

        # HTML section for "Post message in a chat or channel"
        html_rows = "".join(
            f"<li><b>{r['time']}</b>: {r['condition']} | <b>{r['temp']}</b> | ☔ Rain: {r['rain_prob']} ({r['precip']})</li>"
            for r in a["forecast_rows"]
        )
        html_alert = ""
        if a["upcoming_alerts"]:
            items_html = "".join(f"<li>{al}</li>" for al in a["upcoming_alerts"][:3])
            html_alert = f"<p><b>☔ Upcoming Bad Weather:</b><ul>{items_html}</ul></p>"

        html_sections.append(
            f"<h4>📍 <a href='{map_url}'>{loc_name}</a> ({status_badge})</h4>"
            f"<p><b>Now:</b> {a['current_icon']} {a['current_desc']} | "
            f"<b>{a['current_temp']}°C</b> (Feels like {a['feels_like']}°C) | "
            f"💧 {a['humidity']}% | 💨 {a['wind']} km/h</p>"
            f"{html_alert}"
            f"<p><b>Next 6 Hours Forecast:</b><ul>{html_rows}</ul></p>"
        )

    if mention_texts:
        body.append({
            "type": "TextBlock",
            "text": "🔔 Ping: " + " ".join(mention_texts) + " — Don't forget your umbrella/raincoat!",
            "wrap": True,
        })
    else:
        body.append({
            "type": "TextBlock",
            "text": "🔔 **Heads up team!** Remember to bring an umbrella or raincoat if commuting between TTC & FPT Software.",
            "wrap": True,
            "isSubtle": True,
        })

    html_sections.append(
        "<p>🔔 <i>Heads up team! Remember to bring an umbrella or raincoat if commuting between TTC &amp; FPT Software.</i></p>"
    )
    html_message = "".join(html_sections)

    return {
        "type": "message",
        "message": html_message,
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "message": html_message,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                    "msteams": {
                        "entities": mention_entities,
                    },
                },
            }
        ],
    }


def get_az_cli_token() -> str:
    """Try to automatically fetch a Power Automate OAuth token via Azure CLI if logged in."""
    try:
        res = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "https://service.flow.microsoft.com/",
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def send_to_teams(webhook_url: str, payload: dict, bearer_token: str = "") -> None:
    """POST the Adaptive Card JSON to the Power Automate Teams Webhook URL."""
    headers = {"Content-Type": "application/json"}

    if "sig=" not in webhook_url and not bearer_token:
        bearer_token = get_az_cli_token()

    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    elif "sig=" not in webhook_url:
        print(
            "⚠️ WARNING: Your URL is a tenant-restricted URL (no '&sig=...' parameter) and no Bearer token was provided.\n",
            file=sys.stderr,
        )

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[{datetime.now().isoformat()}] Successfully sent alert to Teams (HTTP {resp.status}).")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP Error {e.code} ({e.reason}) from Power Automate:", file=sys.stderr)
        print(err_body, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="MS Teams Weather Alert Bot for TTC & FPT Software")
    parser.add_argument("--webhook", default=DEFAULT_WEBHOOK_URL, help="Teams Power Automate Webhook URL")
    parser.add_argument("--token", default=os.environ.get("TEAMS_BEARER_TOKEN", ""), help="Optional OAuth Bearer token")
    parser.add_argument("--force", action="store_true", help="Send message even if weather is good (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending to Teams")
    args = parser.parse_args()

    results = fetch_all_locations(LOCATIONS)
    any_alert = any(r["analysis"]["is_alert"] for r in results)

    if not any_alert and not args.force:
        summary = ", ".join(
            f"{r['name']}: {r['analysis']['current_desc']} ({r['analysis']['current_temp']}°C)"
            for r in results
        )
        print(f"[{datetime.now().isoformat()}] Weather is clear at both locations ({summary}). No alert sent.")
        return

    payload = build_multi_location_payload(results, MENTION_USERS)

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not args.webhook or args.webhook == "YOUR_POWER_AUTOMATE_WEBHOOK_URL_HERE":
        print("ERROR: Please set TEAMS_WEBHOOK_URL or pass --webhook <URL>", file=sys.stderr)
        sys.exit(1)

    send_to_teams(args.webhook, payload, args.token)


if __name__ == "__main__":
    main()
