import discord
from discord.ext import commands
from datetime import datetime
import cogs.common.check as check

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
        print(datetime.now(), ctx.message.created_at)
    
    

    @commands.command()
    async def lytchi(self, ctx):
        #await message.channel.send(self.bot.quotes['cmdLytchi'])
        await ctx.send(content="Test boutons", components=[[Button(style=ButtonStyle.URL, label="Example link button", url="https://google.com"), Button(style=ButtonStyle.blue, label="Click me", custom_id="button"), Button(style=ButtonStyle.red, label="Should be aligned", emoji=u"\U00002705", custom_id="button2")]])

    @commands.command()
    async def st0mp(self, ctx):
        await ctx.send(self.bot.quotes['cmdSt0mp'])

    @check.is_guild_manager()
    @commands.command()
    async def holycrap(self, ctx):
        # Create category and channels
        role_flawless = discord.utils.get(self.guild.roles, id=int(self.bot.role_flawless_crew_id))
        role_moderator = discord.utils.get(self.guild.roles, id=int(self.bot.role_moderator_id))
        role_bot = discord.utils.get(self.guild.roles, id=int(self.bot.role_bot_id))
        category = await self.guild.create_category_channel(f"\U0001F947┋ TEST")
        await category.set_permissions(self.guild.default_role, send_messages=False)
        await category.set_permissions(role_flawless, send_messages=True)
        await category.set_permissions(role_moderator, send_messages=True)
        await category.set_permissions(role_bot, send_messages=True)

        # get admin channel permissions
        chan_admin = await category.create_text_channel("admin-panel")
        await chan_admin.set_permissions(role_bot, view_channel=True)
        await chan_admin.set_permissions(self.guild.default_role, view_channel=False)
        await chan_admin.set_permissions(role_flawless, view_channel=True)
        await chan_admin.set_permissions(role_moderator, view_channel=True)
        

        chan_signups = await category.create_text_channel("signups")
        chan_calendar = await category.create_text_channel("calendar")
        chan_stage = await category.create_text_channel("stage")
        
    @commands.command()
    async def urt5(self, ctx):
        await ctx.send(self.bot.quotes['cmdUrt5'])

    @commands.Cog.listener() 
    async def on_select_option(self, interaction):
        if interaction.parent_component.id == "select":
            await interaction.channel.send(content = f"{interaction.component[0].label} won the knife fight!")
            await interaction.respond(type=6)

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        if interaction.component.id == "button":
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='Button Clicked')
            await interaction.channel.send(f"{interaction.user.name} clicked on the button")
        if interaction.component.id == "button2":
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='Button Clicked')
            await interaction.channel.send(f"{interaction.user.name} clicked on the second button")

    

def setup(bot):
    bot.add_cog(Test(bot))