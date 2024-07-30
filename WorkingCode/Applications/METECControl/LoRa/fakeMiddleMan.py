from queue import Queue

packageQ = Queue(maxsize=0)
dataQ = Queue(maxsize=0)

def fakeSend():
    data = packageQ.get()
    dataQ.put(data)
