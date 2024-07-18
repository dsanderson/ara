from flask import Flask, request, jsonify
import subprocess
import json
import sys
import os
import importlib
import time
import threading
import random
import config
from pathlib import Path

print(f"Loading {sys.argv[1]}")
module_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
project = importlib.import_module(module_name)


app = Flask(__name__)
PROJ = project.project
TO_PROCESS = []
PROCESSING = set()
TASK_STATUS = []
RESULTS = []
CLIENTS = []
PROCESSED = []

def startup():
    """Load the research file from `project` into RESULTS"""
    log = Path(PROJ.log)
    log.touch()
    for task in PROJ.tasks:
        TO_PROCESS.append(set())
        PROCESSED.append(set())
        TASK_STATUS.append('waiting')
    with open(log, 'r') as f:
        for line in f:
            datum = json.loads(line)
            datum_id = datum['id']
            RESULTS.append(datum)
            #special case to deal with zero-dep tasks
            distribute_results(datum)

def distribute_results(datum):
    if len(PROJ.tasks[datum['source_task']]['deps'])==0:
        TASK_STATUS[datum['source_task']] = 'COMPLETE'
    for t in PROJ.tasks:
        if datum['source_task'] in t['deps']:
            TO_PROCESS[t['id']].add(datum['id'])
    for did in datum['source_data']:
        TO_PROCESS[datum['source_task']].discard(did)
        PROCESSED[datum['source_task']].add(did)
    # Update relevant task statuses
    for t in PROJ.tasks:
        if TASK_STATUS[t['id']]=='COMPLETE':
            continue
        if all(TASK_STATUS[d]=='COMPLETE' for d in t['deps']):
            TASK_STATUS[t['id']]='CLEAR'
        if TASK_STATUS[t['id']]=='CLEAR' and len(TO_PROCESS[t['id']])==0:
            TASK_STATUS[t['id']]='COMPLETE'

def make_job_id(task, data_ids):
    dids = sorted(data_ids)
    return tuple([task['id']]+dids)

def launch_client():
    pyexec = sys.executable
    script = sys.argv[1]
    env_vars = {"OMP_NUM_THREADS":"1"}
    CLIENTS.append(subprocess.Popen([pyexec, script], env=env_vars))

@app.route('/job')
def give_job():
    # First, run zero-dep jobs
    #print(TASK_STATUS, TO_PROCESS, PROCESSING)
    zerodep = [t for t in PROJ.tasks if (len(t['deps'])==0 and TASK_STATUS[t['id']]!='COMPLETE')]
    for z in zerodep:
        jid = make_job_id(z, [])
        if jid not in PROCESSING:
            PROCESSING.add(jid)
            datum = {'source_task':z['id'], 'source_data':[], 'input':None}
            return jsonify(datum)
    # Second, prefer *BIG BATCH ENERGY*
    collectable = [t for t in PROJ.tasks if (t['collect_all'] and TASK_STATUS[t['id']]=='CLEAR')]
    for c in reversed(collectable): #Reversed causes us to go depth-first, easier for inspection
        jid = make_job_id(c, TO_PROCESS[c['id']])
        if jid not in PROCESSING:
            PROCESSING.add(jid)
            datum = {'source_task':c['id'], 'source_data':sorted(TO_PROCESS[c['id']]), 'input':[RESULTS[d]['output'] for d in TO_PROCESS[c['id']]]}
            return jsonify(datum)
    processable = [t for t in PROJ.tasks if (not t['collect_all'] and len(TO_PROCESS[t['id']])>0)]
    for p in reversed(processable):
        for datum_id in TO_PROCESS[p['id']]:
            jid = make_job_id(p, [datum_id])
            if jid not in PROCESSING:
                PROCESSING.add(jid)
                datum = {'source_task':p['id'], 'source_data':[datum_id], 'input':RESULTS[datum_id]['output']}
                return jsonify(datum)
    return ('',204)

lock = threading.Lock()
@app.route('/result', methods=['PUT'])
def add_result():
    #print(TASK_STATUS, TO_PROCESS, PROCESSING)
    datum = request.get_json()
    with lock:
        datum_id = len(RESULTS)
        datum['id'] = datum_id
        datum['time'] = time.time()
        RESULTS.append(datum)
        with open(PROJ.log, 'a') as f:
            f.write(f"{json.dumps(datum)}\n")
            f.flush()
        if 'error' not in datum:
            distribute_results(datum)
    job_id = make_job_id(PROJ.tasks[datum['source_task']], datum['source_data'])
    PROCESSING.discard(job_id)
    #print(TASK_STATUS, TO_PROCESS, PROCESSING)
    return ('',204)

@app.route('/status/datum/<int:datum_id>')
def get_datum_status(datum_id):
    status = f"""<p>{RESULTS[datum_id]}</p>\n"""
    #status = status+f"<p><a href={'/status/datum/'+r}>{r}</a>: {RESULTS[r]['output']}</p>\n"
    links = [('<a href=/status/datum/'+str(d)+'>'+str(d)+'</a>') for d in RESULTS[datum_id]['source_data']]
    status = status+f"<p>From {' '.join(links)}</p>\n"
    return status

@app.route('/status/task/<int:task_id>')
def get_task_status(task_id):
    status = f"""<h1>{task_id}: {TASK_STATUS[task_id]}</h1>\n<p>{len(PROCESSED[task_id])} Results</p>\n<p>{len(TO_PROCESS[task_id])} to Process</p>\n"""
    for r in RESULTS:
        if task_id == r['source_task']:
            status = status+f"<p><a href={'/status/datum/'+str(r['id'])}>{r['id']}</a>: {r['output']}</p>\n"
            links = [('<a href=/status/datum/'+str(d)+'>'+str(d)+'</a>') for d in r['source_data']]
            status = status+f"<p>From {' '.join(links)}</p>\n"
    return status

@app.route('/status')
def get_status():
    status = f"""<h1>{PROJ.name} {sys.argv[1]}, {PROJ.log}</h1>\n<p>{len(RESULTS)} Results</p>\n<p>{len(PROCESSING)} In Processing</p>\n"""
    for t in PROJ.tasks:
        status = status+f"<p><a href={'/status/task/'+str(t['id'])}>{t['id']}</a>: {TASK_STATUS[t['id']]}, {len(PROCESSED[t['id']])}/{len(PROCESSED[t['id']])+len(TO_PROCESS[t['id']])}</p>\n"
    #status = {}
    #status['tasks'] = {t['id']: [TASK_STATUS[t['id']], len(TO_PROCESS[t['id']])] for t in PROJ.tasks}
    #status['processing'] = len(PROCESSING)
    #status['results'] = len(RESULTS)
    #print(status)
    #return jsonify(status)
    return status

if __name__=='__main__':
    if sys.argv[-1]=='RESTART':
        print('CLEARING RESEARCH LOG')
        with open(PROJ.log, 'w') as f:
            pass
    startup()
    n_clients = int(sys.argv[2])
    while len(CLIENTS)<n_clients:
        launch_client()
    app.run(debug=True, port=config.port, host=config.host)