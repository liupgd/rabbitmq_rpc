# -*- coding: utf-8 -*-
import logging
import pickle
import json

import pika
from concurrent.futures import ThreadPoolExecutor
from six import python_2_unicode_compatible

from .threadtool import ThreadAtomLock

from .exceptions import ERROR_FLAG, HAS_ERROR, NO_ERROR
from functools import partial
logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Consumer(object):

    def __init__(self, name, queue=None, exclusive=False):
        self.name = name
        self.queue = queue
        self.exclusive = exclusive
        self.bJsonParameters = False

    def consume(self, *args, **kwargs):
        pass

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s.Consumer: %s>' % (self.__module__, self.name)


def consumer(name=None, queue=None, exclusive=False):

    def decorator(func):
        cname = name or func.__name__

        c = Consumer(cname, queue, exclusive)
        c.consume = func
        return c

    return decorator

ReplyLockName = "_MsgReply"
class MessageDispatcher(object):
    def __init__(self, connection, channel, exchange='', threaded = True, threadpool_size = -1):
        self._connection = connection
        self._channel = channel
        self._registries = {}
        if threadpool_size <= 0:
            self._executor = ThreadPoolExecutor()
        else:
            self._executor = ThreadPoolExecutor(threadpool_size)
        self._exchange = exchange
        self._threaded = threaded

        self.consumer_tag = None

    def register(self, consumer):
        if consumer.name not in self._registries:
            self._registries[consumer.name] = consumer

    def __call__(self, *args, **kwargs):
        return self.dispatch_message(*args, **kwargs)

    def clear(self):
        self._registries = {}

    def dispatch_message(self, channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param Bytes or json: The message body

        """
        try:
            consumer_name = properties.headers.get('consumer_name')
        except :
            consumer_name = 'default'
        if consumer_name is None:
            consumer_name = 'default'

        logger.info("Received a remote call on function '%s'", consumer_name)
        old_consumer_name = consumer_name
        if consumer_name not in self._registries:
            consumer_name = "default"
        try:
            consumer = self._registries[consumer_name]
        except KeyError:
            msg = "Function '%s' not found." % old_consumer_name
            logger.info(msg)
            if properties.reply_to:
                self.reply_message(
                    properties, msg, is_error=True)
            self.acknowledge_message(basic_deliver.delivery_tag)
            return

        try:
            if not consumer.bJsonParameters:
                arguments = pickle.loads(body)
            else:
                arguments = json.loads(body.decode('utf-8'))
        except Exception as e:
            logger.error("Load arguments failed: {}".format(e))
            arguments = {}
        if not isinstance(arguments, dict):
            if isinstance(arguments, list) or isinstance(arguments, tuple):
                args = arguments
                kwargs = {}
            else:
                args = []
                kwargs = {"ErrorInfo":f"Invalid parameters, original arguments: {arguments}, original body: {body}"}
        else:
            args = arguments.get('args', [])
            kwargs = arguments.get('kwargs', {})
            if not (isinstance(args, list) or isinstance(args, tuple)):
                args = [args]
            if not isinstance(kwargs, dict):
                kwargs = {'kwargs':kwargs}
            if len(args) == 0 and len(kwargs) == 0 and len(arguments):
                kwargs = arguments
        if not self._threaded:
            self.call_comsumer(consumer, basic_deliver.delivery_tag, properties, *args, **kwargs)
        else:
            self._executor.submit(self.call_comsumer, consumer,
                                basic_deliver.delivery_tag, properties, *args, **kwargs)
    @ThreadAtomLock(ReplyLockName)
    def reply_message(self, props, body, headers=None, is_error=False):
        if headers is None:
            headers = {}

        headers[ERROR_FLAG] = NO_ERROR if not is_error else HAS_ERROR
        self._connection.ioloop.add_callback_threadsafe(partial(self._channel.basic_publish,
                                                                    exchange=self._exchange,
                                                                    routing_key=props.reply_to,
                                                                    properties=pika.BasicProperties(
                                                                        correlation_id=props.correlation_id,
                                                                        headers=headers),
                                                                    body=pickle.dumps(body)
                                                                ))

    def call_comsumer(self, consumer, delivery_tag, props, *args, **kwargs):
        try:
            ret = consumer.consume(*args, **kwargs)
            is_error = False
        except Exception as ex:
            logger.exception(
                'Error occurred when calling consumer. consumer: %s, args: %s, '
                'kwargs: %s', consumer.name, args, kwargs)
            ret = str(ex)
            is_error = True

        if props.reply_to is not None:
            self.reply_message(props, ret, is_error=is_error)

        self.acknowledge_message(delivery_tag)

    @ThreadAtomLock(ReplyLockName)
    def acknowledge_message(self, delivery_tag):
        self._connection.ioloop.add_callback_threadsafe(partial(self._channel.basic_ack, delivery_tag))
        # ret = self._channel.basic_ack(delivery_tag)

    def __contains__(self, consumer_name):
        return consumer_name in self._registries

    def stop(self):
        self._executor.shutdown()
