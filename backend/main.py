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
from typing import List, Optional
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
        des = DES.new(b"3834363538333538", DES.MODE_ECB)
        cipher_text = base64.b64decode(enc_url)
        dec_text = des.decrypt(cipher_text)
        url = dec_text.decode('utf-8').split('\x00')[0] # Minimal unpad
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
    return {"status": "healthy", "ver": "v1.1.0-final-fix"}

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
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.google.com/"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return Response(content=resp.content, media_type=resp.headers.get("Content-Type", "image/jpeg"))
            else:
                # Fallback to a placeholder if source fails
                return Response(status_code=302, headers={"Location": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500"})
    except Exception as e:
        logger.error(f"Image proxy error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to proxy image")

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
    return {
        'id': result.get('id'),
        'title': result.get('title'),
        'thumbnail': proxy_thumbnail(result.get('thumbnails', [{}])[0].get('url'), base_url),
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
            results_saavn, results_deezer = await asyncio.gather(
                saavn.search(q, base_url),
                deezer.search(q, base_url),
                return_exceptions=True
            )
            # Handle potential exceptions from gather
            if isinstance(results_saavn, Exception): results_saavn = []
            if isinstance(results_deezer, Exception): results_deezer = []
        except Exception as ge:
            logger.warning(f"Gather error: {str(ge)}")

        # Merge results, prioritizing Saavn for Indian content (first 10), then Deezer
        final_merged = []
        if isinstance(results_saavn, list):
            final_merged.extend(list(results_saavn)[:10])
        if isinstance(results_deezer, list):
            final_merged.extend(list(results_deezer))
            
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


async def fetch_invidious_stream(client: httpx.AsyncClient, instance: str, video_id: str):
    """Helper to fetch stream from a single Invidious instance."""
    try:
        resp = await client.get(f"{instance}/api/v1/videos/{video_id}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            adaptive_formats = data.get('adaptiveFormats', [])
            audio_formats = [f for f in adaptive_formats if f.get('type', '').startswith('audio/')]
            if audio_formats:
                best_audio = sorted(audio_formats, key=lambda x: int(x.get('bitrate') or 0), reverse=True)[0]
                thumb = data.get('videoThumbnails', [{}])[0].get('url') if data.get('videoThumbnails') else None
                if thumb and thumb.startswith('/'): thumb = f"{instance}{thumb}"
                
                return {
                    'stream_url': best_audio.get('url'),
                    'title': data.get('title'),
                    'thumbnail': thumb, # Raw
                    'artist': data.get('author'),
                    'duration': data.get('lengthSeconds'),
                    'source': f'Invidious ({instance})'
                }
    except: pass
    return None

async def fetch_piped_stream(client: httpx.AsyncClient, instance: str, video_id: str):
    """Fetch stream from Piped API."""
    try:
        resp = await client.get(f"{instance}/streams/{video_id}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            audio_streams = data.get('audioStreams', [])
            if audio_streams:
                best = sorted(audio_streams, key=lambda x: x.get('bitrate', 0), reverse=True)[0]
                return {
                    'stream_url': best.get('url'),
                    'title': data.get('title'),
                    'thumbnail': data.get('thumbnailUrl'), # Raw
                    'artist': data.get('uploader'),
                    'duration': data.get('duration'),
                    'source': f'Piped ({instance})'
                }
    except: pass
    return None

async def fetch_lavalink_stream(client: httpx.AsyncClient, node: dict, identifier: str):
    """Fetch track info via Lavalink v4 REST API."""
    try:
        protocol = "https" if node['secure'] else "http"
        base = f"{protocol}://{node['host']}:{node['port']}"
        headers = {"Authorization": node['password']}
        resp = await client.get(f"{base}/v4/loadtracks?identifier={identifier}", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('loadType') in ['track', 'search'] and data.get('data'):
                track_data = data['data'][0] if data['loadType'] == 'search' else data['data']
                return {
                    'title': track_data['info']['title'],
                    'artist': track_data['info']['author'],
                    'duration': track_data['info']['length'] // 1000,
                    'thumbnail': track_data['info'].get('artworkUrl'), # Raw
                    'source': f"Lavalink ({node['host']})"
                }
    except: pass
    return None

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
    
    # 0. Primary Fix: Direct Saavn Decryption (Extremely reliable)
    if id.startswith('saavn_') or enc_url:
        logger.info(f"Using direct Saavn decryption for: {id}")
        # Try decrypting the enc_url if provided, or fetch it if not
        secret_url = enc_url
        if not secret_url:
            # Fetch song details to get encrypted_media_url
            try:
                sid = id.replace('saavn_', '')
                async with httpx.AsyncClient() as client:
                    ds = await client.get(f"https://www.jiosaavn.com/api.php?__call=song.getDetails&pids={sid}&_format=json&_marker=0&api_version=4&ctx=web6dot0", timeout=5.0)
                    if ds.status_code == 200:
                        s_data = ds.json()
                        # The response is usually a dict where keys are IDs
                        song_obj = s_data.get(sid) or list(s_data.values())[0] if s_data else {}
                        secret_url = song_obj.get('encrypted_media_url')
            except: pass
        
        if secret_url:
            stream_link = decrypt_saavn_url(secret_url)
            if stream_link:
                # Get a thumbnail from YT search as Saavn thumbnails are often tiny or blocked
                thumb = 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500'
                try:
                    search = VideosSearch(f"{title} {artist}", limit=1)
                    res = search.result().get('result', [])
                    if res: thumb = res[0].get('thumbnails', [{}])[0].get('url')
                except: pass
                
                return {
                    'stream_url': stream_link,
                    'title': title or "Saavn Track",
                    'thumbnail': proxy_thumbnail(thumb, base_url),
                    'artist': artist or "JioSaavn",
                    'duration': int(duration_total) if duration_total else 0,
                    'source': 'JioSaavn (Direct)'
                }

    """
    Optimized streaming logic with parallel lookups and caching.
    Priority: Piped/Invidious Race -> SoundCloud (HLS) -> pytubefix -> yt-dlp
    """
    yt_id = id
    
    # Resolve Saavn/Other non-YT IDs with YTMusic pinpoint
    if (len(id) != 11 or id.startswith('saavn_') or id.startswith('deezer_')) and title and artist:
        logger.info(f"Resolving metadata for: {title} - {artist}")
        try:
            ytm = YTMusic()
            search_results = ytm.search(f"{title} {artist}", filter="songs", limit=1)
            if search_results:
                yt_id = search_results[0].get('videoId')
                logger.info(f"YTMusic resolved to: {yt_id}")
        except Exception as yte:
            logger.warning(f"YTMusic resolution failed: {str(yte)}")

    # 1. Parallel Invidious + Piped Race
    if yt_id:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=3.0) as client:
                inv_tasks = [fetch_invidious_stream(client, inst, yt_id) for inst in INVIDIOUS_INSTANCES]
                piped_tasks = [fetch_piped_stream(client, inst, yt_id) for inst in PIPED_INSTANCES]
                
                tasks = inv_tasks + piped_tasks
                random.shuffle(tasks) # Avoid overloading first ones
                
                found_res = None
                for completed_task in asyncio.as_completed(tasks):
                    res = await completed_task
                    if res and isinstance(res, dict):
                        # Duration Guard
                        if title and artist and duration_total:
                            if not is_duration_match(duration_total, res.get('duration')):
                                continue
                        
                        found_res = res
                        break
                
                if found_res and isinstance(found_res, dict):
                    found_res['thumbnail'] = proxy_thumbnail(found_res.get('thumbnail'), base_url)
                    logger.info(f"SUCCESS: {found_res.get('source')}")
                    return found_res
        except Exception as race_e:
            logger.warning(f"Race error: {str(race_e)}")

    # 1.5 Lavalink Metadata/Stream Check
    if yt_id:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                for node in LAVALINK_NODES:
                    res = await fetch_lavalink_stream(client, node, yt_id)
                    if res:
                        # If Lavalink found it, we can use the metadata and proceed to other fallbacks for stream_url
                        # if the node doesn't provide a direct stream_url in REST response
                        logger.info(f"Lavalink confirmed track: {res['title']}")
                        # We still need a stream_url, so we continue to SoundCloud/Pytubefix if needed
                        break
        except Exception as l_e:
            logger.warning(f"Lavalink check failed: {str(l_e)}")

    # 4. Ultimate Fallback: yt-dlp
    if yt_id:
        try:
            # Clear cache to avoid temporary blocks
            with yt_dlp.YoutubeDL({**YDL_OPTIONS, 'cookiefile': None}) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={yt_id}", download=False)
                return {
                    'stream_url': info.get('url'),
                    'title': info.get('title'),
                    'thumbnail': proxy_thumbnail(info.get('thumbnail'), base_url),
                    'artist': info.get('uploader'),
                    'duration': info.get('duration'),
                    'source': 'yt-dlp'
                }
        except Exception: pass

    # 3. Fallback: SoundCloud HLS (Safety Net)
    logger.info("Falling back to SoundCloud HLS")
    try:
        search_query = f"{title} {artist}" if title and artist else title or "song"
        global SC_CID_CACHE
        cid = SC_CID_CACHE.get("cid")
        expiry = float(SC_CID_CACHE.get("expiry", 0.0))
        if not cid or time.time() > expiry:
            rsc = requests.get('https://soundcloud.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            js_matches = re.findall(r'src=\"(https://a-v2\.sndcdn\.com/assets/[^\"]+\.js)\"', rsc.text)
            for js_url in js_matches:
                rj = requests.get(js_url, timeout=5)
                cid_match = re.search(r'client_id:\"([a-zA-Z0-9]{32})\"', rj.text)
                if cid_match:
                    cid = cid_match.group(1)
                    SC_CID_CACHE = {"cid": cid, "expiry": time.time() + 3600}
                    break
        
        if cid:
            rss = requests.get(f'https://api-v2.soundcloud.com/search/tracks?q={search_query}&client_id={cid}&limit=1', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if rss.status_code == 200:
                sc_results = rss.json().get('collection', [])
                if sc_results:
                    track = sc_results[0]
                    transcodings = track.get('media', {}).get('transcodings', [])
                    best = next((t for t in transcodings if t.get('format', {}).get('protocol') == 'hls'), None)
                    if best:
                        ru = requests.get(best['url'] + f'?client_id={cid}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if ru.status_code == 200:
                            logger.info("SUCCESS: SoundCloud HLS")
                            thumb = track.get('artwork_url', '').replace('-large', '-t500x500')
                            if thumb.startswith('http:'): thumb = thumb.replace('http:', 'https:')
                            return {
                                'stream_url': ru.json()['url'],
                                'title': track.get('title'),
                                'thumbnail': proxy_thumbnail(thumb or 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500'),
                                'artist': track.get('user', {}).get('username'),
                                'duration': track.get('duration') // 1000,
                                'source': 'SoundCloud'
                            }
    except Exception as sce:
        logger.warning(f"SoundCloud safety fallback failed: {str(sce)}")

    # 5. Fallback: pytubefix (Last resort as it's often throttled)
    if yt_id:
        try:
            from pytubefix import YouTube
            yt = YouTube(f"https://youtube.com/watch?v={yt_id}")
            audio_stream = yt.streams.get_audio_only()
            if audio_stream:
                logger.info("SUCCESS: pytubefix")
                return {
                    'stream_url': audio_stream.url,
                    'title': yt.title,
                    'thumbnail': proxy_thumbnail(yt.thumbnail_url),
                    'artist': yt.author,
                    'duration': yt.length,
                    'source': 'pytubefix'
                }
        except Exception as py_e:
            logger.warning(f"pytubefix (last resort) failed: {str(py_e)}")

    raise HTTPException(status_code=503, detail="No stream available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
