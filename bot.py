import discord
from os import getenv
from tools import getURL

PREFIX = '#'

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='mugi waiting'))
    print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith(PREFIX):
        url = getURL(message.content[len(PREFIX):])
        if url:
            await message.delete()
            await message.channel.send(url)
    return

if __name__ == "__main__":
    #Read TOKEN=[token] from a .env file
    client.run(getenv('TOKEN'))