import discord 
from discord.ext import commands

class ProfanityCog(commands.Cog): 
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author != self.bot.user:
            detected_words = []
            with open('data/profanity.txt', 'r') as f:
                for banned_word in f:
                    banned_word = banned_word.strip()
                    if banned_word.lower() in message.content.lower():
                        detected_words.append(banned_word)
            
            if len(detected_words) > 0:
                detected_words_flattened = ', '.join(detected_words)
                await message.channel.send(f'{message.author.mention} please do not swear (the following swear words were detected in your message: {detected_words_flattened})')