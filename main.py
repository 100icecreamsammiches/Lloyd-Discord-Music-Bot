import discord
from discord.ext import commands,tasks
import os
import youtube_dl

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='.',intents=intents)

async def on_ready():
    print('Logged in as {0.user}'.format(client))

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename
    
@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if ctx.message.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    try:
        await ctx.message.delete()
    except:
        "nothing happened"

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await ctx.message.delete()
    if voice_client.is_connected():
        await voice_client.disconnect()
    await clear(ctx)

@bot.command(name='p', help='To play song')
async def play(ctx,url):
    voice_client = ctx.message.guild.voice_client
    if voice_client == None:
        await join(ctx)
    try:
        await ctx.message.delete()
    except:
        "nothing happened"
    
    server = ctx.message.guild
    voice_channel = server.voice_client
    async with ctx.typing():
        
        filename = await YTDLSource.from_url(url, loop=bot.loop)
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=filename))

@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    await ctx.message.delete()

@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    await ctx.message.delete()

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    await ctx.message.delete()
        
@bot.command(name='clear', help='Stops the song')
async def clear(ctx):
    if ctx.message.channel.id == 819991857957830717:
        await ctx.channel.purge(limit=20)

bot.run("token")
