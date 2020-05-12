# -*- coding: utf-8 -*-
import logging
import time
import uuid

import pika
from .base import Connector
import pickle
import json

from .exceptions import (ERROR_FLAG, HAS_ERROR, NO_ERROR, RemoteFunctionError,
                         RemoteCallTimeout)

logger = logging.getLogger(__name__)

class RPCClient(Connector):
    '''
    RPC client.
    Parameters:
        amqp_url: amqp url connect to rabbitmq server. If this is specified, host ip and port parameters will not be used.

        host, port, username, passwd: Rabbitmq ip address and port and account.
        durable, auto_delete: The exchange property that this client will connect to. But, RPCClient will create its own
            queue, whose name is random allocated. This random allocated queue will not be affected by these parameters.
        virtual_host: Your vhost in rabbitmq server
        threaded: Invalid in RPCClient
        exchange: exchange name that will be used.
        queue_name: queue name you want to connect. If not setted, the queue name will be allocated randomly.
        bDataJson: Whether your data will be transmitted in json. If setted to false, the data will be transmitted with pickle.
            This flag should be set if the RPCServer also set to True, otherwise, leave it default.
    '''
    def __init__(self, bDataJson = False, queue_name = "",**kwargs):
        self._results = {}
        self.callback_queue = None
        self.bDataJson = bDataJson
        self._local_queues = []
        self.queue_name = queue_name
        super(RPCClient, self).__init__(**kwargs)
        self._threaded = False # Force threaded flag to false
        self._connection = self.connect()
        self._channel = self._connection.channel()
        self._channel.exchange_declare(self._exchange, exchange_type='direct', auto_delete=self.auto_delete, durable=self.durable)
        self.setup_callback_queue()

    def setup_callback_queue(self):
        if not self.callback_queue:
            # if len(self.queue_name):
            #     ret = self._channel.queue_declare(queue=self.queue_name, exclusive=False, auto_delete=self.auto_delete,
            #                                       durable=self.durable)
            # else:
            ret = self._channel.queue_declare(queue="", exclusive=False, auto_delete=True)
            self.callback_queue = ret.method.queue
            self._channel.queue_bind(self.callback_queue, self._exchange)
            self._channel.basic_consume(self.callback_queue,
                                       self.on_response,
                                       auto_ack=True)

    def on_response(self, channel, basic_deliver, props, body):
        if self.bDataJson:
            ret = json.loads(body.decode('utf-8'))
        else:
            ret = pickle.loads(body)
        if props.headers.get(ERROR_FLAG, NO_ERROR) == HAS_ERROR:
            ret = RemoteFunctionError(ret)
        self._results[props.correlation_id] = ret

    def get_response(self, correlation_id, timeout=None):
        stoploop = time.time() + timeout if timeout is not None else 0
        while stoploop > time.time() or timeout is None:
            self._connection.process_data_events()
            if correlation_id in self._results:
                return self._results.pop(correlation_id)
            self._connection.sleep(0.01)

        raise RemoteCallTimeout()


    def publish_message(self, exchange, routing_key, body, ignore_result = False, headers=None):
        corr_id = str(uuid.uuid4())
        rply_to = None
        if not ignore_result:
            rply_to = self.callback_queue
        if self.bDataJson:
            body = json.dumps(body).encode('utf-8')
        else:
            body = pickle.dumps(body)

        self._channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            properties=pika.BasicProperties(
                reply_to=rply_to,
                headers=headers,
                correlation_id=corr_id,
            ),
            body=body)

        return corr_id

    def skip_response(self, correlation_id):
        self._results.pop(correlation_id, None)

    def call(self, consumer_name):

        def func(*args, **kwargs):
            """Call the remote function.

            :param bool ignore_result: Ignore the result return immediately.
            :param str exchange: The exchange name consists of a non-empty.
            :param str routing_key: The routing key to bind on.
            :param float timeout: if waiting the result over timeount seconds,
                                  RemoteCallTimeout will be raised .
            """
            ignore_result = kwargs.pop('__ignore_result', False)
            exchange = kwargs.pop('__exchange', self._exchange)
            routing_key = kwargs.pop('__routing_key', self.queue_name)
            timeout = kwargs.pop('__timeout', None)

            if not ignore_result:
                self.setup_callback_queue()

            try:
                if timeout is not None:
                    timeout = float(timeout)
            except (ValueError, TypeError):
                raise ValueError("'timeout' is expected a float.")

            payload = {
                'args': args,
                'kwargs': kwargs,
            }
            corr_id = self.publish_message(
                exchange,
                routing_key,
                body=payload,
                ignore_result = ignore_result,
                headers={'consumer_name': consumer_name})

            logger.info('Sent remote call: %s', consumer_name)
            if not ignore_result:
                try:
                    ret = self.get_response(corr_id, timeout)
                except RemoteCallTimeout:
                    raise RemoteCallTimeout(
                        "Calling remote function '%s' timeout." % consumer_name)

                if isinstance(ret, RemoteFunctionError):
                    raise ret

                return ret

            self.skip_response(corr_id)

        func.__name__ = consumer_name
        return func

    def __getattribute__(self, key):
        if key.startswith('call_'):
            _, consumer_name = key.split('call_')
            return self.call(consumer_name)

        return super(RPCClient, self).__getattribute__(key)

    def __del__(self):
        pass
        # if not self._connection.:
        #     self._connection.close()
