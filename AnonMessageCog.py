import discord 
from discord.ext import commands
import os

from utils import get_channel_safe

class AnonMessageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channels = [os.getenv('CHANNEL_ANON_MESSAGES')]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author != self.bot.user:
            if isinstance(message.channel, discord.channel.DMChannel): #if dm
                print(f"User {message.author} said '{message.content}' in DM with bot")
                for channel in self.channels:
                    channel = await get_channel_safe(self.bot, channel)
                    if channel is None:
                        channel = await self.bot.fetch_channel(channel)

                    await channel.send(message.content)