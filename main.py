import discord
from discord.enums import try_enum
from discord.ext import commands
import youtube_dl
import typing
import math

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='.',intents=intents)

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

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    try:
        if ctx.message.author.voice:
            channel = ctx.message.author.voice.channel
            await channel.connect()
        try:
            await ctx.message.delete()
        except:
            "nothing happened"
    except:
        await ctx.send("You're probably not in a VC, why would you do that?")

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    try:
        voice_client = ctx.message.guild.voice_client
        await ctx.message.delete()
        if voice_client.is_connected():
            await voice_client.disconnect()
        await clear(ctx)
    except:
        await ctx.send("Something went wrong and it's probably your fault.")

@bot.command(name='p', help='To play song')
async def play(ctx, timestamp: typing.Optional[int]=0, speed: typing.Optional[float]=1, *, url):
    voice_client = ctx.message.guild.voice_client
    if speed > 2:
        option = '-filter:a "' + ('atempo=2.0,' * (math.floor(math.log(float(speed), 2)) - 1) ) + 'atempo=2.0"'
    elif speed < 0.5:
        option = '-filter:a "' + ('atempo=0.5,' * (math.floor(math.log(float(speed), 0.5)) - 1) ) + 'atempo=0.5"'
    else:
        option = '-filter:a "atempo={}"'.format(speed)
    if voice_client == None:
        await join(ctx)
    try:
        await ctx.message.delete()
    except:
        "nothing happened"
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client
        async with ctx.typing():
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
        await ctx.send("Whoops something went wrong lol, try again")

@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    try:
        if voice_client.is_playing():
            await voice_client.pause()
        await ctx.message.delete()
    except:
        await ctx.send("Nothing's playing lol")

@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    try:
        if voice_client.is_paused():
            await voice_client.resume()
    except:
        await ctx.send("Nothing's playing lol")
    await ctx.message.delete()

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("Nothing's playing lol")
    await ctx.message.delete()
        
@bot.command(name='clear', help='Clears the channel')
async def clear(ctx):
    if ctx.message.channel.id == 819991857957830717:
        await ctx.channel.purge(limit=20)

@bot.command(name="tip", help="give me a generous tip!")
async def tip(ctx):
    await ctx.send("Thanks for the tip!", file = discord.File("lloyd-tip.gif"))
    f = open("tips.txt", mode="r")
    lst = (f.read()).split(",")
    f.close()
    tips = []
    for i in range(0, len(lst) - 1, 2):
        tips.append([lst[i], int(lst[i+1])])
    if "<@!" + str(ctx.message.author.id) + ">" not in [i[0] for i in tips]:
        tips.append(["<@!" + str(ctx.message.author.id) + ">", 0])
    tips[[i[0] for i in tips].index("<@!" + str(ctx.message.author.id) + ">")][1] += 1
    
    string = ""
    for i in tips[:-1]:
        string += str(i[0]) + "," + str(i[1]) + ","
    string += str(tips[-1][0] + "," + str(tips[-1][1]))

    f = open("tips.txt", mode="w")
    f.write(string)
    f.close()

@bot.command(name="score", help="checks how many times everyone's tipped")
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

@bot.command(name="error", help="tells you exactly how i failed")
async def error(ctx):
    await ctx.message.delete()
    await ctx.send(file=discord.File("log.txt"))

bot.run("token")
