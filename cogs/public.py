#import discord
from discord.ext import commands
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Public(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.command()
    async def info(self, ctx, args=None):
        # Check if there is an arg
        if args==None:
            await ctx.send(self.bot.quotes['cmdInfo_error_args'])
            return

        # Check if this is a mention and extract user id
        if args.startswith("<@!") and args.endswith(">"):
            args = args[3:-1] 
        elif args.startswith("<@") and args.endswith(">"):
            args = args[2:-1] 

        self.bot.cursor.execute("SELECT tag, country, captain, roster_message_id, name FROM Teams WHERE tag=%s;", (args,))
        team = self.bot.cursor.fetchone()

        self.bot.cursor.execute("SELECT discord_id, urt_auth, ingame_name, country FROM Users WHERE discord_id=%s OR urt_auth=%s OR ingame_name=%s;", (args, args, args))
        player = self.bot.cursor.fetchone()

        if not team and not player:
            await ctx.send(self.bot.quotes['cmdInfo_error_doesntexist'])
            return

        if team:
            embed, _ = embeds.team(self.bot, tag=team['tag'], show_invited=True)

        else:
            embed = embeds.player(self.bot, player['urt_auth'])

        await ctx.send(embed=embed)

    @commands.command() 
    @check.is_guild_manager()
    async def forceupdate(self, ctx):
        await update.roster(self.bot)
        await update.signups(self.bot)
        await update.fixtures(self.bot)

def setup(bot):
    bot.add_cog(Public(bot))
