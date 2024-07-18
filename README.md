```
   ###    ########     ###    
  ## ##   ##     ##   ## ##   
 ##   ##  ##     ##  ##   ##  
##     ## ########  ##     ## 
######### ##   ##   ######### 
##     ## ##    ##  ##     ## 
##     ## ##     ## ##     ## 

 Autonomous Research Agents
```

I find a *lot* of my "research" falls into, essentially, serial googling:  Google a topic, skim the results looking for some key words/phrases/info, then google those key words, and iterate.  Some examples:
- Finding potential business contacts for my startup: Google "largest manufacturers", look at the results to pull out their names, then google "Startup partnerships at {name}", then look for people named in the results, then Google those people, etc.
- Finding events: Google "robotics events in boston", scrape down the pages, pull out the event names, google for the web page, the summarize each event

ARA is a tool to automate that!  The short version is you define a project as a directed acyclic graph of functions to be run.  We have utility functions for googling, web scraping and performing RAG with an LLM.  You then launch the `manager`, will run multiple workers in parallel to execute the tasks as they become available.  The `manager` provides automatic caching, restart/resume, error handling and exposes an interface to view the current progress and results for each task.

## Installation

I recommend using a virtual env, then `pip install -r requirements.txt` to install the python packages.

Google and web scraping depends on scraperAPI.  Get a key, then create a file `scraperapi.py` which contains `key = <your api key>`.

RAG depends on Ollama and your model of choice.  Follow their instructions to install ollama, and make sure the ollama server is running.

## Defining a Project

A project is defined by instantiating an instance of the `Project` class (defined in `project.py`), then adding tasks to the class with the `add_task` member function.  Here is a short real-world example:
```python
import project as proj

project = proj.Project('External Innovation RAG')

t1 = project.add_task([], utils.echo('What are the largest manufacturing or engineering firms in the US?'))
t2 = project.add_task([t1], collector.query_google())
t3 = project.add_task([t2], collector.get_urls_from_query(), produce_many=True)
t4 = project.add_task([t3], collector.scrape_url_to_cache())
t5 = project.add_task([t4], extractor.RAG('Please provide a list of every company named in the document, with a semicolon (;) between each company.  If no companies are named, answer "none".  Be as concise as possible.'))
t6 = project.add_task([t5], extractor.partition_data("none"), collect_all=True, produce_many=True)
t7 = project.add_task([t6], utils.split_text(';', clean=True), produce_many=True)

if __name__=="__main__":
    project.work()
```

The `if __name__` block is needed, because we call the definition file as a script to execute tasks.

## Adding a task

The `add_task` function is the key to building a project.  It has 2 required arguments: a list of tasks it depends on, and the (single-argument) function to be run.  There are two keyword arguments, which modify how inputs & outputs are handled.  By default, a task is expected to take a single input from a task it depends on, and return a single result.  A task with `collect_all = True`. will wait for all the tasks it depends on to complete, then pass *all* those results into the task function as a single big array.  A task with `produce_many = True` is expexted to return an array.  Rather than sending back the entire array as a single output, each element in the array will be sent back as a separate output.

We use JSON to pass inputs and outputs between workers and to serialize results to disc, so the task output **MUST BE JSON SERIALIZABLE**

## Launching the manager

You can launch the manager with `python3 manager.py <project file> <number of workers>`.  The default port is 8888, set in `config.py`.  This will start the server, load in the previous state (if resuming) or create the log file `<project name with underscores>.jl`, then launch the requested number of workers.  The number of workers will depend on the resources available on your machine, and the complexity of the tasks and models running.  I usually use 2.  If you want to start a project fresh, rather than resume, you can delete/rename the existing log.

## Monitoring the project

The `manager` defaults to port `8888`, set in `config.py`.  Go to `localhost:<port>/status` to view the current status and I/O counts of every task.  You can click on a task ID to see the outputs of that task.  Each output also shows the source datum(s), so you can click back through the chain of data that led to that output.

## Prebuilt Task Functions

I've written some common functions to make it easier to develop projects.  However, you can easily write your own functions as well!'

### utils.py: utility task functions, mostly around string manupulation

- `utils.echo(<str>)`: output the given string.  Used to initialize a project, say by passing in a query to google or url to scrape.
- `utils.template_text(<template>)`: using the built-in `format` function, insert task inputs into `<template>`.  Useful for programmatically constructing google queries from prior results.
- `utils.split_text([<split tokens>])`: Return an array of strings, separating the task input at each `<split token>`.  Useful when using an LLM to extract data: the LLM can provide a list of items, then you split the list with this function.
- `utils.dedupe([<items>])`: Convert items into a set then a list to remove duplicate items. 

### collector.py: task functions for web scraping and googling

- `collector.query_google()`: search google with the task input as the query.  We use scraperapi, the keys must be configured in `scraperapi.py`.  Reutrns the scraperapi query results.
- `collector.get_urls_from_query()`: Takes in a `scraperapi` google query result, and return an array of the URLs of the returned web pages.
- `collector.scrape_url_to_cache()`: Takes in a url, and scrapes the page using scraperapi.  It creates a random UUID, and saves the result to `<uuid>/page.html`, and runs readability and saves the result to `<uuid>/page.readability.html`.  The directory for the cache is set in `config.py`.  Its output is a dictionary, `{url: directory}`.  This is... not a great system.  We don't actually check for duplicate pages, and we masically have to have special logic in functions to load pages from the cache.

### extractor.py: task functions for RAG and getting data from pages

- `extractor.RAG(<query>)`: Takes one or more chunks of text or cached pages as input, and uses an LLM (configured in config.py) to query the document(s).  Assumes Ollama is configured and running.
- `extractor.partition_data(<target>, keep_near=False)`: Takes several chunks of text, and returns the ones similar to the target string (or dissimilar, if `keep_near=False`).  A common pattern in RAG is to have the LLM reply with a set answer, such as "none", if the question cannot be answered.  This function lets you fuzzily match that set answer and discard the matches in the project.