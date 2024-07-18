import config
from pathlib import Path

def string_accessor(data):
    if type(data)==str:
        return data
    elif type(data)==dict and data.get('type','')=='cached_page':
        with open(Path(data['path'])/'page.readability.html', 'r') as f:
            text = f.read()
        return text
    return str(data)

def split_text(tokens, clean=True):
    tokens = tokens
    def inner(text):
        text = text.split(tokens[0])
        for t in tokens[1:]:
            text = (t.join(text)).split(t)
        if clean:
            text = [t.strip() for t in text]
        return text
    return inner            

def template_text(template):
    template = template
    def inner(text):
        return template.format(text)
    return inner

def echo(text):
    text = text
    def inner(arg):
        return text
    return inner

def dedupe():
    def inner(data):
        return list(set(data))
    return inner