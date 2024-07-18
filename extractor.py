from scipy.spatial.distance import cosine
from sklearn.cluster import SpectralClustering
import lxml.html
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import copy
import config
import requests
from pathlib import Path
import utils

MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def single_chat(message):
    data = {
        "model": config.llm_model,
        "stream": False,
        "messages": [
            {'role':'user', 'content':message}
        ],
    }
    resp = requests.post(config.llm_url, json=data)
    response = resp.json()
    content = response['message']['content']
    return content

def RAG(query):
    query = query
    def inner(context_docs):
        if type(context_docs)!=list:
            context_docs = [context_docs]
        context = '\n'.join([f"<doc>\n{utils.string_accessor(doc)}\n</doc>\n" for doc in context_docs])
        message = f"""Below is a document between the tags <doc> and </doc>.  Following the document is a user query.  Please answer the user query as concisely as possible, using information only the provided document.
    {context}
    User query: "{query}" """
        return single_chat(message)
    return inner

def cluster_answers(filter_query, texts, n_clusters=2):
    dists = np.zeros((len(texts),1))
    embedding = MODEL.encode(filter_query)
    for i, t in tqdm(enumerate(texts)):
        a_embedding = MODEL.encode(t)
        dists[i,0] = 2-cosine(embedding, a_embedding)
    clusterer = SpectralClustering(n_clusters=n_clusters)
    labels = clusterer.fit_predict(dists)
    cleaned_labels = {}
    for i, l in enumerate(labels):
        cleaned_labels[l] = cleaned_labels.get(l,[])+[i]
    centers = {l:sum([dists[i] for i in cleaned_labels[l]])/len(cleaned_labels[l]) for l in cleaned_labels.keys()}
    return centers, cleaned_labels, dists

def separate_data(target, data):
    """Partition data into items that are close and far to target"""
    centers, labels, _ = cluster_answers(target, data)
    closest_label = max(centers.keys(), key=lambda l:centers[l]) #we're using a similarity matrix so 'closest' is the highest values
    close = [i for i in labels[closest_label]]
    far = [i for i, d in enumerate(data) if i not in labels[closest_label]]
    return close, far

def partition_data(target, keep_near=False):
    target = target
    keep_near = keep_near
    def inner(data):
        near, far = separate_data(target, data)
        if keep_near:
            return [data[i] for i in near]
        else:
            return [data[i] for i in far]
    return inner

def split_page(page_text):
    lines = []
    for line in page_text.split('\n'):
        if line.strip()!="":
            lines.append(line)
    return lines

def RAG_pages(query, negative_answer, pages, split_pages=True, verbose=True, filter_negatives=True):
    results = []
    for url, path in (tqdm(pages.items()) if verbose else pages.items()):
        with open(Path(path)/'page.readability.html', 'r') as f:
            html = lxml.html.fromstring(f.read())
            txt = html.text_content()
            if split_pages:
                for line in (tqdm(split_page(txt), leave=False) if verbose else split_page(txt)):
                    results.append([RAG(query, [line], negative_answer=negative_answer), url])
            else:
                results.append([RAG(query, [txt], negative_answer=negative_answer), url])
    return results

def dedupe(data, verbose=True):
    """Iterativly partition the data, removing "similar" results"""
    clean = []
    remaining = copy.deepcopy(data)
    while len(remaining)>0:
        d = remaining[0]
        remaining = remaining[1:]
        near, far = separate_data(d, remaining+clean)
        clean.append(d)
        remaining = [remaining[i] for i in far if i<len(remaining)]
        print(f'{len(remaining)} remain')
    return clean