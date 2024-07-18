import glob, json, time, os, random
from pathlib import Path
import requests
import config
from readability import Document
from tqdm import tqdm

def load_cached_urls():
    raise NotImplemented

def query_google():
    def inner(query):
        payload = {'api_key':config.scraperapi_key, 'query':query}
        resp = requests.get('https://api.scraperapi.com/structured/google/search', params=payload)
        return resp.json()
    return inner

def scrape_url_to_cache():
    def inner(url, cache=False):
        """Use scraperAPI to download and save a page plus its readability-formatted version.  If cache, check if the page has been downloaded before"""
        if cache:
            raise NotImplemented
        dir_name = make_uid()
        path = config.web_cache_dir/dir_name
        path.mkdir()
        with open(path/'metadata.json', 'w') as f:
            json.dump({'url':url, 'time':time.time()}, f, indent=2)
        payload = {'api_key': config.scraperapi_key, 'url': url}
        resp = requests.get('https://api.scraperapi.com', params=payload)
        with open(path/'page.html', 'w') as f:
            f.write(resp.text)
        doc = Document(resp.content)
        with open(path/'page.readability.html', 'w') as f:
            f.write(doc.summary())
        return {'type':'cached_page', 'url':url, 'path':str(path)}
    return inner

def get_urls_from_query():
    def inner(query_results):
        urls = []
        for res in query_results['organic_results']:
            urls.append(res['link'])
        return urls
    return inner

#def query_and_scrape_to_cache(query, cache=False, verbose=True):
#    query_results = query_google(query)
#    pages = {}
#    for res in (tqdm(query_results['organic_results']) if verbose else query_results['organic_results']):
#        url = res['link']
#        pages[url] = scrape_url_to_cache(url, cache=cache)
#    return {'query_results':query_results, 'pages':pages}

def make_uid(lr=8, lt=8):
    """Generate a uid as a concatenation of a random string and a partial timestamp, of length lr and lt respectively"""
    rs = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=lr))
    ts = str(int(time.time()*100))[-lt:-1]
    return f'{rs}-{ts}'