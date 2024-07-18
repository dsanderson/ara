from pathlib import Path
import scraperapi

llm_url = 'http://localhost:11434/api/chat'
llm_model = 'gemma2:27b' #'phi3:medium' #'gemma2:9b'
web_cache_dir = Path('/data/exocortex/web')
scraperapi_key = scraperapi.key
host = '0.0.0.0'
port = '8888'
