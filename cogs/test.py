import discord
from discord.ext import commands
from datetime import datetime
import cogs.common.check as check
import cogs.common.embeds as embeds
import cogs.common.update as update
import requests
import bs4

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.command()
    async def zmb(self, ctx):
        zmb = discord.utils.get(self.bot.guilds[0].members, id=205821831964393472)
        embed=discord.Embed(title="Go to sleep Zmb!", color=0x9b2ab2)
        embed.set_thumbnail(url=zmb.avatar_url)
        await ctx.send(embed=embed)
        
        
    @commands.command()
    async def urt5(self, ctx):
        await ctx.send(self.bot.quotes['cmdUrt5'])

    
    @commands.command()
    async def testpickup(self, ctx):
        embed=discord.Embed(description="[Live scoreboard](ms-settings://)", color=0x1876cd, )
        await ctx.send(embed=embed)
    

    @commands.command()
    async def lytchi(self, ctx):
        uploads = bs4.BeautifulSoup(requests.get("https://urt.li/ac-flawless/adxx/2021-09-19%2020:00:00/", auth=requests.auth.HTTPBasicAuth("flawless", "such cheaters much anticheat uwu")).text, features="lxml") 
        print([upload["href"] for upload in uploads.find_all("a") if any(type_ in upload["href"] for type_ in ("zip", "dm_68", "urtdemo"))])


    @commands.command()
    @check.is_guild_manager()
    async def deleteall(self, ctx):
        category  = ctx.message.channel.category
        for chan in category.channels:
            await chan.delete()

    
    @commands.command()
    @check.is_guild_manager()
    async def clearchan(self, ctx):
        chan  = ctx.message.channel
        async for message in chan.history(limit=200):
            await message.delete()

    @commands.command()
    @check.is_guild_manager()
    async def post_all_rosters(self, ctx):
        admin_managed = 0
        await self.post_all_rosters_fun(admin_managed)
        admin_managed = 1
        await self.post_all_rosters_fun(admin_managed)

    async def post_all_rosters_fun(self, admin_managed):
        for team in self.bot.db.get_all_clans(admin_managed):
            # Generate the embed
            embed, insuficient_roster = embeds.team(self.bot, tag=team['tag'])

            if not insuficient_roster:
                await update.post_roster(self.bot, admin_managed, team['id'], post_all=True)

        # Get channel
        channel_id = self.bot.channel_roster_id
        if admin_managed == 1:
            channel_id = self.bot.channel_roster_national_teams_id
        roster_channel = discord.utils.get(self.bot.guilds[0].channels, id=channel_id)

        # Post or edit team index
        index_embed = await embeds.team_index(self.bot, admin_managed)
        await roster_channel.send(embed=index_embed)




def setup(bot):
    bot.add_cog(Test(bot))