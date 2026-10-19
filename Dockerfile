# Official Microsoft Playwright Python image (already includes Chromium + all Linux libraries!)
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Install Python Playwright matching the base image
RUN pip install --no-cache-dir playwright==1.49.0

COPY weather_bot.py teams_web_sender.py README.md ./

# Hugging Face Spaces & Render use PORT 7860 by default
ENV PORT=7860
EXPOSE 7860

# Run 24/7 listener: replies to @Weather Bot tags AND sends commute rain alerts for TTC & FPT Software
CMD ["python3", "teams_web_sender.py", "--listen"]

