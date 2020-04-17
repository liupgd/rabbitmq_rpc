# -*- coding: utf-8 -*-
import logging
from threading import Lock
import sys
import pika
import warnings

logger = logging.getLogger(__name__)

class Connector(object):
    '''
    Base connector.
    Parameters:
    amqp_url: amqp url to rabbitmq server, format is like this: amqp://yourname:yourpasswd@serverip:serverport/
    host,port,username, passwd: If amqp_url is not specified, you should specify these server parameters.
    exchange: exchange in the server
    threaded: If true, connector will run with pika.SelectionConnection. It's a asynchronous io. Otherwise,
        pika.BlockConnection will be used. In asynchronous io mode. The RPC server can run in multi-threaded mode.
        There is no difference for RPC clients.
    kwargs: Invalid if amqp_url specified. See more from pika.ConnectionParameters
    '''
    DEFUALT_QUEUE = 'default'
    EXCHANGE_TYPE = 'direct'
    def __init__(self, amqp_url=None,
                 host = "localhost", port = 5672, prefetch_count = 1,
                 username = "guest", passwd="guest", exchange='default', threaded = True, auto_delete = True, durable = False,
                 **kwargs):
        self.auto_delete = auto_delete
        self.durable = durable
        self._url = amqp_url
        self._exchange = exchange
        self._host = host
        self._port = port
        self._username = username
        self._passwd = passwd
        self.prefetch_count = prefetch_count
        self._channel = None
        self._connection = None
        self._closing = False
        self._lock = Lock()
        if threaded and sys.platform == 'win32':
            warnings.warn("### In windows, pika may has problems with multi-thread processing ###")
        self._threaded = threaded
        if 'conn_parameters' in kwargs:
            self.conn_parameters = kwargs.get("conn_parameters")
        else:
            self.conn_parameters = None
        if amqp_url is not None:
            self.conn_parameters = pika.URLParameters(self._url)
        elif self.conn_parameters is None:
            self.conn_parameters = pika.ConnectionParameters(host= self._host, port=self._port,
                                                             credentials=pika.PlainCredentials(self._username, self._passwd),
                                                             **kwargs)



    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        if self._threaded:
            self._connection = pika.SelectConnection(
                self.conn_parameters,
                on_open_callback=self.on_connection_open,
                on_close_callback=self.on_connection_closed)
        else:
            self._connection = pika.BlockingConnection(self.conn_parameters)
        return self._connection

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        logger.info('Connection opened..')
        self.open_channel()

    def on_connection_closed(self, *args):#connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logger.info(
                'Connection was closed unexpected, we will try to reconnect it..')
            # self._connection.add_timeout(1, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:

            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def open_channel(self):
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        logger.info('Channel opened..')

        self._channel = channel
        self._channel.basic_qos(prefetch_count=self.prefetch_count)
        self.add_on_channel_close_callback()
        if self._exchange:
            self.setup_exchange(self._exchange)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, chn_exception):#channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        logger.info('Channel closed..')
        self.close_connection()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        self._channel.exchange_declare(
            exchange_name, exchange_type=self.EXCHANGE_TYPE, auto_delete=self.auto_delete,
            callback=self.on_exchange_declareok, durable=self.durable)

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        pass

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        self._connection.close()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.

        """
        if self._channel is not None:
            self._channel.close()


