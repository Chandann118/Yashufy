
import urllib.parse

def proxy_thumbnail(url: str) -> str:
    if not url or not url.startswith('http'):
        return 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500'
    
    # Extract the part after protocol for weserv
    clean_url = url.split('?')[0] if 'ytimg.com' in url else url
    url_no_proto = clean_url.replace('https://', '').replace('http://', '')
    encoded_url = urllib.parse.quote(url_no_proto, safe='')
    return f"https://images.weserv.nl/?url={encoded_url}&w=500&h=500&fit=cover"

# Test cases
test_urls = [
    "https://c.saavncdn.com/123/Song-Title-Hindi-2024-500x500.jpg",
    "https://i.ytimg.com/vi/60ItHLz5WEA/hqdefault.jpg?sqp=-oaymwEjCOADEIA4SFryq4qpAxUIARUAAAAAGAElAADIQj0AgKJDeAE=&rs=AOn4CLB-...",
    "http://example.com/image with spaces.jpg"
]

print("--- Testing Thumbnail Proxy Logic ---")
for url in test_urls:
    proxied = proxy_thumbnail(url)
    print(f"Original: {url[:50]}...")
    print(f"Proxied:  {proxied}")
    print("-" * 20)
