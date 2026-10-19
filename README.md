# MS Teams Weather Alert Bot (TTC & FPT Software TP.HCM)

This bot checks upcoming weather (next 6 hours) using the free **Open-Meteo API** (no API key needed) for **only 2 locations**:

1. **TTC (Tan Thuan Tower, District 7, HCMC)**
   - Coordinates: `10.7537535, 106.7312552`
   - Google Maps: <https://maps.app.goo.gl/tmwUAMxbKQkgUkW76>
2. **FPT Software TP.HCM (Saigon Hi-Tech Park, Thu Duc)**
   - Coordinates: `10.8508885, 106.7983267`
   - Google Maps: <https://maps.app.goo.gl/2VwrEjnVmk2TSabp7>

It **only pings your MS Teams chat when rain, thunderstorms, or extreme heat are forecast at either location** (or anytime you pass `--force`).

---

## Option A: Run via Free `@outlook.com` Bot Account + GitHub Actions (No Local PC Needed)

1. Install Playwright in WSL:
   ```bash
   pip install --break-system-packages playwright
   python3 -m playwright install chromium
   sudo apt-get update && sudo apt-get install -y libnspr4 libnss3 libasound2t64
   ```
2. Log in once with your `@outlook.com` Weather Bot account:
   ```bash
   python3 /home/nguyen/teams-weather-bot/teams_web_sender.py --login
   ```
3. Preview the combined message for **TTC & FPT Software TP.HCM**:
   ```bash
   python3 /home/nguyen/teams-weather-bot/teams_web_sender.py --dry-run --force
   ```
4. Test sending to your Teams chat:
   ```bash
   python3 /home/nguyen/teams-weather-bot/teams_web_sender.py --chat-name "Your Group Chat Name" --force
   ```
5. Push to a private GitHub repository and add `TEAMS_SESSION_B64` and `TEAMS_CHAT_NAME` to **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.

---

## Option B: Run via Power Automate Webhook ([`weather_bot.py`](./weather_bot.py))

```bash
python3 /home/nguyen/teams-weather-bot/weather_bot.py \
  --webhook "YOUR_WEBHOOK_URL" \
  --force
```
In Power Automate's **`Post message in a chat or channel`** step, set the **Message** expression (`fx`) to:
```text
triggerBody()?['message']
```
