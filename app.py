#!/usr/bin/env python3
"""
Hugging Face FREE Gradio Space Entrypoint (app.py)
Runs on the 100% Free Gradio SDK (No Pro subscription required!).
Automatically installs Chromium on startup and runs the 24/7 Teams Weather Bot listener.
"""

import os
import subprocess
import sys
import threading
import time
import gradio as gr

from weather_bot import LOCATIONS, fetch_all_locations
from teams_web_sender import (
    format_multi_location_message,
    listen_for_mentions,
    send_via_teams_web,
)

BOT_STATUS = "Starting up..."


def background_worker():
    global BOT_STATUS
    BOT_STATUS = "Installing Playwright Chromium browser..."
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

    chat_name = os.environ.get("TEAMS_CHAT_NAME", "").strip()
    bot_name = os.environ.get("TEAMS_BOT_NAME", "Weather Bot").strip()
    session_b64 = os.environ.get("TEAMS_SESSION_B64", "").strip()

    if not chat_name or not session_b64:
        BOT_STATUS = "⚠️ Waiting for TEAMS_CHAT_NAME and TEAMS_SESSION_B64 secrets in Space Settings..."
        return

    while True:
        try:
            BOT_STATUS = f"🟢 Online — Listening 24/7 in chat '{chat_name}' for @{bot_name} / !weather"
            listen_for_mentions(chat_name, bot_name, one_shot=False, start_server=False)
        except Exception as e:
            BOT_STATUS = f"🔄 Reconnecting after error: {e}"
            time.sleep(15)


def check_live_weather():
    results = fetch_all_locations(LOCATIONS)
    return format_multi_location_message(results), BOT_STATUS


def force_send_now():
    chat_name = os.environ.get("TEAMS_CHAT_NAME", "").strip()
    if not chat_name:
        return "❌ Please set TEAMS_CHAT_NAME secret first.", BOT_STATUS
    results = fetch_all_locations(LOCATIONS)
    msg = format_multi_location_message(results, triggered_by="Manual Cloud Trigger")
    send_via_teams_web(chat_name, msg)
    return f"✅ Sent to Teams chat '{chat_name}'!\n\n{msg}", BOT_STATUS


# Start the 24/7 Teams listener thread
threading.Thread(target=background_worker, daemon=True).start()

with gr.Blocks(title="Teams Weather Bot — TTC & FPT Software") as demo:
    gr.Markdown("## 🌤️ MS Teams Weather Bot (TTC & FPT Software TP.HCM)")
    status_box = gr.Textbox(label="24/7 Listener Status", value=BOT_STATUS, interactive=False)
    output_box = gr.Textbox(label="Live Forecast Preview (TTC & FPT Software)", lines=16)

    with gr.Row():
        btn_preview = gr.Button("🔄 Refresh Weather Preview")
        btn_send = gr.Button("📨 Force Send Alert to Teams Chat Now", variant="primary")

    btn_preview.click(fn=check_live_weather, outputs=[output_box, status_box])
    btn_send.click(fn=force_send_now, outputs=[output_box, status_box])
    demo.load(fn=check_live_weather, outputs=[output_box, status_box])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")))

