from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import asyncio
import logging
import random
import requests
import re
import time
import httpx
import urllib.parse
from typing import List, Optional, Dict
import aiohttp
from youtubesearchpython import VideosSearch
from ytmusicapi import YTMusic
import base64
from Crypto.Cipher import DES

ytmusic = YTMusic()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VortexMusic")

# Global cache for SoundCloud Client ID
SC_CID_CACHE = {"cid": None, "expiry": 0.0}

# Global stream cache: {video_id: {"url": str, "bitrate": int, "expiry": float}}
STREAM_CACHE = {}

def get_cached_stream(video_id: str):
    cached = STREAM_CACHE.get(video_id)
    if cached and cached['expiry'] > time.time():
        return cached['data']
    return None

def set_cached_stream(video_id: str, data: dict):
    STREAM_CACHE[video_id] = {
        'data': data,
        'expiry': time.time() + 1800  # 30 minute cache
    }

def cleanup_cache():
    """Remove expired entries from the cache."""
    current_time = time.time()
    expired_keys = [k for k, v in STREAM_CACHE.items() if v['expiry'] <= current_time]
    for k in expired_keys:
        del STREAM_CACHE[k]

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://inv.tux.pizza",
    "https://iv.melmac.space",
    "https://inv.tuep.pizza",
    "https://invidious.nerdvpn.de",
    "https://iv.ggtyler.dev",
    "https://inv.zzls.xyz",
    "https://iv.datura.network",
    "https://invidious.lunar.icu",
    "https://invidious.flokinet.to"
]

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://piped-api.garudalinux.org",
    "https://api.piped.victr.me",
    "https://pipedapi.leptons.xyz",
    "https://piped-api.lunar.icu"
]

LAVALINK_NODES = [
    {"host": "lavalink-4.oops.moe", "port": 443, "password": "youshallnotpass", "secure": True},
    {"host": "lavalink.lexis.host", "port": 443, "password": "lexishostlavalink", "secure": True},
    {"host": "lava1.free-lavalink.com", "port": 443, "password": "free-lavalink", "secure": True}
]

def decrypt_saavn_url(enc_url: str):
    """Decrypt Saavn encrypted media URLs."""
    try:
        if not enc_url: return None
        # DES key for Saavn is exactly 8 bytes
        des = DES.new(b"38343635", DES.MODE_ECB) 
        cipher_text = base64.b64decode(enc_url)
        dec_text = des.decrypt(cipher_text)
        url = dec_text.decode('utf-8', errors='ignore').split('\x00')[0]
        # Upgrade to 320kbps if possible
        url = url.replace("_96.mp4", "_320.mp4").replace("_160.mp4", "_320.mp4")
        return url
    except Exception as e:
        logger.warning(f"Saavn decryption error: {str(e)}")
        return None

def proxy_thumbnail(url: str, base_url: str = None) -> str:
    """Internal proxy router for maximum reliability."""
    if not url or not url.startswith('http'):
        return 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500'
    
    # 1. Force HTTPS for base_url if it's Render but comes in as http
    if base_url and "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
    
    encoded_url = urllib.parse.quote(url, safe='')
    
    if base_url:
        base = str(base_url).rstrip('/')
        return f"{base}/proxy-image?url={encoded_url}"
    
    return f"https://wsrv.nl/?url={encoded_url}&w=500&h=500&fit=cover&n=-1"

app = FastAPI(title="Vortex Music Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    cleanup_cache()
    return {"status": "healthy", "ver": "v1.1.0-final-fix", "cache_size": len(STREAM_CACHE)}

@app.get("/version")
async def get_version():
    return {"version": "1.1.0"}

@app.get("/ping")
async def ping():
    """Keep-alive endpoint for third-party services like cron-job.org"""
    return {"status": "pong", "timestamp": time.time()}

@app.get("/proxy-image")
async def proxy_image(url: str = Query(...)):
    """Internal image proxy to bypass blocking."""
    try:
        if not url or not url.startswith('http'):
            return Response(status_code=302, headers={"Location": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500"})
            
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://www.youtube.com/"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                return Response(content=resp.content, media_type=content_type)
            else:
                logger.warning(f"Image proxy failed for {url} with status {resp.status_code}")
                # Fallback to a placeholder if source fails
                return Response(status_code=302, headers={"Location": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500"})
    except Exception as e:
        logger.error(f"Image proxy error: {str(e)}")
        return Response(status_code=302, headers={"Location": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500"})

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36',
    'nocheckcertificate': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'],
            'skip': ['hls', 'dash']
        }
    }
}

class SaavnAPI:
    """Helper for JioSaavn Internal API lookup."""
    BASE_URL = "https://www.jiosaavn.com/api.php"
    @staticmethod
    def _format_song(song, base_url: str = None):
        # Upgrade image to 500x500. Support 'image' or 'thumbnail' keys.
        image_data = song.get('image') or song.get('thumbnail')
        image = ""
        if isinstance(image_data, list) and len(image_data) > 0:
            # Handle list of images (highest quality usually last or has quality key)
            image = image_data[-1].get('url') if isinstance(image_data[-1], dict) else str(image_data[-1])
        else:
            image = str(image_data) if image_data else ""

        if image and image.startswith('http'):
            image = image.replace('150x150', '500x500').replace('50x50', '500x500')
            if 'http:' in image and 'https:' not in image:
                image = image.replace('http:', 'https:')
        else:
            image = 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500' # High-quality fallback
        
        # Format duration
        duration = song.get('duration', 0)
        try: duration = int(duration)
        except: duration = 0
            
        return {
            'id': song.get('id'),
            'type': 'saavn',
            'title': song.get('title') or song.get('song'),
            'artist': song.get('primary_artists') or song.get('singers') or 'Unknown',
            'thumbnail': proxy_thumbnail(image, base_url),
            'duration': duration,
            'album': song.get('album'),
            'year': song.get('year'),
            'language': song.get('language'),
            'url': song.get('perma_url'),
            'enc_url': song.get('encrypted_media_url')
        }

    async def search(self, query: str, base_url: str = None):
        params = {
            '__call': 'autocomplete.get',
            '_format': 'json',
            '_marker': '0',
            'cc': 'in',
            'includeMetaTags': '1',
            'query': query
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                songs = data.get('songs', {}).get('data', [])
                return [self._format_song(s, base_url) for s in songs]
        return []

    async def get_charts(self, base_url: str = None):
        # Fetch Weekly Top 15 as home content
        params = {
            '__call': 'content.getCharts',
            '_format': 'json',
            '_marker': '0',
            'cc': 'in',
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                # Return first chart
                if data:
                    chart_id = data[0].get('id')
                    return await self.get_playlist(chart_id, base_url)
        return []

    async def get_playlist(self, listid: str, base_url: str = None):
        params = {
            '__call': 'playlist.getDetails',
            '_format': 'json',
            'listid': listid
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                songs = data.get('songs', [])
                return [self._format_song(s, base_url) for s in songs]
        return []

saavn = SaavnAPI()

def format_search_result(result, base_url: str = None):
    thumbnails = result.get('thumbnails', [])
    thumbnail_url = thumbnails[0].get('url') if thumbnails and isinstance(thumbnails, list) else None
    return {
        'id': result.get('id'),
        'title': result.get('title'),
        'thumbnail': proxy_thumbnail(thumbnail_url, base_url),
        'artist': result.get('descriptionSnippet', [{}])[0].get('text') if result.get('descriptionSnippet') else result.get('channel', {}).get('name'),
        'duration': result.get('duration'),
        'url': f"https://www.youtube.com/watch?v={result.get('id')}",
    }
class AudioDBAPI:
    """Helper for TheAudioDB for artist bios and images."""
    BASE_URL = "https://www.theaudiodb.com/api/v1/json/1" # Public test key

    async def get_artist_info(self, name: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/search.php", params={'s': name}, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    artists = data.get('artists')
                    if artists:
                        artist = artists[0]
                        return {
                            'bio': artist.get('strBiographyEN'),
                            'banner': artist.get('strArtistBanner'),
                            'fanart': artist.get('strArtistFanart'),
                            'logo': artist.get('strArtistLogo'),
                            'style': artist.get('strStyle'),
                            'genre': artist.get('strGenre'),
                            'country': artist.get('strCountry')
                        }
        except Exception as e:
            logger.warning(f"AudioDB Error: {str(e)}")
        return None

class DeezerAPI:
    """Helper for Deezer Search & Metadata."""
    BASE_URL = "https://api.deezer.com"

    async def search(self, query: str, base_url: str = None):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/search", params={'q': query}, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return [{
                        'id': str(track.get('id')),
                        'type': 'deezer',
                        'title': track.get('title'),
                        'artist': track.get('artist', {}).get('name'),
                        'thumbnail': proxy_thumbnail(track.get('album', {}).get('cover_xl') or track.get('album', {}).get('cover_medium'), base_url),
                        'duration': track.get('duration'),
                        'album': track.get('album', {}).get('title'),
                        'source': 'Deezer'
                    } for track in data.get('data', [])[:5]]
        except Exception as e:
            logger.warning(f"Deezer Error: {str(e)}")
        return []

saavn = SaavnAPI()
audiodb = AudioDBAPI()
deezer = DeezerAPI()

@app.get("/artist/{name}")
async def get_artist(name: str):
    info = await audiodb.get_artist_info(name)
    if not info:
        raise HTTPException(status_code=404, detail="Artist info not found")
    return info

from fastapi import Request

@app.get("/search")
async def search(request: Request, q: str = Query(...)):
    base_url = str(request.base_url)
    try:
        # Parallel Search: Saavn + Deezer
        results_saavn: List = []
        results_deezer: List = []
        
        try:
            # Parallel Search: Saavn + Deezer
            results = await asyncio.gather(
                saavn.search(q, base_url),
                deezer.search(q, base_url),
                return_exceptions=True
            )
            results_saavn = results[0] if not isinstance(results[0], Exception) else []
            results_deezer = results[1] if not isinstance(results[1], Exception) else []
            # Handle potential exceptions from gather
            if isinstance(results_saavn, Exception): results_saavn = []
            if isinstance(results_deezer, Exception): results_deezer = []
        except Exception as ge:
            logger.warning(f"Gather error: {str(ge)}")

        # Merge results, prioritizing Saavn for Indian content (first 10), then Deezer
        final_merged = []
        if isinstance(results_saavn, list):
            final_merged.extend(results_saavn[:10])
        if isinstance(results_deezer, list):
            final_merged.extend(results_deezer)
            
        if final_merged:
            return final_merged
            
        # Fallback: YouTube Search
        search_engine = VideosSearch(q, limit=15)
        yt_results = search_engine.result().get('result', [])
        return [format_search_result(v, base_url) for v in yt_results]
    except Exception as e:
        logger.error(f"Search Error: {str(e)}")
        return []

@app.get("/trending")
async def trending(request: Request):
    base_url = str(request.base_url)
    try:
        # Get Saavn Charts
        results = await saavn.get_charts(base_url)
        if results:
            return results
            
        # YT fallback
        search_engine = VideosSearch("popular music 2024", limit=10)
        yt_results = search_engine.result().get('result', [])
        return [format_search_result(v, base_url) for v in yt_results]
    except Exception as e:
        logger.error(f"Trending Error: {str(e)}")
        return []

@app.get("/home")
async def home_content(request: Request):
    base_url = str(request.base_url)
    try:
        trending_songs = await trending(request)
        return {
            "trending": trending_songs,
            "recently_played": trending_songs[:4] 
        }
    except Exception as e:
        logger.error(f"Home Content Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Home content failed")

def is_duration_match(meta_duration, stream_duration):
    """Verify if the audio duration matches the metadata within a reasonable threshold."""
    if not meta_duration or not stream_duration:
        return True # Can't verify, trust but trace
    
    try:
        # Convert both to float
        m_dur = float(meta_duration)
        s_dur = float(stream_duration)
        
        # Threshold: 15% or 30 seconds, whichever is smaller
        threshold = min(m_dur * 0.15, 30.0)
        diff = abs(m_dur - s_dur)
        
        if diff <= threshold:
            return True
        logger.warning(f"Duration mismatch: Meta={m_dur}s vs Stream={s_dur}s (Diff={diff}s)")
        return False
    except:
        return True


class RobustYouTubeExtractor:
    """Uses multiple methods to extract audio streams with maximum reliability."""
    
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36',
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                    'skip': ['hls', 'dash']
                }
            }
        }

    async def get_audio_stream(self, video_id: str) -> Optional[Dict]:
        """Try multiple methods sequentially with fallback."""
        methods = [
            (self._extract_with_ytdlp, "yt-dlp"),
            (self._extract_with_piped, "Piped"),
            (self._extract_with_invidious, "Invidious"),
            (self._extract_with_pytubefix, "pytubefix")
        ]
        
        # Check cache first
        cached = get_cached_stream(video_id)
        if cached:
            logger.info(f"Using cached stream for {video_id}")
            return cached

        for method, name in methods:
            try:
                logger.info(f"Trying extraction method: {name}")
                result = await method(video_id)
                if result:
                    result['method'] = name
                    set_cached_stream(video_id, result)
                    return result
            except Exception as e:
                logger.warning(f"Method {name} failed: {str(e)}")
                continue
        return None

    async def _extract_with_ytdlp(self, video_id: str):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return {'url': info.get('url'), 'bitrate': info.get('abr', 128), 'duration': info.get('duration')}

    async def _extract_with_piped(self, video_id: str):
        instance = random.choice(PIPED_INSTANCES)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{instance}/streams/{video_id}")
            if resp.status_code == 200:
                data = resp.json()
                audio_streams = data.get('audioStreams', [])
                if audio_streams:
                    best = sorted(audio_streams, key=lambda x: x.get('bitrate', 0), reverse=True)[0]
                    return {'url': best.get('url'), 'bitrate': best.get('bitrate', 128), 'duration': data.get('duration')}
        return None

    async def _extract_with_invidious(self, video_id: str):
        instance = random.choice(INVIDIOUS_INSTANCES)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{instance}/api/v1/videos/{video_id}")
            if resp.status_code == 200:
                data = resp.json()
                adaptive_formats = data.get('adaptiveFormats', [])
                audio_formats = [f for f in adaptive_formats if f.get('type', '').startswith('audio/')]
                if audio_formats:
                    best = sorted(audio_formats, key=lambda x: int(x.get('bitrate') or 0), reverse=True)[0]
                    return {'url': best.get('url'), 'bitrate': int(best.get('bitrate', 128)), 'duration': data.get('lengthSeconds')}
        return None

    async def _extract_with_pytubefix(self, video_id: str):
        from pytubefix import YouTube
        yt = YouTube(f"https://youtube.com/watch?v={video_id}")
        audio_stream = yt.streams.get_audio_only()
        if audio_stream:
            return {'url': audio_stream.url, 'bitrate': 128, 'duration': yt.length}
        return None

extractor = RobustYouTubeExtractor()

async def proxy_stream_iter(url: str, start_byte: int = 0):
    """Generator to proxy audio bytes with range support."""
    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        if start_byte > 0:
            headers['Range'] = f'bytes={start_byte}-'
            
        async with session.get(url, headers=headers) as resp:
            async for chunk in resp.content.iter_chunked(64 * 1024): # 64KB chunks
                yield chunk

@app.get("/stream")
async def get_stream(
    request: Request,
    id: str = Query(...), 
    title: Optional[str] = Query(None), 
    artist: Optional[str] = Query(None),
    duration_total: Optional[str] = Query(None),
    enc_url: Optional[str] = Query(None)
):
    base_url = str(request.base_url)
    if "onrender.com" in base_url:
        base_url = base_url.replace("http://", "https://")
    
    # JioSaavn Direct Decryption
    if id.startswith('saavn_') or enc_url:
        secret_url = enc_url
        if not secret_url:
            try:
                sid = id.replace('saavn_', '')
                async with httpx.AsyncClient() as client:
                    ds = await client.get(f"https://www.jiosaavn.com/api.php?__call=song.getDetails&pids={sid}&_format=json&_marker=0&api_version=4&ctx=web6dot0", timeout=5.0)
                    if ds.status_code == 200:
                        s_data = ds.json()
                        song_obj = s_data.get(sid) or list(s_data.values())[0] if s_data else {}
                        secret_url = song_obj.get('encrypted_media_url')
            except: pass
        
        if secret_url:
            stream_link = decrypt_saavn_url(secret_url)
            if stream_link:
                # Proxy Saavn too for reliability
                return StreamingResponse(proxy_stream_iter(stream_link), media_type="audio/mpeg")

    # YouTube Extraction with Robust Fallback
    yt_id = id
    if (len(id) != 11 or id.startswith('saavn_')) and title and artist:
        try:
            search_results = ytmusic.search(f"{title} {artist}", filter="songs", limit=1)
            if search_results:
                yt_id = search_results[0].get('videoId')
        except: pass

    if yt_id:
        stream_info = await extractor.get_audio_stream(yt_id)
        if stream_info:
            # Handle Range header for scrubbing
            range_header = request.headers.get('range')
            start_byte = 0
            if range_header:
                try:
                    start_byte = int(range_header.replace('bytes=', '').split('-')[0])
                except: pass

            return StreamingResponse(
                proxy_stream_iter(stream_info['url'], start_byte),
                status_code=206 if range_header else 200,
                media_type="audio/mpeg",
                headers={
                    "X-Stream-Source": stream_info['method'],
                    "X-Bitrate": str(stream_info['bitrate']),
                    "Accept-Ranges": "bytes"
                }
            )

    raise HTTPException(status_code=503, detail="No robust stream available")

@app.get("/stream-info")
async def get_stream_info(
    request: Request,
    id: str = Query(...), 
    title: Optional[str] = Query(None), 
    artist: Optional[str] = Query(None),
    duration_total: Optional[str] = Query(None),
    enc_url: Optional[str] = Query(None)
):
    """Metadata-only endpoint for the frontend to get the actual stream URL and info."""
    base_url = str(request.base_url)
    if "onrender.com" in base_url:
        base_url = base_url.replace("http://", "https://")
    
    stream_url = None
    thumbnail = None
    duration = 0
    
    # JioSaavn Direct 
    if id.startswith('saavn_') or enc_url:
        secret_url = enc_url
        if not secret_url:
            try:
                sid = id.replace('saavn_', '')
                async with httpx.AsyncClient() as client:
                    ds = await client.get(f"https://www.jiosaavn.com/api.php?__call=song.getDetails&pids={sid}&_format=json&_marker=0&api_version=4&ctx=web6dot0", timeout=5.0)
                    if ds.status_code == 200:
                        s_data = ds.json()
                        song_obj = s_data.get(sid) or list(s_data.values())[0] if s_data else {}
                        secret_url = song_obj.get('encrypted_media_url')
                        thumbnail = song_obj.get('image') or song_obj.get('thumbnail')
                        duration = int(song_obj.get('duration', 0))
            except: pass
        
        if secret_url:
            stream_url = f"{base_url.rstrip('/')}/stream?id={id}&enc_url={urllib.parse.quote(secret_url)}"
    
    # YouTube Fallback
    if not stream_url:
        yt_id = id
        if (len(id) != 11 or id.startswith('saavn_')) and title and artist:
            try:
                search_results = ytmusic.search(f"{title} {artist}", filter="songs", limit=1)
                if search_results:
                    yt_id = search_results[0].get('videoId')
            except: pass

        if yt_id:
            stream_info = await extractor.get_audio_stream(yt_id)
            if stream_info:
                stream_url = f"{base_url.rstrip('/')}/stream?id={yt_id}"
                duration = stream_info.get('duration', 0)
                thumbnail = f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg"
    
    if not stream_url:
        raise HTTPException(status_code=503, detail="No robust stream available")

    # Final polish for thumbnail URL
    if thumbnail and isinstance(thumbnail, str):
        thumbnail = thumbnail.replace('150x150', '500x500').replace('50x50', '500x500')

    return {
        "stream_url": stream_url,
        "thumbnail": proxy_thumbnail(thumbnail, base_url) if thumbnail else None,
        "duration": duration * 1000 if duration else None, # frontend expects millis
        "id": id
    }

@app.get("/warmup")
async def warmup(ids: str = Query(...)):
    """Pre-extract multiple IDs to warm up the cache."""
    id_list = ids.split(',')
    warmed = []
    
    async def task(vid):
        try:
            res = await extractor.get_audio_stream(vid)
            if res: warmed.append(vid)
        except: pass

    # Run up to 5 warmups in parallel to avoid overwhelming
    chunks = [id_list[i:i + 5] for i in range(0, len(id_list), 5)]
    for chunk in chunks:
        await asyncio.gather(*(task(vid) for vid in chunk))
    
    return {"warmed": warmed, "count": len(warmed)}

@app.get("/stream/health/{video_id}")
async def check_stream_health(video_id: str):
    """Check if a song is playable."""
    start_time = time.time()
    try:
        stream_info = await extractor.get_audio_stream(video_id)
        return {
            "available": bool(stream_info),
            "method": stream_info.get('method') if stream_info else None,
            "response_time": time.time() - start_time,
            "bitrate": stream_info.get('bitrate') if stream_info else None
        }
    except Exception as e:
        return {"available": False, "error": str(e)}

@app.get("/test/stream/{video_id}")
async def test_specific_method(video_id: str, method: str = Query("yt-dlp")):
    """Internal debugging endpoint."""
    try:
        if method == "yt-dlp": res = await extractor._extract_with_ytdlp(video_id)
        elif method == "piped": res = await extractor._extract_with_piped(video_id)
        elif method == "invidious": res = await extractor._extract_with_invidious(video_id)
        elif method == "pytubefix": res = await extractor._extract_with_pytubefix(video_id)
        else: return {"error": "Invalid method"}
        return {"available": bool(res), "data": res}
    except Exception as e:
        return {"available": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
