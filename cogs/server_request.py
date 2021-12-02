import random
from typing import Dict

import asyncio
import discord
import flag
from discord import channel
from discord.ext import commands, tasks
from ftwgl import FTWClient, GameType

import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import datetime
# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

class ServerRequest(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        # Get user info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (user.id,))
        user_info = self.bot.cursor.fetchone()

        if interaction.component.id.startswith("button_fixture_requestserver"):
            await self.request_server(interaction, user_info)

    # Request a server for a game
    async def request_server(self, interaction, user_info):
        # Get  feature  
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        '''
        # Check if we are match day
        gamedate = datetime.date.fromisoformat(fixture_info['date'].split()[0])
        if gamedate != datetime.datetime.now().date():
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_gamedate'])
            return
        '''

        # Make server location drop menu
        ftw_client: FTWClient = self.bot.ftw
        servers = await ftw_client.server_locations()

        region_list: Dict[str, dropmenus.RegionList] = {}
        for server in servers.values():
            r = dropmenus.RegionList()
            r.label = f"{server['name']}, {server['country']}"
            r.emoji = flag.flagize(f":{server['country']}:")
            r.dcid = server['DCID']
            region_list[r.dcid] = r

        server_region_dropmenu = dropmenus.server_regions(region_list.values())

        # Get server location
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdServerRequest_promptregion'], components=server_region_dropmenu)
        interaction_serverlocation = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "dropmenu_server_region" and i.message.channel.id == interaction.message.channel.id)
        server_dcid = interaction_serverlocation.component[0].value

        # TODO: Allow for a team to select which gametype will be played first
        server_gametype = GameType.team_survivor

        # Server will stay alive even after ttl expiration if players are connected
        server_ttl = (int(fixture_info['format'][2]) // 2) + 1  # ie. (BO3//2)+1 == 2 hour, (BO5//2)+1 == 3 hours
        server_rcon = str(random.randint(111111, 999999))
        server_pass = str(random.randint(111111, 999999))

        # Request to get a server
        server_id = await ftw_client.server_rent(fixture_info['ftw_match_id'], int(server_dcid), server_gametype, server_rcon, server_pass, server_ttl)

        # Wait for server to finish spawning
        server = await ftw_client.server_get_with_id(server_id)
        while 'ip' not in server['config']:
            await asyncio.sleep(5)
            server = await ftw_client.server_get_with_id(server_id)

        server_ip = server['config']['ip']
        await interaction_serverlocation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdServerRequest_success'].format(location=region_list[server_dcid].label, location_emoji=region_list[server_dcid].emoji, ip=server_ip, password=server_pass, rcon=server_rcon, username=user_info['ingame_name']))


def setup(bot):
    bot.add_cog(ServerRequest(bot))
