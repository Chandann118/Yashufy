
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

async def test_backend():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- Testing /search ---")
        try:
            resp = await client.get(f"{BASE_URL}/search", params={'q': 'Arijit Singh'})
            if resp.status_code == 200:
                data = resp.json()
                print(f"Search Success: Found {len(data)} results")
                if data:
                    item = data[0]
                    print(f"Sample Item: {item.get('title')} - {item.get('thumbnail')}")
            else:
                print(f"Search Failed: {resp.status_code}")
        except Exception as e:
            print(f"Search Error: {str(e)}")

        print("\n--- Testing /stream ---")
        try:
            # Using Gehra Hua as it was in the logs
            resp = await client.get(f"{BASE_URL}/stream", params={
                'id': 'saavn_QQ8jRRlhBEs',
                'title': 'Gehra Hua',
                'artist': 'Arijit Singh',
                'duration_total': '362'
            })
            if resp.status_code == 200:
                data = resp.json()
                print(f"Stream Success: {data.get('source')}")
                print(f"Stream URL: {data.get('stream_url')[:50]}...")
            else:
                print(f"Stream Failed: {resp.status_code}")
        except Exception as e:
            print(f"Stream Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_backend())
