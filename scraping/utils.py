from bs4 import BeautifulSoup
# import cloudscraper
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_soup_from_url(url, verb="get", data=None, extra_headers=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    if extra_headers:
        headers.update(extra_headers)

    # Try with cloudscraper first, fallback to requests if SSL issues
    # try:
    #     s = cloudscraper.create_scraper()
    #     if verb == 'get':
    #         resp = s.get(url, data=data, headers=headers, verify=False)
    #     elif verb == 'post':
    #         resp = s.post(url, data=data, headers=headers, verify=False)
    # except Exception as e:
    #     print(f"Cloudscraper failed: {e}")
    #     print("Falling back to requests...")
    #     # Fallback to regular requests
    #     if verb == 'get':
    #         resp = requests.get(url, data=data, headers=headers, verify=False)
    #     elif verb == 'post':
    #         resp = requests.post(url, data=data, headers=headers, verify=False)
    
    # Use regular requests directly (cloudscraper commented out)
    if verb == 'get':
        resp = requests.get(url, data=data, headers=headers, verify=False)
    elif verb == 'post':
        resp = requests.post(url, data=data, headers=headers, verify=False)

    return BeautifulSoup(resp.content, "html.parser")