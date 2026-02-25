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
    return {"status": "healthy", "ver": "v1.0.5-pytubefix"}

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
    import httpx
    # 1. Try a list of robust Invidious instances first
    instances = [
        "https://invidious.projectsegfau.lt",
        "https://inv.zzls.xyz",
        "https://invidious.snopyta.org",
        "https://yewtu.be",
        "https://invidious.nerdvpn.de",
        "https://inv.riverside.rocks"
    ]
    
    invidious_errors = []
    for instance in instances:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{instance}/api/v1/videos/{id}")
                if resp.status_code == 200:
                    data = resp.json()
                    adaptive_formats = data.get('adaptiveFormats', [])
                    audio_formats = [f for f in adaptive_formats if f.get('type','').startswith('audio/')]
                    if audio_formats:
                        best_audio = sorted(audio_formats, key=lambda x: int(x.get('bitrate') or 0), reverse=True)[0]
                        return {
                            'stream_url': best_audio.get('url'),
                            'title': data.get('title'),
                            'thumbnail': data.get('videoThumbnails', [{}])[0].get('url') if data.get('videoThumbnails') else None,
                            'artist': data.get('author'),
                            'duration': data.get('lengthSeconds'),
                            'source': f'Invidious ({instance})'
                        }
        except:
            continue

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
        raise HTTPException(status_code=500, detail=f"All sources failed: {str(final_e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
