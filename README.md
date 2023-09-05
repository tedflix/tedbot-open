# tedbot
discord bot by tedflix

## Features
1. Media playback
2. Anonymous messaging
3. Reminder scheduling
4. Birthday notifications
5. Minecraft server status checking (for servers hosted with [Pterodactyl](https://pterodactyl.io/))
6. [Profanity filter from Minecraft](https://www.youtube.com/watch?v=p56oN3aAg3I)

## Requirements
- Python 3
- FFmpeg in PATH

## Setup
1. Install dependencies
```
python3 -m pip install dateparser discord pynacl python-dotenv yt-dlp
```
2. Populate the `.env` (a sample .env file is provided) and `data/birthdays.yaml` file

## Run
```
python3 tedbot.py
```