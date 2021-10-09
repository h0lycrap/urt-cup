import discord
from discord.ext import commands
from datetime import datetime
import cogs.common.check as check
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
    async def lytchi(self, ctx):
        uploads = bs4.BeautifulSoup(requests.get("https://urt.li/ac-flawless/adxx/2021-09-19%2020:00:00/", auth=requests.auth.HTTPBasicAuth("flawless", "such cheaters much anticheat uwu")).text, features="lxml") 
        print([upload["href"] for upload in uploads.find_all("a") if any(type_ in upload["href"] for type_ in ("zip", "dm_68", "urtdemo"))])

    '''
    @commands.command()
    async def deleteall(self, ctx):
        category  = ctx.message.channel.category
        for chan in category.channels:
            await chan.delete()
    '''

    

def setup(bot):
    bot.add_cog(Test(bot))