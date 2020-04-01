# -*- coding: utf-8 -*-


class Queue(object):

    def __init__(self, name, dispatcher, exclusive=False):
        self.name = name
        self.exclusive = exclusive
        self.dispatcher = dispatcher

    def add_consumer(self, consumer):
        return self.dispatcher.register(consumer)
