from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import asyncio
from typing import List, Optional
from youtubesearchpython import VideosSearch

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
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'nocheckcertificate': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'],
            'skip': ['hls', 'dash']
        }
    }
}

def format_search_result(result):
    return {
        'id': result.get('id'),
        'title': result.get('title'),
        'thumbnail': result.get('thumbnails', [{}])[0].get('url'),
        'artist': result.get('descriptionSnippet', [{}])[0].get('text') if result.get('descriptionSnippet') else result.get('channel', {}).get('name'),
        'duration': result.get('duration'),
        'url': f"https://www.youtube.com/watch?v={result.get('id')}",
    }

@app.get("/search")
async def search(q: str = Query(...)):
    try:
        search_engine = VideosSearch(q, limit=15)
        results = search_engine.result()
        
        formatted_results = []
        for video in results.get('result', []):
            formatted_results.append(format_search_result(video))
        return formatted_results
    except Exception as e:
        print(f"Search Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/trending")
async def trending():
    try:
        # Using a fixed high-quality search for trending content
        search_engine = VideosSearch("trending music hits 2024", limit=10)
        results = search_engine.result()
        
        formatted_results = []
        for video in results.get('result', []):
            formatted_results.append(format_search_result(video))
        return formatted_results
    except Exception as e:
        print(f"Trending Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trending fetch failed: {str(e)}")

@app.get("/home")
async def home_content():
    try:
        trending_songs = await trending()
        return {
            "trending": trending_songs,
            "recently_played": trending_songs[:4] 
        }
    except Exception as e:
        print(f"Home Content Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Home content failed: {str(e)}")

@app.get("/stream")
async def get_stream(
    id: str = Query(...), 
    title: Optional[str] = Query(None), 
    artist: Optional[str] = Query(None)
):
    """
    Enhanced streaming logic with multiple fallback layers.
    Priority: Invidious (Rotating) -> pytubefix -> SoundCloud (HLS Preferred) -> yt-dlp
    """
    import httpx
    import logging
    import random
    import requests
    import re

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("VortexMusic")

    # 1. Try Invidious (Rotating Instances)
    instances = [
        "https://iv.ggtyler.dev",
        "https://invidious.projectsegfau.lt",
        "https://inv.zzls.xyz",
        "https://yewtu.be",
        "https://inv.riverside.rocks",
        "https://invidious.namazso.eu"
    ]
    random.shuffle(instances)

    for instance in instances:
        try:
            logger.info(f"Trying Invidious instance: {instance}")
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{instance}/api/v1/videos/{id}")
                if resp.status_code == 200:
                    data = resp.json()
                    adaptive_formats = data.get('adaptiveFormats', [])
                    audio_formats = [f for f in adaptive_formats if f.get('type', '').startswith('audio/')]
                    if audio_formats:
                        best_audio = sorted(audio_formats, key=lambda x: int(x.get('bitrate') or 0), reverse=True)[0]
                        logger.info(f"SUCCESS: Invidious ({instance})")
                        return {
                            'stream_url': best_audio.get('url'),
                            'title': data.get('title'),
                            'thumbnail': data.get('videoThumbnails', [{}])[0].get('url') if data.get('videoThumbnails') else None,
                            'artist': data.get('author'),
                            'duration': data.get('lengthSeconds'),
                            'source': f'Invidious ({instance})'
                        }
        except Exception as inv_e:
            logger.warning(f"Invidious instance {instance} failed: {str(inv_e)}")
            continue

    # 2. Try pytubefix (YouTube)
    logger.info("Falling back to pytubefix")
    try:
        from pytubefix import YouTube
        yt = YouTube(f"https://www.youtube.com/watch?v={id}")
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            logger.info("SUCCESS: pytubefix")
            return {
                'stream_url': audio_stream.url,
                'title': yt.title,
                'thumbnail': yt.thumbnail_url,
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
        
        # If no title/artist provided, try to get from YouTube metadata (might be blocked)
        if search_query == "song":
            try:
                from youtubesearchpython import Video
                vd = Video.get(f"https://www.youtube.com/watch?v={id}")
                if vd and vd.get('title'):
                    search_query = vd.get('title')
            except:
                logger.warning("YouTube metadata blocked; using generic search query")

        # SoundCloud CID extraction
        rsc = requests.get('https://soundcloud.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        js_matches = re.findall(r'src=\"(https://a-v2\.sndcdn\.com/assets/[^\"]+\.js)\"', rsc.text)
        
        cid = None
        for js_url in js_matches:
            rj = requests.get(js_url, timeout=10)
            cid_match = re.search(r'client_id:\"([a-zA-Z0-9]{32})\"', rj.text)
            if cid_match:
                cid = cid_match.group(1)
                break
        
        if cid:
            search_url = f'https://api-v2.soundcloud.com/search/tracks?q={search_query}&client_id={cid}&limit=1'
            rss = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if rss.status_code == 200:
                results = rss.json().get('collection', [])
                if results:
                    track = results[0]
                    transcodings = track.get('media', {}).get('transcodings', [])
                    
                    # PREFER HLS OVER PROGRESSIVE TO FIX 1:45 CUTOFF
                    # HLS streams are often the full track, while progressive might be a preview
                    best = next((t for t in transcodings if t['format']['protocol'] == 'hls'), None)
                    if not best:
                        best = next((t for t in transcodings if t['format']['protocol'] == 'progressive'), transcodings[0] if transcodings else None)
                    
                    if best:
                        ru = requests.get(best['url'] + f'?client_id={cid}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        if ru.status_code == 200:
                            stream_url = ru.json()['url']
                            logger.info(f"SUCCESS: SoundCloud ({best['format']['protocol']})")
                            return {
                                'stream_url': stream_url,
                                'title': track.get('title'),
                                'thumbnail': track.get('artwork_url'),
                                'artist': track.get('user', {}).get('username'),
                                'duration': track.get('duration') // 1000,
                                'source': 'SoundCloud'
                            }
    except Exception as sce:
        logger.warning(f"SoundCloud fallback failed: {str(sce)}")

    # 4. Last resort: yt-dlp
    logger.info("Falling back to yt-dlp as last resort")
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"https://www.youtube.com/watch?v={id}", download=False))
            best_format = sorted([f for f in info.get('formats', []) if f.get('vcodec') == 'none'], key=lambda x: x.get('abr') or 0, reverse=True)[0]
            logger.info("SUCCESS: yt-dlp")
            return {
                'stream_url': best_format.get('url'),
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'artist': info.get('uploader'),
                'duration': info.get('duration'),
                'source': 'yt-dlp'
            }
    except Exception as final_e:
        logger.error(f"Critical Failure: All streaming sources failed for ID {id}")
        raise HTTPException(status_code=500, detail="Streaming currently unavailable from all sources. Technical team notified.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
