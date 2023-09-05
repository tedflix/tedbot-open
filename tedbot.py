import discord
from discord.ext import commands
import os

from AnonMessageCog import AnonMessageCog
from BirthdayNotificationsCog import BirthdayNotificationsCog
from MinecraftCog import MinecraftCog
from MusicCog import MusicCog
from ProfanityCog import ProfanityCog
from ReminderCog import ReminderCog

# load .env file
from dotenv import load_dotenv
load_dotenv()

activity = discord.Game(name='tedbot v2 test')

# the bot needs at least the 'message content intent' to retrieve messages 
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents, activity=activity)


cogs_ok = False

@bot.listen()
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

    global cogs_ok
    if not cogs_ok:
        await bot.add_cog(AnonMessageCog(bot))
        await bot.add_cog(BirthdayNotificationsCog(bot))
        await bot.add_cog(MinecraftCog(bot))
        await bot.add_cog(MusicCog(bot))
        await bot.add_cog(ProfanityCog(bot))
        await bot.add_cog(ReminderCog(bot))
        cogs_ok = True

bot.run(os.getenv("API_KEY", default=''))
