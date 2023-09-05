'''
Tries fetch_channel (API call) only if get_channel fails
'''
async def get_channel_safe(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)
    return channel