import aiohttp
import asyncio
from discord.ext import commands
from discord.ext.tasks import loop
from mcstatus import JavaServer
import os
from urllib.parse import urljoin, urlparse

from utils import get_channel_safe

class MinecraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connected_players = {}
        self.check_server_status.start()

    @loop(seconds = 30)
    async def check_server_status(self):
        # https://dashflo.net/docs/api/pterodactyl/v1/
        url = urljoin(os.getenv('PTERODACTYL_URL'), '/api/client')
        headers = {
            'Authorization': os.getenv('PTERODACTYL_AUTH'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'}

        async with aiohttp.ClientSession() as session:
                async with session.request('GET', url, headers=headers) as response:
                    #print(f'check_server_status: Pterodactyl returned code {response.status}')
                    if response.status == 200:
                        async def check_specific_server_status(server):
                            #print(server['attributes'])
                            name = server['attributes']['name']
                            id = server['attributes']['identifier']

                            # check if server is running
                            async with aiohttp.ClientSession() as session:
                                async with session.request('GET', urljoin(os.getenv('PTERODACTYL_URL'), f'/api/client/servers/{id}/resources'), headers=headers) as online_status_check:
                                    if online_status_check.status == 200 and (await online_status_check.json())['attributes']['current_state'] == 'running':
                                        # get ports
                                        ip_data = server['attributes']['relationships']['allocations']['data']
                                        ports = tuple(allocation['attributes']['port'] for allocation in ip_data)
                                        
                                        # try each port
                                        for port in ports:
                                            try:
                                                addr = urlparse(os.getenv('PTERODACTYL_URL')).netloc + ":" + str(port)
                                                mc_server = await JavaServer.async_lookup(addr, timeout=1)

                                                old_players = self.connected_players.get(id, [])
                                                new_players = (await mc_server.async_query()).players.names

                                                connects = []
                                                disconnects = []

                                                for player in new_players:
                                                    if player not in old_players:
                                                        connects.append(player)

                                                for player in old_players:
                                                    if player not in new_players:
                                                        disconnects.append(player)
                                                
                                                try:
                                                    #i like this format so ill keep it datetime.datetime.now().strftime("%b %d, %I:%M %p :: ")
                                                    if len(connects) > 0:
                                                        await (await get_channel_safe(self.bot, os.getenv('CHANNEL_MC_SERVER_STATUS'))).send(", ".join(connects) + " joined the server " + name + ".")
                                                    if len(disconnects) > 0:
                                                        await (await get_channel_safe(self.bot, os.getenv('CHANNEL_MC_SERVER_STATUS'))).send(", ".join(disconnects) + " left the server " + name + ".")
                                                except:
                                                    print(f'check_server_status: failed to send message')
                                                
                                                # overwrite connected players list
                                                self.connected_players[id] = new_players
                                            except:
                                                # some of the ports aren't valid (such as voice chat ports), ignore them
                                                pass
                                    else:
                                        # invalidate connected_players list
                                        self.connected_players[id] = []

                        servers = (await response.json())['data']
                        asyncio.gather(*[check_specific_server_status(server) for server in servers])

