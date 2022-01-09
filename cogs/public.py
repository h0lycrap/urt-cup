#import discord
from discord.ext import commands
import discord
import cogs.common.embeds as embeds
from cogs.common.enums import FixtureStatus
import cogs.common.update as update
import cogs.common.check as check

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Public(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.command()
    async def cancel(self, ctx):
        pass

    @commands.command()
    async def info(self, ctx, args=None):
        # Check if there is an arg
        if args==None:
            #await ctx.send(self.bot.quotes['cmdInfo_error_args'])
            args = f"<@!{ctx.author.id}>"
            

        # Check if this is a mention and extract user id
        if args.startswith("<@!") and args.endswith(">"):
            args = args[3:-1] 
        elif args.startswith("<@") and args.endswith(">"):
            args = args[2:-1] 

        team = self.bot.db.get_clan(tag=args)
        player = self.bot.db.get_player(discord_id=args)
        if player == None:
            player = self.bot.db.get_player(urt_auth=args)
        if player == None:
            player = self.bot.db.get_player(ingame_name=args)


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

    @commands.command() 
    @check.is_guild_manager()
    async def forceupdatefixtures(self, ctx):
        await update.fixture_cards(self.bot)

    @commands.command()
    async def notscheduled(self, ctx):
        print('coucou')
        # Get fixtures 
        fixtures = self.bot.db.get_fixtures_of_status(self, FixtureStatus.Created)

        #Create embed field content
        fixture_string = "Matches not scheduled \n\n"
        if fixtures:
            for fixture_info in fixtures:

                # Get fixture link
                fixture_channel = discord.utils.get(self.bot.guilds[0].channels, id=int(fixture_info['channel_id']))

                fixture_string += f"{fixture_channel.mention}\n"

                if len(fixture_string) > 1900:
                    await ctx.send(fixture_string)
                    fixture_string = ""

            await ctx.send(fixture_string)

def setup(bot):
    bot.add_cog(Public(bot))
