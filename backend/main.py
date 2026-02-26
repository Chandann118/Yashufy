from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import asyncio
import logging
import random
import requests
import re
import time
import httpx
from typing import List, Optional
from youtubesearchpython import VideosSearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VortexMusic")

# Global cache for SoundCloud Client ID
SC_CID_CACHE = {"cid": None, "expiry": 0.0}

app = FastAPI(title="Vortex Music Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "ver": "v1.0.7-verified-streaming"}

@app.get("/version")
async def get_version():
    return {"version": "1.0.1-yt-search-python"}

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
    def _format_song(song):
        # Upgrade image to 500x500
        image = song.get('image', '').replace('150x150', '500x500')
        if image.startswith('http:'): image = image.replace('http:', 'https:')
        
        # Format duration
        duration = song.get('duration', 0)
        try: duration = int(duration)
        except: duration = 0
            
        return {
            'id': song.get('id'),
            'type': 'saavn',
            'title': song.get('title') or song.get('song'),
            'artist': song.get('primary_artists') or song.get('singers') or 'Unknown',
            'thumbnail': image,
            'duration': duration,
            'album': song.get('album'),
            'year': song.get('year'),
            'language': song.get('language'),
            'url': song.get('perma_url')
        }

    async def search(self, query: str):
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
                return [self._format_song(s) for s in songs]
        return []

    async def get_charts(self):
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
                    return await self.get_playlist(chart_id)
        return []

    async def get_playlist(self, listid: str):
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
                return [self._format_song(s) for s in songs]
        return []

saavn = SaavnAPI()

def format_search_result(result):
    return {
        'id': result.get('id'),
        'title': result.get('title'),
        'thumbnail': result.get('thumbnails', [{}])[0].get('url'),
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

    async def search(self, query: str):
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
                        'thumbnail': track.get('album', {}).get('cover_xl') or track.get('album', {}).get('cover_medium'),
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

@app.get("/search")
async def search(q: str = Query(...)):
    try:
        # Parallel Search: Saavn + Deezer
        results_saavn: List = []
        results_deezer: List = []
        
        try:
            results_saavn, results_deezer = await asyncio.gather(
                saavn.search(q),
                deezer.search(q),
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
        return [format_search_result(v) for v in yt_results]
    except Exception as e:
        logger.error(f"Search Error: {str(e)}")
        return []

@app.get("/trending")
async def trending():
    try:
        # Get Saavn Charts
        results = await saavn.get_charts()
        if results:
            return results
            
        # YT fallback
        search_engine = VideosSearch("popular music 2024", limit=10)
        yt_results = search_engine.result().get('result', [])
        return [format_search_result(v) for v in yt_results]
    except Exception as e:
        logger.error(f"Trending Error: {str(e)}")
        return []

@app.get("/home")
async def home_content():
    try:
        trending_songs = await trending()
        return {
            "trending": trending_songs,
            "recently_played": trending_songs[:4] 
        }
    except Exception as e:
        logger.error(f"Home Content Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Home content failed")


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
                
                # Fix relative thumbnails
                thumb = data.get('videoThumbnails', [{}])[0].get('url') if data.get('videoThumbnails') else None
                if thumb and thumb.startswith('/'):
                    thumb = f"{instance}{thumb}"
                
                return {
                    'stream_url': best_audio.get('url'),
                    'title': data.get('title'),
                    'thumbnail': thumb,
                    'artist': data.get('author'),
                    'duration': data.get('lengthSeconds'),
                    'source': f'Invidious ({instance})'
                }
    except Exception:
        pass
    return None

@app.get("/stream")
async def get_stream(
    id: str = Query(...), 
    title: Optional[str] = Query(None), 
    artist: Optional[str] = Query(None)
):
    """
    Optimized streaming logic with parallel lookups and caching.
    Priority: Invidious (Parallel) -> pytubefix -> SoundCloud (HLS) -> yt-dlp
    """
    # If ID looks like Saavn or title/artist are provided, resolve to YT ID first
    yt_id = id
    is_saavn = len(id) != 11 or (id.isalnum() and not any(c.isupper() for c in id) and not any(c.islower() for c in id)) # Very rough check
    
    # Better Saavn check: Saavn IDs are often different lengths or alphanumeric
    if (len(id) < 11 or len(id) > 12) and title and artist:
        is_saavn = True

    if is_saavn and title and artist:
        logger.info(f"Resolving Saavn track to YouTube: {title} - {artist}")
        try:
            search_query = f"{title} {artist} official audio"
            search_engine = VideosSearch(search_query, limit=1)
            yt_res = search_engine.result().get('result', [])
            if yt_res:
                yt_id = yt_res[0].get('id')
                logger.info(f"Resolved to YT ID: {yt_id}")
        except Exception as e:
            logger.warning(f"Metadata resolution failed: {str(e)}")

    # 1. Try Invidious (Parallel Lookups) with resolved yt_id
    instances = [
        "https://inv.nadeko.net",
        "https://inv.zzls.xyz",
        "https://iv.datura.network",
        "https://invidious.projectsegfau.lt",
        "https://yewtu.be",
        "https://inv.tux.pizza",
        "https://invidious.nerdvpn.de"
    ]
    random.shuffle(instances)
    top_instances = instances[0:4]

    logger.info(f"Racing Invidious parallel lookups for {yt_id}: {top_instances}")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Create tasks for the race with shorter timeout
        tasks = [asyncio.create_task(fetch_invidious_stream(client, inst, yt_id)) for inst in top_instances]
        
        # True Race: Return as soon as ONE completes successfully
        found_res = None
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    res = await task
                    if res and not found_res:
                        found_res = res
                        for p in pending:
                            p.cancel()
                        break
                except Exception as te:
                    logger.warning(f"Race task error: {str(te)}")
                    pass
            if found_res and isinstance(found_res, dict):
                logger.info(f"SUCCESS: {found_res.get('source')} (Race Winner)")
                thumb = found_res.get('thumbnail')
                if thumb and isinstance(thumb, str) and thumb.startswith('http:'):
                    found_res['thumbnail'] = thumb.replace('http:', 'https:')
                return found_res
            tasks = list(pending)
            if not tasks: break

    # 2. Try pytubefix (YouTube)
    logger.info("Falling back to pytubefix")
    try:
        from pytubefix import YouTube
        yt = YouTube(f"https://www.youtube.com/watch?v={yt_id}")
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            logger.info("SUCCESS: pytubefix")
            thumb = yt.thumbnail_url
            if thumb and thumb.startswith('http:'): thumb = thumb.replace('http:', 'https:')
            return {
                'stream_url': audio_stream.url,
                'title': yt.title,
                'thumbnail': thumb,
                'artist': yt.author,
                'duration': yt.length,
                'source': 'pytubefix'
            }
    except Exception as py_e:
        logger.warning(f"pytubefix failed: {str(py_e)}")

    # 3. Fallback: Search same title on SoundCloud
    logger.info("Falling back to SoundCloud")
    try:
        search_query = f"{title} {artist}" if title and artist else title or "song"
        
        if search_query == "song":
            try:
                from youtubesearchpython import Video
                vd = Video.get(f"https://www.youtube.com/watch?v={yt_id}")
                if vd and vd.get('title'):
                    search_query = vd.get('title')
            except:
                pass

        # SoundCloud CID extraction with simple caching
        global SC_CID_CACHE
        cid = SC_CID_CACHE.get("cid")
        if not cid or time.time() > SC_CID_CACHE.get("expiry", 0):
            logger.info("Extracting new SoundCloud Client ID")
            rsc = requests.get('https://soundcloud.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            js_matches = re.findall(r'src=\"(https://a-v2\.sndcdn\.com/assets/[^\"]+\.js)\"', rsc.text)
            for js_url in js_matches:
                rj = requests.get(js_url, timeout=5)
                cid_match = re.search(r'client_id:\"([a-zA-Z0-9]{32})\"', rj.text)
                if cid_match:
                    cid = cid_match.group(1)
                    SC_CID_CACHE = {"cid": cid, "expiry": time.time() + 3600} # Cache for 1 hour
                    break
        
        if cid:
            search_url = f'https://api-v2.soundcloud.com/search/tracks?q={search_query}&client_id={cid}&limit=1'
            rss = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if rss.status_code == 200:
                results = rss.json().get('collection', [])
                if results:
                    track = results[0]
                    transcodings = track.get('media', {}).get('transcodings', [])
                    
                    # FORCE HLS: Progressive streams cut off at 1:45 because of SoundCloud's IP-range blocking
                    best = next((t for t in transcodings if t.get('format', {}).get('protocol') == 'hls'), None)
                    
                    if best:
                        ru = requests.get(best['url'] + f'?client_id={cid}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if ru.status_code == 200:
                            stream_url = ru.json()['url']
                            logger.info(f"SUCCESS: SoundCloud (HLS Forced)")
                            thumb = track.get('artwork_url')
                            if thumb: thumb = thumb.replace('-large', '-t500x500') # Better quality
                            if thumb and thumb.startswith('http:'): thumb = thumb.replace('http:', 'https:')
                            return {
                                'stream_url': stream_url,
                                'title': track.get('title'),
                                'thumbnail': thumb or 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500',
                                'artist': track.get('user', {}).get('username'),
                                'duration': track.get('duration') // 1000,
                                'source': 'SoundCloud'
                            }
                    else:
                        logger.warning("No HLS transcoding found for SoundCloud track. Skipping to next fallback.")
    except Exception as sce:
        logger.warning(f"SoundCloud fallback failed: {str(sce)}")

    # 4. Last resort: yt-dlp
    logger.info("Falling back to yt-dlp")
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"https://www.youtube.com/watch?v={yt_id}", download=False))
            formats = [f for f in info.get('formats', []) if f.get('vcodec') == 'none']
            if formats:
                best_format = sorted(formats, key=lambda x: x.get('abr') or 0, reverse=True)[0]
                logger.info("SUCCESS: yt-dlp")
                thumb = info.get('thumbnail')
                if thumb and thumb.startswith('http:'): thumb = thumb.replace('http:', 'https:')
                return {
                    'stream_url': best_format.get('url'),
                    'title': info.get('title'),
                    'thumbnail': thumb,
                    'artist': info.get('uploader'),
                    'duration': info.get('duration'),
                    'source': 'yt-dlp'
                }
    except Exception as final_e:
        logger.error(f"Critical Failure for ID {yt_id}")
        raise HTTPException(status_code=500, detail="Playback unavailable. Please try another song.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
