import project as proj

project = proj.Project('Test 3')

t1 = project.add_task([], lambda x: 'Hello World')
t2 = project.add_task([], lambda x: 'Lorem Ipsum')
t3 = project.add_task([t1, t2], lambda x: list(set(x)), produce_many=True)
t4 = project.add_task([t3], lambda x: x.lower())
t5 = project.add_task([t4], lambda x: ''.join(sorted(x)), collect_all=True)

if __name__=="__main__":
    project.work()