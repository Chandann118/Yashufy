from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import asyncio
from typing import List, Optional

app = FastAPI(title="Vortex Music Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

YDLE_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

@app.get("/search")
async def search(q: str = Query(...)):
    ydl_opts = {
        **YDLE_OPTIONS,
        'default_search': 'ytsearch10',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch10:{q}", download=False))
            
            results = []
            for entry in info.get('entries', []):
                if not entry: continue
                results.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'thumbnail': entry.get('thumbnail'),
                    'artist': entry.get('uploader'),
                    'duration': entry.get('duration'),
                    'url': entry.get('webpage_url'),
                })
            return results
    except Exception as e:
        print(f"Search Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/trending")
async def trending():
    ydl_opts = {
        **YDLE_OPTIONS,
        'default_search': 'ytsearch10',
    }
    try:
        # Fetch trending music
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info("ytsearch10:trending music hits", download=False))
            
            results = []
            for entry in info.get('entries', []):
                if not entry: continue
                results.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'thumbnail': entry.get('thumbnail'),
                    'artist': entry.get('uploader'),
                    'duration': entry.get('duration'),
                })
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/home")
async def home_content():
    try:
        trending_songs = await trending()
        return {
            "trending": trending_songs,
            "recently_played": trending_songs[:4] 
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream")
async def get_stream(id: str = Query(...)):
    ydl_opts = {
        **YDLE_OPTIONS,
        'format': 'bestaudio/best',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"https://www.youtube.com/watch?v={id}", download=False))
            
            # Find the best audio stream
            formats = info.get('formats', [])
            audio_formats = [f for f in formats if f.get('vcodec') == 'none']
            if not audio_formats:
                audio_formats = formats # Fallback
            
            best_format = sorted(audio_formats, key=lambda x: x.get('abr') or 0, reverse=True)[0]
            
            return {
                'stream_url': best_format.get('url'),
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'artist': info.get('uploader'),
                'duration': info.get('duration'),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
