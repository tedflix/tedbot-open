import discord 
from discord.ext import commands

from tedhym import Tedhym

class MusicCog(commands.Cog): 
    def __init__ (self, bot):
        self.bot = bot
        self.connected_guilds = {}

    # /play <video>
    @commands.command()
    async def play(self, ctx, *, arg=''):
        if ctx.message.guild not in self.connected_guilds:
            self.connected_guilds[ctx.message.guild] = Tedhym(ctx.message.guild)

        if ctx.message.author.voice != None:
            if arg != '':
                await self.connected_guilds[ctx.message.guild].play(ctx.message.channel, ctx.message.author.voice.channel, arg)
            else:
                await ctx.message.channel.send("Cannot be empty")
        else:
            await ctx.message.channel.send("You are not connected to a voice channel.")

    # /queue
    @commands.command()
    async def queue(self, ctx, *, arg=''):
        if ctx.message.guild in self.connected_guilds:
            await self.connected_guilds[ctx.message.guild].show_queue(ctx.message.channel)

    # /nowplaying
    @commands.command()
    async def nowplaying(self, ctx, *, arg=''):
        if ctx.message.guild in self.connected_guilds:
            await self.connected_guilds[ctx.message.guild].nowplaying(ctx.message.channel)
    
    # /skip <optional arg denoting index>
    @commands.command()
    async def skip(self, ctx, *, arg=''):
        if ctx.message.guild in self.connected_guilds:
            if arg.isdecimal():
                await self.connected_guilds[ctx.message.guild].skip(ctx.message.channel, int(arg))
            else:
                await self.connected_guilds[ctx.message.guild].skip(ctx.message.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # someone could have joined vc, left vc, muted themselves, etc
        # in this case we check if someone could have disconnected from their channel before state update (hence why we use the before variable)

        if before.channel is not None:
            print(f'{member.name} state changed')

            user_channel = before.channel
            user_guild   = before.channel.guild
            tedbot = self.bot.user
            
            # check if the user is from a guild where the bot is also connected
            if user_guild in self.connected_guilds:
                music_instance = self.connected_guilds[user_guild]

                if music_instance.voice_client is not None:
                    music_channel = music_instance.voice_client.channel

                    # now we can check if the music channel is the same as the channel the user touched
                    # after that check if the queue is empty (a neccesary condition for disconnecting)
                    if user_channel == music_channel and len(music_instance.queue) == 0:
                        members_list = music_instance.voice_client.channel.members

                        if tedbot not in members_list:
                            print("Bot is not in vc when it should be. Force disconnecting. This should never happen")
                            await music_instance.voice_client.disconnect(force=True)

                        # is the bot the only one connected
                        if len(members_list) == 1 and members_list[0] == tedbot:
                            print("disconnecting bot")
                            await music_instance.voice_client.disconnect(force=True)