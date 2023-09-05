import dateparser as dp
import datetime
import discord 
from discord.ext import commands
from reminder import Reminder

class ReminderCog(commands.Cog):
    def __init__ (self, bot):
        self.reminder = Reminder(bot)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        try:
            custom_id = interaction.message.components[0].children[0].custom_id
            if custom_id == 'reminder':
                await self.reminder.cancel(interaction.message.id, interaction.user.id, interaction.response)
        except Exception as e:
            print(e)

    @commands.command()
    async def remind(self, ctx, *split_message):
        preposition_index = -1
        for i, word in enumerate(split_message):
            if word.strip() in ('in', 'on', 'at'):
                preposition_index = i

        if preposition_index >= 0:
            reminder_name = ' '.join(split_message[0:preposition_index])
            reminder_time = ' '.join(split_message[preposition_index + 1:])

            timezone = 'Asia/Manila'
            
            parsed_time = dp.parse(reminder_time, settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True, 'PREFER_DATES_FROM': 'future'})
            #readable_reminder_time = parsed_time.strftime("%B %d %Y, %I:%M:%S %p")
            utc_parsed_time = parsed_time.astimezone(datetime.timezone.utc)
            utc_parsed_timestamp = int(utc_parsed_time.timestamp())
            
            if len(reminder_name) == 0:
                await ctx.message.channel.send("pls add a valid reminder name :clown:\nformat is 'remind [name] in/on/at [time]'")

            if len(reminder_time) == 0:
                await ctx.message.channel.send("pls add a valid reminder time :clown:\nformat is 'remind [name] in/on/at [time]'")

            if len(reminder_name) > 0 and len(reminder_time) > 0:
                response = f"reminder name: {reminder_name}\nreminder time: <t:{utc_parsed_timestamp}:F>"

                cancel_button = discord.ui.Button(style=discord.ButtonStyle.danger, label='cancel reminder (author only)', custom_id='reminder')
                reminder_controller_view = discord.ui.View(timeout=None)
                reminder_controller_view.add_item(cancel_button)
                reminder_controller_message = await ctx.message.channel.send(response, view=reminder_controller_view)

                # use reminder message id as reminder id
                self.reminder.schedule(reminder_controller_message.id, ctx.message.author.id, ctx.message.channel.id, utc_parsed_timestamp, reminder_name)
        else:
            await ctx.message.channel.send("format is 'remind [name] in/on/at [time]'")