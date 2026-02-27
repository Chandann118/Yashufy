
import httpx
import asyncio
import json

BASE_URL = "https://www.jiosaavn.com/api.php"

async def test_saavn():
    params = {
        '__call': 'content.getCharts',
        '_format': 'json',
        '_marker': '0',
        'cc': 'in',
    }
    async with httpx.AsyncClient() as client:
        print("Testing JioSaavn search...")
        resp = await client.get(BASE_URL, params={
            '__call': 'autocomplete.get',
            '_format': 'json',
            '_marker': '0',
            'cc': 'in',
            'includeMetaTags': '1',
            'query': 'Arijit Singh'
        }, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            songs = data.get('songs', {}).get('data', [])
            print(f"Found {len(songs)} songs")
            if songs:
                song = songs[0]
                print(f"Song Sample: {json.dumps(song, indent=2)}")
        
        print("\nTesting JioSaavn charts...")
        resp = await client.get(BASE_URL, params=params, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {len(data)} charts")
            if data:
                chart = data[0]
                print(f"Chart ID: {chart.get('id')}")
                listid = chart.get('id')
                resp_pl = await client.get(BASE_URL, params={
                    '__call': 'playlist.getDetails',
                    '_format': 'json',
                    'listid': listid
                }, timeout=10.0)
                if resp_pl.status_code == 200:
                    pl_data = resp_pl.json()
                    songs = pl_data.get('songs', [])
                    print(f"Found {len(songs)} songs in chart")
                    if songs:
                        print(f"Chart Song Sample: {json.dumps(songs[0], indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_saavn())
