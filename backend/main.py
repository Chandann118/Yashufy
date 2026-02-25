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
    return {"status": "healthy", "ver": "v1.0.6-sc-fallback"}

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
async def get_stream(id: str = Query(...)):
    # 1. Try pytubefix first (YouTube)
    try:
        from pytubefix import YouTube
        yt = YouTube(f"https://www.youtube.com/watch?v={id}")
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            return {
                'stream_url': audio_stream.url,
                'title': yt.title,
                'thumbnail': yt.thumbnail_url,
                'artist': yt.author,
                'duration': yt.length,
                'source': 'pytubefix'
            }
    except Exception as e:
        print(f"pytubefix for {id} failed: {str(e)}. Trying SoundCloud fallback...")

    # 2. Fallback: Search same title on SoundCloud
    try:
        import requests, re
        # Get title from youtube-search-python if pytubefix failed to get it
        title = "song"
        try:
            from youtubesearchpython import Video
            vd = Video.get(f"https://www.youtube.com/watch?v={id}")
            title = vd.get('title')
        except:
            pass

        # Scrape SoundCloud client_id
        rsc = requests.get('https://soundcloud.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        match = re.search(r'src=\"(https://a-v2\.sndcdn\.com/assets/[^\"]+\.js)\"', rsc.text)
        if match:
            js_url = match.group(1)
            rj = requests.get(js_url, timeout=5)
            cid_match = re.search(r'client_id:\"([a-zA-Z0-9]{32})\"', rj.text)
            if cid_match:
                cid = cid_match.group(1)
                # Search on SC
                search_url = f'https://api-v2.soundcloud.com/search/tracks?q={title}&client_id={cid}&limit=1'
                rss = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if rss.status_code == 200:
                    track = rss.json()['collection'][0]
                    transcodings = track.get('media', {}).get('transcodings', [])
                    # Prefer progressive mp3
                    best = next((t for t in transcodings if t['format']['protocol'] == 'progressive'), transcodings[0] if transcodings else None)
                    if best:
                        ru = requests.get(best['url'] + f'?client_id={cid}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if ru.status_code == 200:
                            return {
                                'stream_url': ru.json()['url'],
                                'title': track.get('title'),
                                'thumbnail': track.get('artwork_url'),
                                'artist': track.get('user', {}).get('username'),
                                'duration': track.get('duration') // 1000,
                                'source': 'SoundCloud (Fallback)'
                            }
    except Exception as sce:
        print(f"SoundCloud fallback failed: {str(sce)}")

    # 3. Last resort: yt-dlp
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"https://www.youtube.com/watch?v={id}", download=False))
            best_format = sorted([f for f in info.get('formats', []) if f.get('vcodec') == 'none'], key=lambda x: x.get('abr') or 0, reverse=True)[0]
            return {
                'stream_url': best_format.get('url'),
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'artist': info.get('uploader'),
                'duration': info.get('duration'),
                'source': 'yt-dlp'
            }
    except Exception as final_e:
        raise HTTPException(status_code=500, detail=f"All sources blocked. SoundCloud Error: {str(sce) if 'sce' in locals() else 'Unknown'}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
