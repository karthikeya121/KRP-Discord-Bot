import os
import discord
from discord.embeds import EmbedProxy
import discord.embeds
from discord.ext import commands, tasks
from discord.ui import Button, View
from discord import app_commands
import asyncio
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import random
import aiohttp
import json

guild_id = 1434419179531796511
developer_mode = True

SSU_Voted_Users = set()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='-',intents=intents)

#variables
role_to_ping = None
channel_id = None
ssu_permissions_role_id = 1434422943823433738 # placeholder; change to actual value once deployed in the original server *

#classes
class RoleDropdown(discord.ui.Select):
    def __init__(self, roles):
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in roles
            if not role.managed and role.name != "@everyone"
        ]

        super().__init__(
            placeholder="Select a SSU ping role.",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])
        selected_role = interaction.guild.get_role(selected_role_id)
        global role_to_ping
        role_to_ping = selected_role_id
        await interaction.response.send_message(f'Changed the SSU ping role to be {selected_role} `{selected_role_id}`', ephemeral=True)

class RoleDropdownView(discord.ui.View):
    def __init__(self, roles):
        super().__init__()
        self.add_item(RoleDropdown(roles))

class ChannelDropdown(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels
            if isinstance(channel, discord.TextChannel)
        ]

        super().__init__(
            placeholder="Select a channel...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_channel_id = int(self.values[0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)
        global channel_to_use, channel_id
        channel_to_use = selected_channel_id
        channel_id = selected_channel_id
        await interaction.response.send_message(f"Changed the SSU announcement channel to {selected_channel.name} `{selected_channel_id}`", ephemeral=True)

class ChannelDropdownView(discord.ui.View):
    def __init__(self, channels):
        super().__init__()
        self.add_item(ChannelDropdown(channels))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if developer_mode:
        guild = discord.Object(id=guild_id)
        await bot.tree.sync(guild=guild)
        print("Commands synced")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Knoxville RP"))
    else:
        print('impossible mate, how did u get here -?')

@bot.tree.command(name='config', description='Configure the bot settings', guild=discord.Object(id=guild_id))
async def config(interaction:discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Missing permissions. Contact a server administrator if you think this is a mistake.', ephemeral=True)
        return
    
    embed = discord.Embed(
        title='Configure bot settings.',
        description='Please choose the option you would like to configure. If you encounter any issues, contact `not_architect`',
        color=discord.Color.blue()
    )

    SSU_button = Button(label='SSU options', style=discord.ButtonStyle.green)
    async def SSU_button_callback(interaction:discord.Interaction):
        button_configrole = Button(label='Config SSU Role', style=discord.ButtonStyle.green)
        view = View()
        async def rolecallback(interaction:discord.Interaction):
            if role_to_ping != None:
                current_role = interaction.guild.get_role(role_to_ping)
            else:
                current_role = 'None'
            roles = interaction.guild.roles
            secondView = RoleDropdownView(roles)
            Embed = discord.Embed(
                title='Role configurator',
                description=f'Here, you can change the role that should be pinged when SSU command is ran.\n\nCurrent Role: `{current_role}`\n\nChoose a new role from the list below.',
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=Embed, view=secondView, ephemeral=True)
        button_configrole.callback = rolecallback

        button_configchannel = Button(label='Config SSU Channel', style=discord.ButtonStyle.green)
        async def channelcallback(interaction:discord.Interaction):
            if channel_id != None:
                current_channel = interaction.guild.get_channel(channel_id)
            else:
                current_channel = 'None'

            channels = interaction.guild.channels
            Embed = discord.Embed(
                title='Channel configurator',
                description=f'Here, you can change the channel where the SSU commands should be sent.\n\nCurrent Role: `{current_channel}`\n\nChoose a new channel from the list below.',
                color=discord.Color.blue()
            )
            thirdview = ChannelDropdownView(channels)
            await interaction.response.send_message(embed= Embed, view=thirdview, ephemeral=True)
        button_configchannel.callback = channelcallback

        view.add_item(button_configchannel)
        view.add_item(button_configrole)

        await interaction.response.send_message('What would you like to configure in the SSU module?', view=view, ephemeral=True)
    view = View()
    view.add_item(SSU_button)
    SSU_button.callback = SSU_button_callback

    await interaction.response.send_message(embed=embed, view=view,ephemeral=True)


@bot.tree.command(name='startssuvote', description='Starts an SSU vote.', guild=discord.Object(id=guild_id))
async def startssu(interaction: discord.Interaction):
    print(role_to_ping)
    print(channel_id)
    role = interaction.guild.get_role(role_to_ping)
    channel = interaction.guild.get_channel(channel_id)

    embed = discord.Embed(
        title='SSU Vote',
        description='An SSU vote has been started. Please vote below if you are able to attend. **You must join if you vote**.',
        color=discord.Color.blue()
    )

    mainView = View()
    vote = Button(label='Vote', style=discord.ButtonStyle.green)

    async def vote_callback(interaction:discord.Interaction):
        if interaction.user.id in SSU_Voted_Users:
            branchedView = View()
            unvote = Button(label='Remove Vote', style=discord.ButtonStyle.red)
            async def unvote_callback(interaction:discord.Interaction):
                SSU_Voted_Users.remove(interaction.user.id)
                await interaction.response.send_message('Removed your vote from SSU voting.', ephemeral=True)
            unvote.callback = unvote_callback
            branchedView.add_item(unvote)

            await interaction.response.send_message('You have already voted for this session. Press the button below to remove your vote.',view=branchedView, ephemeral=True)
        else:
            SSU_Voted_Users.add(interaction.user.id)
            await interaction.response.send_message('You have voted for this session!',ephemeral=True)
    
    mainView.add_item(vote)
    vote.callback = vote_callback
    await channel.send(role.mention,embed=embed,view=mainView)
    await interaction.response.send_message('Started SSU user vote. Please check it regularly and run `-hostssu` when (placeholder) users have voted.') #placeholder; to be changed *

@bot.command(name='hostssu', description='Officially start the SSU.')
async def hostssu(ctx):

    required_role = ctx.guild.get_role(ssu_permissions_role_id)
    member = ctx.author
    if required_role not in member.roles:
        await ctx.send('No permissions. Contact a server administrator if you think this is a mistake.', delete_after=5)
        return
    

    if len(SSU_Voted_Users) <= 0: # placeholder; change to actual value later *
        await ctx.send('Not allowed to host yet. Less than (placeholder) number of people voted.') # placeholder; change to actual value later *
        return
    else:
        mentions = " ".join([f"<@{user_id}>" for user_id in SSU_Voted_Users])
        embed = discord.Embed(
            title='Server Start Up',
            description='A Server Start Up has commenced! If you have voted for the SSU, you must join!\n\nServer code : `(Placeholder)`\n\nBe sure to check the server rules before you join, to ensure not to get moderated. Have fun!', #placeholder; change to actual values later *
            color=discord.Color.blue()
        )
        channel = ctx.guild.get_channel(channel_id)

        await channel.send(embed=embed)
        await channel.send(f'The following users must join:\n{mentions}',delete_after = 10)

        message = ctx.message

        await message.delete()



bot.run('Placeholder')
