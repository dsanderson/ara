import json
from pathlib import Path
import config
import requests
import time

class Project:
    def __init__(self, name, log=None):
        self.name = name
        if log==None:
            self.log = f"{name.replace(' ','_')}.jl"
        else:
            self.log = log
        self.log = Path(self.log)
        self.log.touch()
        self.tasks = []
        #self.host = 'http://'+config.host
        #self.port = config.port
        self.url = f"http://{config.host}:{config.port}"
    
    def add_task(self, dependencies, task, collect_all=False, produce_many=False, options = {}):
        task_id = len(self.tasks)
        self.tasks.append({'id':task_id, 'deps':dependencies, 'task':task, 'collect_all':collect_all, 'options':options, 'produce_many':produce_many})
        return task_id

    def run(self, task_id, inp):
        return self.tasks[task_id]['task'](inp, **self.tasks[task_id]['options'])

    def get_job(self):
        while True:
            try:
                req = requests.get(self.url+'/job')
            except Exception as e:
                print(e)
                time.sleep(1)
                continue
            if req.status_code==200:
                return req.json()
            print('Waiting for job')
            time.sleep(1)

    def send_result(self, inp, result, produce_many, error):
        if not produce_many:
            result = [result]
        for res in result:
            datum = {'source_task':inp['source_task'], 'source_data':inp['source_data'], 'output':res}
            if error:
                datum['error'] = error
            print('Sending result')
            requests.put(self.url+'/result', json=datum)

    def work(self):
        while True:
            inp = self.get_job()
            error = False
            try:
                res = self.run(inp['source_task'], inp['input'])
            except Exception as e:
                res = {}
                error = str(e)
                time.sleep(1)
            self.send_result(inp, res, self.tasks[inp['source_task']]['produce_many'], error)
