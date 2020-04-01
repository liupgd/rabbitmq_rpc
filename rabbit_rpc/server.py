# -*- coding: utf-8 -*-
import logging

from .base import Connector
from .consumer import MessageDispatcher,Consumer
from .queue import Queue

logger = logging.getLogger(__name__)

class RPCServer(Connector):

    def __init__(self,queue_name = None, consumers = None, *args, **kwargs):
        self._queues = {}
        if consumers is None:
            self._consumers = []
        else:
            self._consumers = consumers
        self.default_queue = queue_name or self.DEFUALT_QUEUE

        super(RPCServer, self).__init__(*args, **kwargs)

    def consumer(self, name=None, queue=None, exclusive=False):
        def decorator(func):
            cname = name or func.__name__
            c = Consumer(cname, queue, exclusive)
            c.consume = func
            self._consumers.append(c)
            return func
        return decorator

    def on_exchange_declareok(self, unused_frame):
        self.setup_queues()

    def _setup_queue(self, queue_name):
        dispatcher = MessageDispatcher(self._channel, self._exchange, threaded=self._threaded)
        queue = Queue(queue_name, dispatcher)
        self._queues[queue_name] = queue
        return queue

    def setup_default_queue(self):
        return self._setup_queue(self.default_queue)

    def setup_queues(self):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command.

        :param str|unicode queue_name: The name of the queue to declare.
        """
        default_queue = self.setup_default_queue()

        for c in self._consumers:
            if c.queue is None:
                queue = default_queue
            else:
                try:
                    queue = self._queues[c.queue]
                    if queue.exclusive or c.exclusive:
                        raise ValueError(
                            'Consumer %s is set exclusive with queue %s, but there '
                            'are other consumers already exist.' % (c.name,
                                                                    queue.name))
                except KeyError:
                    queue = self._setup_queue(c.queue)

            queue.add_consumer(c)

        # setup the queue on RabbitMQ
        for queue_name in self._queues.keys():
            self._channel.queue_declare(queue_name,  auto_delete=True, durable=True)
            self._channel.queue_bind(queue_name, exchange=self._exchange)

        self.start_consuming()

    def start_consuming(self):
        if self._threaded:
            self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        else:
            pass
        for queue in self._queues.values():
            consumer_tag = self._channel.basic_consume(queue.name, queue.dispatcher)#, auto_ack=True)
            queue.dispatcher.consumer_tag = consumer_tag

        logger.info(self._queues)
        logger.info('Start consuming..')

        if not self._threaded:
            self._channel.start_consuming()

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        logger.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        self.close_channel()

    def run(self):
        """Run by connecting and then starting the IOLoop."""

        # make sure one processor one connection
        if self._threaded:
            with self._lock:
                self._connection = self.connect()
            self._connection.ioloop.start()
        else:
            self._connection = self.connect()
            self._channel = self._connection.channel()
            self._channel.exchange_declare(self._exchange, exchange_type='direct', auto_delete=True, durable=True)
            self.on_exchange_declareok(None)

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.

        """
        self._closing = True
        self.close_channel()
        self.close_connection()
