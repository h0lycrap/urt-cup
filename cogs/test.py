import discord
from discord.ext import commands

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def zmb(self, ctx):
        zmb = discord.utils.get(self.bot.guilds[0].members, id=205821831964393472)
        embed=discord.Embed(title="Va dormir Zmb", color=0x9b2ab2)
        embed.set_thumbnail(url=zmb.avatar_url)
        await ctx.send(embed=embed)
    
    

    @commands.command()
    async def lytchi(self, ctx):
        #await message.channel.send(self.bot.quotes['cmdLytchi'])
        await ctx.send(content="Test boutons", components=[[Button(style=ButtonStyle.URL, label="Example link button", url="https://google.com"), Button(style=ButtonStyle.blue, label="Click me", custom_id="button"), Button(style=ButtonStyle.red, label="Should be aligned", emoji=u"\U00002705", custom_id="button2")]])

    @commands.command()
    async def st0mp(self, ctx):
        await ctx.send(self.bot.quotes['cmdSt0mp'])

    @commands.command()
    async def holycrap(self, ctx):
        #await message.channel.send(self.bot.quotes['cmdHoly'])
        await ctx.send(
            "Who won the knife fight?",
            components = [
                Select(
                    placeholder = "Select one team",
                    options = [
                        SelectOption(label = "NoWay", emoji = u"\U0001F1EB\U0001F1F7", value = "NoWay"),
                        SelectOption(label = "Quad", emoji = u"\U0001F1EE\U0001F1F9", value = "Quad")
                    ],
                    custom_id="select"
                )
            ]
        )
        
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