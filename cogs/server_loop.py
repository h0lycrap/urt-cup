import discord
from discord.ext import commands, tasks
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

class ServerLoop(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]
        self.Loop.start()


    @tasks.loop(seconds=3600)
    async def Loop(self):
        # Do dummy select to wake up the database
        self.bot.async_loop.create_task(update.roster(self.bot))
        self.bot.async_loop.create_task(update.signups(self.bot))
        print("Loop!")


def setup(bot):
    bot.add_cog(ServerLoop(bot))