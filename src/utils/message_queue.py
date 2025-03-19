# encoding: utf-8
from queue import Queue

class WrapperQueue():
    def __init__(self, queue_obj:Queue = None):
        self.queue = queue_obj
    def put(self, info):
        if self.queue is not None:
            self.queue.put(info)
    def get(self, block=True):
        ret = None
        if self.queue is not None:
            ret = self.queue.get(block=block)
        return ret
