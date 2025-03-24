import discord
import asyncio
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import math
import os
from dotenv import load_dotenv
import time
import datetime
import traceback
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from gpiozero import CPUTemperature
load_dotenv()

title = ""
info = {}
link = ""
looping = False
place = 0
timer = 9999999999
max_timer = 60*60

intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot = discord.ext.commands.Bot(command_prefix='.', intents=intents)

playlist = []

i2c = board.I2C()
WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 5
oled_reset = digitalio.DigitalInOut(board.D4)
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)


def drawText(text, fontSize, centered=False):
    oled.fill(0)
    oled.show()

    print("drawing" + text)
    oled.fill(0)
    oled.show()

    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default(size=fontSize)
    bbox = font.getbbox(text)
    (font_width, font_height) = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((oled.width // 2 - font_width // 2 if centered else 5), oled.height // 2 - font_height // 2),
        text,
        font=font,
        fill=255,
    )

    oled.image(image)
    oled.show()

drawText("Lloyd Started!", 16, True)

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio',
    'restrictfilenames': True,
    'no-playlist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
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
        ytdl.cache.remove()
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename
    

status = None
@bot.event
async def on_ready():
    global status
    print('Logged in as {0.user}'.format(bot))
    status = await bot.get_channel(819991857957830717).send("Lloyd Started!", view=None)
    await clear_by_id(819991857957830717)


stopButton = Button(
    style=discord.ButtonStyle.primary,
    emoji="⏹️",
)

pauseButton = Button(
    style=discord.ButtonStyle.primary,
    emoji="⏯️",
)

loopButton = Button(
    style=discord.ButtonStyle.primary,
    emoji="🔁",
)

@bot.slash_command(name='join', description='Tells Lloyd to join the voice channel')
async def join(ctx):
    await ctx.response.send_message("Joining...")
    try:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
    except Exception as err:
        print("Error joining: " + err)
        pass
        # await ctx.response.send_message("You're probably not in a VC, why would you do that?")
    drawText("Lloyd", 16, True)
    await status.edit("Nothing's playing.")
    await clear(ctx)

@bot.slash_command(name='leave', description='Tells Lloyd to leave the voice channel')
async def leave(ctx):
    await ctx.response.send_message("Leaving...")
    try:
        await ctx.guild.voice_client.disconnect()
    except Exception as err:
        print("Error leaving: " + err)
    await clear(ctx)
    await status.edit("I'm not in a VC right now.", view=None)

async def prepare_audio(url, option, timestamp=0):
    global timer
    timer = 9999999999
    with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
        global title, link
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            # take first item from a playlist
            info = info['entries'][0]
        # print(info.keys())
        URL = info['url']
        title = info.get("title", None)
        link = info['webpage_url']

    for i in range(len(url) - 2):
        if url[i:i+2] == "t=":
            timestamp = url[i+2:]
            if "s" in timestamp:
                timestamp = timestamp[:timestamp.index("s"):]
            timestamp = int(timestamp)
    return discord.FFmpegPCMAudio(source=URL, before_options='-vn -ss {} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 16 -loglevel error'.format(timestamp), options=option)

@bot.slash_command(name='play', description='Plays a song')
async def play(ctx, url, speed=1, timestamp=0, bassboost=0, wobble=0, echo=0):
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    
    voice_channel = ctx.guild.voice_client

    if voice_channel == None:
        await ctx.author.voice.channel.connect()
        voice_channel = ctx.guild.voice_client

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
        echo = int(echo)
        echostring = ",aecho=0.8:0.9:"
        for i in range(1, echo + 1):
            echostring += str(1000 * i) + "|"
        echostring = echostring[:-1:] + ":"
        echostring += "0.3|" * echo
        option += echostring[:-1:]
    
    playlist.append([url, option])
    if not ("/" in url and "." in url):
        url = "ytsearch:'{}'".format(url)
    if not voice_channel.is_playing():
        try:
            await ctx.response.send_message("Preparing...", view=None)
            async with ctx.channel.typing():
                voice_channel.play(await prepare_audio(url, option, timestamp), after=lambda error: (asyncio.run_coroutine_threadsafe(HandleEnd(error, ctx), bot.loop)))
                drawText(title, 14)
                print("Playing {}".format(title))
                # if "ytsearch" in url:
                #     await status.edit(content="Playing {} (Looping)".format(title) if looping else "Playing {}".format(title, url), view=view)
                # else:
                await status.edit(content="Playing [{}]({}) (Looping)".format(title, link) if looping else "Playing [{}]({})".format(title, link), view=view)
                await clear(ctx)
        
        except Exception as err:
            print(traceback.format_exc())
            print("Error playing: " + err)
            errorLog = open("/home/pi/Documents/Lloyd/log.txt", "w")
            errorLog.write(str(err))
            errorLog.close()
            await status.edit(content="Something went wrong, please try again", view=None)
            await clear(ctx)
    
    else:
        msg = await ctx.response.send_message("Added to playlist!", view=None)
        await clear(ctx)
        # await msg.delete_original_message()

async def HandleEnd(err, ctx):
    global timer
    global looping
    global place
    global playlist
    timer = max_timer
    asyncio.run_coroutine_threadsafe(timeout(ctx), bot.loop)
    if err == None:
        if looping:
            if place < len(playlist) - 1:
                place += 1
            else:
                place = 0
        else:
            playlist.pop(0)
        if len(playlist) > 0:
            try:
                timestamp = 0
                voice_channel = ctx.guild.voice_client
                url = playlist[place][0]
                option = playlist[place][1]
                view = View()
                view.add_item(stopButton)
                view.add_item(pauseButton)
                view.add_item(loopButton)
                async with ctx.channel.typing():
                    voice_channel.play(await prepare_audio(url, option, timestamp), after=lambda error: (asyncio.run_coroutine_threadsafe(HandleEnd(error, ctx), bot.loop)))
                    drawText(title, 14)
                    await status.edit(content="Playing [{}]({}) (Looping)".format(title, url) if looping else "Playing [{}]({})".format(title, url), view=view)
            except Exception as err:
                print(traceback.format_exc())
                print("Error handling end: " + err)
                errorLog = open("/home/pi/Documents/Lloyd/log.txt", "w")
                errorLog.write(str("Error handling end: " + err))
                errorLog.close()
                await status.edit(content="Something went wrong, please try again", view=None)
                await clear(ctx)
        else:
            drawText("Lloyd", 16, True)
            await status.edit(content="Nothing's playing.", view=None)
    else:
        print(err)
        errorLog = open("/home/pi/Documents/Lloyd/log.txt", "w")
        errorLog.write(str(err))
        errorLog.close()
        await status.edit(content="Something went wrong, please try again", view=None)

@bot.slash_command(name='pause', description='Pauses the song')
async def pause(ctx):
    await ctx.response.send_message("Pausing...")
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_playing():
            await voice_client.pause()
    except Exception as err:
        print("Error pausing: " + err)
        drawText("Lloyd", 16, True)
        await status.edit("Nothing's playing")
    await status.edit("Paused", view=view)
    await clear(ctx)

@bot.slash_command(name='resume', description='Resumes the song')
async def resume(ctx):
    await ctx.response.send_message("Resuming...")
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    voice_client = ctx.guild.voice_client
    try:
        if voice_client.is_paused():
            await voice_client.resume()
    except Exception as err:
        print("Error resuming: " + err)
        drawText("Lloyd", 16, True)
        await status.edit("Nothing's playing")
    await status.edit("Playing [{}]({})".format(title, link), view=view)
    await clear(ctx)

@bot.slash_command(name='stop', description='Stops the song')
async def stop(ctx):
    try:
        await ctx.respond("Stopping...")
        global looping, playlist
        looping = False
        playlist = []
        voice_client = ctx.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        drawText("Lloyd", 16, True)
        await status.edit("Nothing's playing")
        await clear(ctx)
    except Exception as err:
        print(traceback.format_exc())
        print("Error stopping: " + err)
        errorLog = open("/home/pi/Documents/Lloyd/log.txt", "w")
        errorLog.write(str(err))
        errorLog.close()
        await status.edit(content="Something went wrong, please try again", view=None)
        await clear(ctx)

@bot.slash_command(name='skip', description='Skips the song')
async def skip(ctx):
    try:
        await ctx.respond("Skipping...")
        global looping, playlist
        looping = False
        voice_client = ctx.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        await clear(ctx)
    except Exception as err:
        print(traceback.format_exc())
        print("Error with skipping: " + err)
        errorLog = open("/home/pi/Documents/Lloyd/log.txt", "w")
        errorLog.write(str(err))
        errorLog.close()
        await status.edit(content="Something went wrong, please try again", view=None)
        await clear(ctx)

async def pauseInter(ctx):
    await ctx.response.send_message("Pausing...")
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await status.edit(content="Paused", view=view)
    else:
        voice_client.resume()
        await status.edit(content="Playing [{}]({})".format(title, link), view=view)
    await clear(ctx)

async def stopInter(ctx):
    await ctx.response.send_message("Stopping...")
    global looping, playlist
    looping = False
    playlist = []
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    
    drawText("Lloyd", 16, True)
    await status.edit(content="Nothing's playing.", view=None)
    await clear(ctx)

async def loopInter(ctx):
    await ctx.response.send_message("Looping...")
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    global looping
    global place
    looping = not looping
    if not looping:
        place = 0
    await status.edit(content="Playing [{}]({}) (Looping)".format(title, link) if looping else "Playing [{}]({})".format(title, link), view=view)
    await clear(ctx)

@bot.slash_command(name="loop", description="Toggles looping the playlist")
async def loopCommand(ctx):
    await ctx.response.send_message("Looping...")
    global place
    view = View()
    view.add_item(stopButton)
    view.add_item(pauseButton)
    view.add_item(loopButton)
    looping = not looping
    if not looping:
        place = 0
    await status.edit(content="Playing [{}]({}) (Looping)".format(title, link) if looping else "Playing [{}]({})".format(title, link), view=view)
    await clear(ctx)

@bot.slash_command(name='clear', description='Clears the channel')
async def clearCommand(ctx):
    # try:
    #     if ctx.guild.voice_client.is_playing():
    #         view = View()
    #         view.add_item(stopButton)
    #         view.add_item(pauseButton)
    #         view.add_item(loopButton)
    #         await status.edit("Playing [{}]({})".format(title, link), view=view)
    #     else:
    #         await ctx.response.send_message("Nothing's playing", view=None)
    # except:
    #     await ctx.response.send_message("Nothing's playing", view=None)
    await ctx.response.send_message("Clearing...")
    await clear(ctx)

def isnt_status(m):
    return m.id != status.id

async def clear(ctx):
    if ctx.channel.id == 819991857957830717:
        # await ctx.channel.purge(limit=20, before=datetime.datetime.now() - datetime.timedelta(seconds=2))
        await ctx.channel.purge(limit=20, check=isnt_status)

async def clear_by_id(id):
    if id == 819991857957830717:
        # await ctx.channel.purge(limit=20, before=datetime.datetime.now() - datetime.timedelta(seconds=2))
        await bot.get_channel(id).purge(limit=20, check=isnt_status)

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
    await ctx.response.send_message(file=discord.File("/home/pi/Documents/Lloyd/log.txt"))

async def timeout(ctx):
    global timer
    while timer > 0:
        await asyncio.sleep(1)
        timer -= 1
    try:
        await ctx.guild.voice_client.disconnect()
    except Exception as e:
        print("Error on timeout: " + e)

stopButton.callback = stopInter
pauseButton.callback = pauseInter
loopButton.callback = loopInter


bot.run(os.environ.get("LLOYD_TOKEN"))
