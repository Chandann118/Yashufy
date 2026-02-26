
import httpx
import asyncio
import re
import requests

async def test_invidious(video_id):
    instances = ["https://iv.ggtyler.dev", "https://invidious.projectsegfau.lt", "https://inv.zzls.xyz", "https://yewtu.be"]
    for instance in instances:
        print(f"Testing Invidious: {instance}")
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{instance}/api/v1/videos/{video_id}")
                print(f"  Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    adaptive_formats = data.get('adaptiveFormats', [])
                    audio_formats = [f for f in adaptive_formats if f.get('type','').startswith('audio/')]
                    if audio_formats:
                        print(f"  SUCCESS: Found {len(audio_formats)} audio formats")
                        return True
                    else:
                        print(f"  FAIL: No audio formats found")
                else:
                    print(f"  FAIL: Status {resp.status_code}")
        except Exception as e:
            print(f"  ERROR: {str(e)}")
    return False

def test_soundcloud(title):
    print(f"Testing SoundCloud for title: {title}")
    try:
        rsc = requests.get('https://soundcloud.com', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}, timeout=10)
        print(f"  Home page status: {rsc.status_code}")
        # Search for multiple JS files because the CID might be in any of them
        js_urls = re.findall(r'src=\"(https://a-v2\.sndcdn\.com/assets/[^\"]+\.js)\"', rsc.text)
        print(f"  Found {len(js_urls)} JS assets")
        
        for js_url in js_urls:
            print(f"  Checking JS: {js_url}")
            rj = requests.get(js_url, timeout=10)
            cid_match = re.search(r'client_id:\"([a-zA-Z0-9]{32})\"', rj.text)
            if cid_match:
                cid = cid_match.group(1)
                print(f"  Found Client ID: {cid}")
                search_url = f'https://api-v2.soundcloud.com/search/tracks?q={title}&client_id={cid}&limit=1'
                rss = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                print(f"  Search status: {rss.status_code}")
                if rss.status_code == 200:
                    results = rss.json().get('collection', [])
                    if results:
                        print(f"  SUCCESS: Found track on SoundCloud")
                        return True
                    else:
                        print(f"  FAIL: No results for '{title}'")
                break
    except Exception as e:
        print(f"  ERROR: {str(e)}")
    return False

async def main():
    video_id = "fTKqtvXjkvo" # Some song
    print("--- Testing Invidious Fallbacks ---")
    await test_invidious(video_id)
    
    print("\n--- Testing SoundCloud Fallback ---")
    test_soundcloud("Shape of You")

if __name__ == "__main__":
    asyncio.run(main())
