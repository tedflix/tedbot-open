import datetime
import discord
from discord.ext import commands
from discord.ext.tasks import loop
import os
import yaml # pip3 install pyyaml

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from utils import get_channel_safe

'''
Birthday notifications

Notes:
- enabling Intents.members is highly encouraged to avoid using API calls

Implementation issues:
- time to run at cannot be changed without restart
- handle missing keys better
- people with leap year birthdays only get to celebrate their birthday every 4 years

v1.1: converted into a Cog
'''

VERSION = '1.1 (2023-09-01)'

def get_time_to_run_at():
    with open('data/birthdays.yaml', 'r') as birthdays_file:
        birthdays_info = yaml.safe_load(birthdays_file)
        return datetime.time(hour=0, 
                            minute=0, 
                            second=0, 
                            tzinfo=ZoneInfo(birthdays_info['timezone']))

class BirthdayNotificationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthday.start()

        if os.getenv('TEST'):
            import asyncio
            asyncio.run_coroutine_threadsafe(self.check_birthday(), self.bot.loop)

    @loop(time=get_time_to_run_at())
    async def check_birthday(self):
        print(f'Birthday notifications {VERSION}')
        with open('data/birthdays.yaml', 'r') as birthdays_file:
            birthdays_info = yaml.safe_load(birthdays_file)

            datetime_now = datetime.datetime.now(ZoneInfo(birthdays_info['timezone']))
            date_today = datetime_now.date()
            date_tomorrow = date_today + datetime.timedelta(days=1)

            send_channel = await get_channel_safe(self.bot, birthdays_info['channel_id'])
            if isinstance(send_channel, discord.abc.GuildChannel):
                for birthday_info in birthdays_info['birthdays']:
                    celebrant, celebrant_discord, birthday = [(k, v.get('user_id'), v['birthday']) for k, v in birthday_info.items()][0] # evil dictionary thing, user_id can be None

                    check_month_day = lambda x, y : x.month == y.month and x.day == y.day
                    is_birthday_tomorrow = check_month_day(date_tomorrow, birthday)
                    is_bithday_today = check_month_day(date_today, birthday)


                    # replace celebrant name with discord mention only if the account exists (on the config file AND not deleted) and the account can see the message.
                    if (is_birthday_tomorrow or is_bithday_today) and celebrant_discord is not None:
                        # try obtaining from discord.py's member cache
                        celebrant_discord_member = send_channel.guild.get_member(celebrant_discord)

                        # retry with API call if member was not found in member cache
                        if celebrant_discord_member is not None:
                            print(f'DEBUG: Found {celebrant_discord_member} in member cache.')
                        else:
                            print(f'WARN: {celebrant_discord} was not found in member cache.')
                            print(f'WARN: using API call fallback. This is only normal if (a) Intents.members is not enabled or (b) the user is not in the guild')
                            try:
                                celebrant_discord_member = await send_channel.guild.fetch_member(celebrant_discord)
                                print(f'DEBUG: Found {celebrant_discord_member} using API call.')
                            except Exception as e:
                                print(f'WARN: API call failed with {e}.')

                        if celebrant_discord_member is not None:
                            celebrant = celebrant_discord_member.mention
                            print(f'DEBUG: Replaced celebrant name with discord account.')
                        else:
                            print(f'WARN: Discord account {celebrant_discord} not found. Not replacing celebrant name.')
                    
                    #print(celebrant, birthday)
                    
                    if is_birthday_tomorrow:
                        await send_channel.send(f'Tomorrow is {celebrant}\'s birthday.')
                    elif is_bithday_today:
                        await send_channel.send(f'Today is {celebrant}\'s birthday. Happy birthday!')
                
            else:
                print(f'WARN: birthday notifications only support guild channels for now (received a {type(send_channel)}).') 
