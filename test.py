import yt_dlp as youtube_dl


ytdl_format_options = {
    'format': 'bestaudio',
    'restrictfilenames': True,
    'no-playlist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    # 'quiet': True,
    'no_warnings': True,
    'verbose': True,
    'default_search': 'ytsearch',
    # 'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
    # 'downloader': 'm3u8:native'
    # 'youtube_include_dash_manifest': False,
    # 'youtube_include_hls_manifest': False,
}

# dict_keys(['id', 'title', 'formats', 'thumbnails', 'thumbnail', 'description', 'channel_id', 'channel_url', 'duration', 'view_count', 'average_rating', 'age_limit', 'webpage_url', 'categories', 'tags', 'playable_in_embed', 'live_status', 'media_type', 'release_timestamp', '_format_sort_fields', 'automatic_captions', 'subtitles', 'comment_count', 'chapters', 'heatmap', 'like_count', 'channel', 'channel_follower_count', 'license', 'channel_is_verified', 'uploader', 'uploader_id', 'uploader_url', 'upload_date', 'timestamp', 'availability', 'original_url', 'webpage_url_basename', 'webpage_url_domain', 'extractor', 'extractor_key', 'playlist', 'playlist_index', 'display_id', 'fulltitle', 'duration_string', 'release_year', 'is_live', 'was_live', 'requested_subtitles', '_has_drm', 'epoch', 'requested_formats', 'format', 'format_id', 'ext', 'protocol', 'language', 'format_note', 'filesize_approx', 'tbr', 'width', 'height', 'resolution', 'fps', 'dynamic_range', 'vcodec', 'vbr', 'stretched_ratio', 'aspect_ratio', 'acodec', 'abr', 'asr', 'audio_channels'])
# ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
# help(y)

def prepare_audio(url, option, timestamp=0):
    try:
        global timer
        timer = 9999999999
        with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
            ydl.cache.remove()
            global title, link
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            URL = info['url']
            title = info.get("title", None)
            link = info['webpage_url']

        for i in range(len(url) - 2):
            if url[i:i+2] == "t=":
                timestamp = url[i+2:]
                if "s" in timestamp:
                    timestamp = timestamp[:timestamp.index("s"):]
                timestamp = int(timestamp)

        print(URL)
    except:
        pass

        
prepare_audio("https://www.youtube.com/watch?v=u5NqO2v_xnY", "")