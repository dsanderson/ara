import project as proj
import time

def slow(func):
    def inner(arg):
        time.sleep(3)
        return func(arg)
    return inner


project = proj.Project('Test 2')

t1 = project.add_task([], slow(lambda x: 'Hello World'))
t2 = project.add_task([t1], slow(lambda x: list(set(x))), produce_many=True)
t3 = project.add_task([t2], slow(lambda x: x.lower()))
t4 = project.add_task([t3], slow(lambda x: ''.join(sorted(x))), collect_all=True)

if __name__=="__main__":
    project.work()