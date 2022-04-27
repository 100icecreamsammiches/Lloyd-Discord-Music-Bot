import discord
from discord.enums import try_enum
from discord.ext import commands
import youtube_dl
import typing
import math
from discord_slash import SlashCommand

intents = discord.Intents().all()
#client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='.',intents=intents)
slash = SlashCommand(bot, sync_commands=True)

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
    

@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))

@slash.slash(name='join', description='Tells Lloyd to join the voice channel')
async def join(ctx):
    await clear(ctx)
    try:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send("Joined")
    except:
        await ctx.send("You're probably not in a VC, why would you do that?")

@slash.slash(name='leave', description='Tells Lloyd to leave the voice channel')
async def leave(ctx):
    await clear(ctx)
    try:
        await ctx.voice_client.disconnect()
        await clear(ctx)
    except Exception as err:
        "idk why it breaks but i do be lazy"
    await ctx.send("Left")

@slash.slash(name='play', description='Plays a song')
async def play(ctx, url, speed=1, timestamp=0):
    await clear(ctx)
    await ctx.send("Playing")
    voice_client = ctx.voice_client
    speed = float(speed)

    if speed > 2:
        power = math.floor(math.log(float(speed), 2))
        option = '-filter:a "' + ('atempo=2.0,' * power) + 'atempo={}"'.format(speed / (2**power))

    elif speed < 0.5:
        power = math.floor(math.log(float(speed), 0.5))
        option = '-filter:a "' + ('atempo=0.5,' * power) + 'atempo={}"'.format(speed / (0.5**power))
        
    else:
        option = '-filter:a "atempo={}"'.format(speed)

    if voice_client == None:
        await ctx.author.voice.channel.connect()

    try:
        voice_channel = ctx.guild.voice_client
        async with ctx.channel.typing():

            with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
                info = ydl.extract_info(url, download=False)
                URL = info['formats'][0]['url']

            for i in range(len(url) - 3):
                if url[i:i+3] == "?t=":
                    timestamp = int(url[i+3:])
            voice_channel.play(discord.FFmpegPCMAudio(source=URL, before_options='-vn -ss {} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 16'.format(timestamp), options=option))
    
    except Exception as err:
        print(err)
        errorLog = open("log.txt", "w")
        errorLog.write(str(err))
        errorLog.close()
        await ctx.send("Something went wrong")

@slash.slash(name='pause', description='Pauses the song')
async def pause(ctx):
    await clear(ctx)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_playing():
            await voice_client.pause()
    except:
        await ctx.send("Nothing's playing lol")
    await ctx.send("Paused")

@slash.slash(name='resume', description='Resumes the song')
async def resume(ctx):
    await clear(ctx)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_paused():
            await voice_client.resume()
    except:
        await ctx.send("Nothing's playing lol")
    await ctx.send("Resumed")

@slash.slash(name='stop', description='Stops the song')
async def stop(ctx):
    await clear(ctx)
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("Nothing's playing lol")
    await ctx.send("Stopped")
        
@slash.slash(name='clear', description='Clears the channel')
async def clearCommand(ctx):
    await clear(ctx)
    await ctx.send("Cleared")

async def clear(ctx):
    if ctx.channel.id == 819991857957830717:
        await ctx.channel.purge(limit=20)

@slash.slash(name="tip", description="Give me a generous tip!")
async def tip(ctx):
    await ctx.send("Thanks for the tip!", file = discord.File("lloyd-tip.gif"))
    f = open("tips.txt", mode="r")
    lst = (f.read()).split(",")
    f.close()
    tips = []
    for i in range(0, len(lst) - 1, 2):
        tips.append([lst[i], int(lst[i+1])])
    if "<@!" + str(ctx.author.id) + ">" not in [i[0] for i in tips]:
        tips.append(["<@!" + str(ctx.author.id) + ">", 0])
    tips[[i[0] for i in tips].index("<@!" + str(ctx.author.id) + ">")][1] += 1
    
    string = ""
    for i in tips[:-1]:
        string += str(i[0]) + "," + str(i[1]) + ","
    string += str(tips[-1][0] + "," + str(tips[-1][1]))

    f = open("tips.txt", mode="w")
    f.write(string)
    f.close()

@slash.slash(name="score", description="Checks how many times everyone's tipped")
async def tip(ctx, *, user):
    if user == "":
        await ctx.send("Needs a user!")
    elif "<@!" not in user:
        await ctx.send("That's not a user!")
    else:
        f = open("tips.txt", mode="r")
        lst = (f.read()).split(",")
        f.close()
        tips = []
        for i in range(0, len(lst) - 1, 2):
            tips.append([lst[i], int(lst[i+1])])
        print(tips)
        try:
            place = [i[0] for i in tips].index(str(user))
            await ctx.send("{} has given me {} tips!".format(tips[place][0], tips[place][1]))
        except:
            await ctx.send("{} hasn't given me any tips yet! Rude...".format(user))

@slash.slash(name="error", description="Tells you exactly how I failed")
async def error(ctx):
    await ctx.send(file=discord.File("log.txt"))

bot.run("token")
