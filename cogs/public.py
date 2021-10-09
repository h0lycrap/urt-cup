#import discord
from discord.ext import commands
import discord
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

    @commands.command() 
    @check.is_guild_manager()
    async def forceupdatefixtures(self, ctx):
        await update.fixture_cards(self.bot)

    @commands.command()
    async def notscheduled(self, ctx):
        print('coucou')
        # Get fixtures 
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE status IS NULL")
        fixtures = self.bot.cursor.fetchall()

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
