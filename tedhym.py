import discord
import traceback
from urllib.parse import urlparse
from yt_dlp import YoutubeDL

'''
Tedhym
'''

DEBUG = True
def debug_print(*args):
    if DEBUG:
        print("TEDHYM DEBUG:", *args)

def error_print(*args):
    print("TEDHYM ERROR:", *args)

class Track():
    title: str
    url: str

    def __init__(self, title, url):
        self.title = title
        self.url = url

class Tedhym():
    YTD_OPTIONS = {}
    TEDHYM_FATAL_ERROR = "Tedhym encountered an internal error."

    def __init__(self, guild_id):
        # youtube-dl
        self.ytd = YoutubeDL(self.YTD_OPTIONS)

        # guild_id to ensure that an instance only serves requests from the discord server that created it
        self.guild_id = guild_id

        # used for skip
        self.now_playing = ""

        # unoptimized queue FIXME
        self.queue = []

        # hack https://stackoverflow.com/questions/66070749/how-to-fix-discord-music-bot-that-stops-playing-before-the-song-is-actually-over
        self.ffmpeg_options = {
                'options': '-vn',
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            }

    @property
    def voice_client(self):
        return self.guild_id.voice_client
    
    async def play(self, reply_channel, voice_channel, link):
        # should not happen (this is a security hole)
        if voice_channel.guild != self.guild_id:
            error_print("Wrong Tedhym instance")
            await reply_channel.send(self.TEDHYM_FATAL_ERROR)
            return

        # ensure that Tedhym is connected to the correct voice channel
        if self.voice_client != None:
            if self.voice_client.is_connected() == False:
                # bot is supposed to be connected to voice but its not

                # call disconnect (sometimes connect() errors out saying 
                # that bot is already connected to a channel idk why)
                try:
                    await voice_channel.connect()
                except:
                    traceback.print_exc()
                    await reply_channel.send("Warning: force disconnecting bot due to an error")
                    await self.voice_client.disconnect(force=True)
                    await voice_channel.connect()
                
            elif self.voice_client.channel != voice_channel:
                # bot is supposed to be connected to different voice channel
                self.voice_client.move_to(voice_channel)
            else:
                # do nothing
                pass
        else:
            await voice_channel.connect()

        # get title of video and its url
        ytd_info = self.get_url(link)
        if ytd_info == None:
            error_print("get_url failed")
            await reply_channel.send(self.TEDHYM_FATAL_ERROR)
            return

        title, url = (ytd_info["title"], ytd_info['webpage_url'])

        self.queue.append(Track(title, url))
        if self.voice_client.is_playing() == False:
            self.play_next_in_queue()
            
        await reply_channel.send("Added **{}** ({}) to queue".format(title, url))

    async def show_queue(self, reply_channel):
        if self.voice_client != None and self.voice_client.is_playing():
            queue_msg = "Currently playing: **{}** ({})\n\nIn queue:\n".format(self.now_playing.title, self.now_playing.url)
            if len(self.queue) == 0:
                queue_msg = queue_msg + "None\n"
            else:
                for i, track in enumerate(self.queue):
                    queue_msg = queue_msg + "{}. **{}** ({})\n".format(i+1, track.title, track.url)
            queue_msg = queue_msg + "\nTo skip current track, type `/skip`\n"
            queue_msg = queue_msg + "\nTo remove an item in queue, type `/skip <number>`"
            await reply_channel.send(queue_msg)

    async def nowplaying(self, reply_channel):
        if self.voice_client != None and self.voice_client.is_playing():
            await reply_channel.send("Currently playing **{}** ({})".format(self.now_playing.title, self.now_playing.url))

    async def skip(self, reply_channel, index=None):
        if self.voice_client != None and self.voice_client.is_playing():
            if index == None:
                self.voice_client.stop()
                await reply_channel.send("Skipped **{}**".format(self.now_playing.title))
            else:
                index -= 1 # convert to zero-based numbering
                if 0 <= index < len(self.queue):
                    remove = self.queue.pop(index)
                    await reply_channel.send("Removed **{}** from queue".format(remove.title))
                else:
                    await reply_channel.send("Invalid number")


    def after(self, error):
        print('after called, error:', error)
        # sometimes it calls after() when the bot ends up disconnecting (eg. crashes when kicked from the vc and theres still music in queue)
        if self.voice_client != None and self.voice_client.is_connected():
            self.play_next_in_queue()
        
    def play_next_in_queue(self):
        if len(self.queue) > 0:
            track = self.queue.pop(0)

            # we need to reobtain ytd_info as many audio stream urls expire after a period of time
            ytd_info = self.get_url(track.url)
            if ytd_info == None:
                error_print("get_url failed")
                #await reply_channel.send(self.TEDHYM_FATAL_ERROR)
                return

            self.now_playing = track
            self.voice_client.play(discord.FFmpegPCMAudio(self.get_stream_url(ytd_info), **(self.ffmpeg_options)), after=self.after) #need pynacl

    # this might look hacky
    def get_url(self, link):
        try:
            ytd_info = self.ytd.extract_info(link, download=False)
        except:
            if link.startswith("ytsearch:") == False:
                # handle youtube search terms
                return self.get_url("ytsearch:" + link)
            else:
                # youtube search failed
                error_print("info extraction failed")
                return None


        # extraction successful
        # the contents of ytd_info is documented at https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L87
        # which also says that dictionary entries might not be present
        # so avoid using code like ytd_info["acodec"] and use ytd_info.get("acodec", None) instead to prevent crashes
        debug_print("extract_info successful")

        # convert non-video types to video
        # TODO: implement video selection
        ytd_info_type = ytd_info.get("_type", "video")
        if ytd_info_type == "playlist" or ytd_info_type == "multi_video":
            ytd_info = ytd_info["entries"][0]
        elif ytd_info_type == "url" or ytd_info_type == "url_transparent":
            # TODO
            pass
        return ytd_info

    # get actual stream url
    def get_stream_url(self, ytd_info):
        # some videos have ytd_info["url"] instead of ytd_info["formats"]
        # convert ytd_info["url"] into ytd_info["formats"][0]["url"]
        if "url" in ytd_info:
            ytd_info["formats"] = [{"url": ytd_info["url"]}]

        # audio search
        target_bitrate = 128
        best_match_bitrate_delta = 2 ** 32
        best_match = ""

        # try opus @ target_bitrate (for youtube)
        for format in ytd_info["formats"]:
            if format.get("acodec", None) == "opus" and abs(format.get("abr", 0) - target_bitrate) < best_match_bitrate_delta:
                best_match = format["url"]
                best_match_bitrate_delta = abs(format.get("abr", 0) - target_bitrate)

        # if opus @ target_bitrate not found
        if best_match == "" and len(ytd_info["formats"]) > 0:
            debug_print("audio stream not found; using first available format") # TODO save bandwidth by reducing video quality if possible
            error_print("first available format might not contain audio") # TODO
            best_match = ytd_info["formats"][0]["url"]
            best_match_bitrate_delta = 0

        debug_print("best_match url: {}".format(best_match))
        return best_match
