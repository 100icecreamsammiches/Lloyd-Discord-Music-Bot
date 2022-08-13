import discord
import asyncio
from discord.enums import try_enum
from discord.ext import commands
from discord.ui import Button, View
import youtube_dl
import math
import os
from dotenv import load_dotenv
load_dotenv()

title = ""
info = {}
link = ""

intents = discord.Intents().all()
#client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='.', intents=intents)

playlist = []

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

stopButton = Button(
    style=discord.ButtonStyle.primary,
    emoji="⏹️",
)

pauseButton = Button(
    style=discord.ButtonStyle.primary,
    emoji="⏯️",
)

@bot.slash_command(name='join', description='Tells Lloyd to join the voice channel')
async def join(ctx):
    await clear(ctx)
    try:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.response.send_message("Nothing's playing")
    except:
        await ctx.response.send_message("You're probably not in a VC, why would you do that?")

@bot.slash_command(name='leave', description='Tells Lloyd to leave the voice channel')
async def leave(ctx):
    await clear(ctx)
    try:
        await ctx.voice_client.disconnect()
        await clear(ctx)
    except Exception as err:
        "idk why it breaks but i do be lazy"
    await ctx.response.send_message("Nothing's playing")

@bot.slash_command(name='play', description='Plays a song')
async def play(ctx, url, speed=1, timestamp=0, bassboost=0, wobble=0, echo=0):
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    url = url.replace("m.youtube.com", "youtu.be").replace("watch?v=", "")
    
    voice_client = ctx.guild.voice_client

    if voice_client == None:
        await ctx.author.voice.channel.connect()

    voice_client = ctx.guild.voice_client

    speed = float(speed)
    option = "-af "
    if speed > 2:
        power = math.floor(math.log(float(speed), 2))
        option += ('atempo=2.0,' * power) + 'atempo={}'.format(speed / (2**power))

    elif speed < 0.5:
        power = math.floor(math.log(float(speed), 0.5))
        option += ('atempo=0.5,' * power) + 'atempo={}'.format(speed / (0.5**power))
        
    else:
        option += 'atempo={}'.format(speed)

    if bassboost != 0:
        option += ',bass=g={},equalizer=frequency=100:width=10000:width_type=h:gain={}'.format(bassboost,bassboost)
    
    if wobble != 0:
        if float(wobble) > 1:
            option += (",vibrato=d=1" * math.floor(float(wobble))) + ",vibrato=d={}".format(float(wobble) - math.floor(float(wobble)))
        else:
            option += ",vibrato=d={}".format(wobble)

    if echo != 0:
        option += ",aecho=0.8:0.9:{}|{}|{}|{}:0.3|0.25|0.2|0.15".format(echo, echo, echo, echo)
    
    if not voice_client.is_playing():
        try:
            await clear(ctx)
            await ctx.response.send_message("Preparing...", view=None)
            voice_channel = ctx.guild.voice_client
            async with ctx.channel.typing():

                with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
                    global title, link
                    info = ydl.extract_info(url, download=False)
                    URL = info['formats'][0]['url']
                    title = info.get("title", None)
                    link = url

                for i in range(len(url) - 3):
                    if url[i:i+3] == "?t=":
                        timestamp = int(url[i+3:])

                audio = discord.FFmpegPCMAudio(source=URL, before_options='-vn -ss {} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 16'.format(timestamp), options=option)
                voice_channel.play(audio, after=lambda error: (asyncio.run_coroutine_threadsafe(HandleEnd(error, ctx), bot.loop)))
                await ctx.interaction.edit_original_message(content="Playing [{}]({})".format(title, url), view=view)
        
        except Exception as err:
            print(err)
            errorLog = open("log.txt", "w")
            errorLog.write(str(err))
            errorLog.close()
            await ctx.interaction.edit_original_message(content="Something went wrong, please try again", view=None)
    
    else:
        playlist.append([url, option])
        msg = await ctx.response.send_message("Preparing...", view=None)
        await msg.delete_original_message()

async def HandleEnd(err, ctx):
    if err == None:
        if len(playlist) > 0:
            try:
                timestamp = 0
                voice_channel = ctx.guild.voice_client
                url = playlist[0][0]
                option = playlist[0][1]
                playlist.pop(0)
                view = View()
                view.add_item(stopButton)
                view.add_item(pauseButton)
                async with ctx.channel.typing():
                    with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
                        global title, link
                        info = ydl.extract_info(url, download=False)
                        URL = info['formats'][0]['url']
                        title = info.get("title", None)
                        link = url

                    for i in range(len(url) - 3):
                        if url[i:i+3] == "?t=":
                            timestamp = int(url[i+3:])

                    audio = discord.FFmpegPCMAudio(source=URL, before_options='-vn -ss {} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 16'.format(timestamp), options=option)

                    voice_channel.play(audio, after=lambda error: (asyncio.run_coroutine_threadsafe(HandleEnd(error, ctx), bot.loop)))
                    await ctx.interaction.edit_original_message(content="Playing [{}]({})".format(title, url), view=view)
            except Exception as err:
                print("error: {}".format(err))
        else:
            await ctx.interaction.edit_original_message(content="Done playing", view=None)
    else:
        print(err)
        errorLog = open("log.txt", "w")
        errorLog.write(str(err))
        errorLog.close()
        await ctx.interaction.edit_original_message(content="Something went wrong, please try again", view=None)

@bot.slash_command(name='pause', description='Pauses the song')
async def pause(ctx):
    await clear(ctx)
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_playing():
            await voice_client.pause()
    except:
        await ctx.response.send_message("Nothing's playing")
    await ctx.response.send_message("Paused", view=view)

@bot.slash_command(name='resume', description='Resumes the song')
async def resume(ctx):
    await clear(ctx)
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_paused():
            await voice_client.resume()
    except:
        await ctx.response.send_message("Nothing's playing")
    await ctx.response.send_message("Playing [{}]({})".format(title, link), view=view)

@bot.slash_command(name='stop', description='Stops the song')
async def stop(ctx):
    await clear(ctx)
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    await ctx.response.send_message("Nothing's playing")

async def pauseInter(ctx):
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.response.edit_message(content="Paused", view=view)
    else:
        voice_client.resume()
        await ctx.response.edit_message(content="Playing [{}]({})".format(title, link), view=view)

async def stopInter(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    await ctx.response.edit_message(content="Nothing's playing", view=None)
        
@bot.slash_command(name='clear', description='Clears the channel')
async def clearCommand(ctx):
    await clear(ctx)
    if ctx.guild.voice_client.is_playing():
        view = View()
        view.add_item(stopButton)
        view.add_item(pauseButton)
        await ctx.response.send_message("Playing [{}]({})".format(title, link), view=view)
    else:
        await ctx.response.send_message("Nothing's playing", view=None)

async def clear(ctx):
    if ctx.channel.id == 819991857957830717:
        await ctx.channel.purge(limit=20)

@bot.slash_command(name="tip", description="Give me a generous tip!")
async def tip(ctx):
    await ctx.response.send_message("Thanks for the tip!", file = discord.File("lloyd-tip.gif"))
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

@bot.slash_command(name="score", description="Checks how many times everyone's tipped")
async def score(ctx, user):
    if user == "":
        await ctx.response.send_message("Needs a user!")
    elif "<@!" not in user:
        await ctx.response.send_message("That's not a user!")
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
            await ctx.response.send_message("{} has given me {} tips!".format(tips[place][0], tips[place][1]))
        except:
            await ctx.response.send_message("{} hasn't given me any tips yet! Rude...".format(user))

@bot.slash_command(name="error", description="Tells you exactly how I failed")
async def error(ctx):
    await ctx.response.send_message(file=discord.File("log.txt"))

stopButton.callback = stopInter
pauseButton.callback = pauseInter


bot.run(os.environ.get("LLOYD_TOKEN"))
