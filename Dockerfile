FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements-bot.txt /app/requirements-bot.txt
RUN pip install --no-cache-dir -r /app/requirements-bot.txt

COPY discord_hide_bot.py /app/discord_hide_bot.py

CMD ["python", "-u", "discord_hide_bot.py"]
