RPC based on rabbitmq, cloned from [here](https://github.com/MidTin/rabbit-rpc)

### How To Use
The orignal code can just be runned in console and has problems in windows(Server side). So I modified some code. 
Now, the server side supports both pika.BlockConnection and pika.SelectionConnection. 
In BlockConnection mode, the server side can only be runned in single thread. In SelectionConnection mode, 
the server can be runned in multi-threads(Not in windows).

* Install:
```buildoutcfg
pip install rabbitmq-rpc
```

* Usage:  
1.Create rabbitmq account in your rabbitmq server.  
2.Run server.py first and then run client.py


* Server.py

```python  
from rabbitmq_rpc import server as Server
server = Server.RPCServer(queue_name='default',
                          amqp_url = "amqp://yourname:yourpasswd@10.147.17.135:5672/",
                          threaded=False)

@server.consumer()
def add(a, b):
    return a+b

if __name__ == '__main__':
    server.run()

```
* Client.py

```python
from rabbitmq_rpc.client import RPCClient
import time

def add(i):
    t1 = time.time()
    client = RPCClient(amqp_url='amqp://yourname:yourpasswd@10.147.17.135:5672/')
    res = client.call_add(0, i)
    t2= time.time()
    print(f"{0} + {i} = {res} RPC Time Cost: {t2-t1:.2f}")
    return res

for i in range(300):
    obj = add(i)

```
* Client with flask: client_with_flask.py

```python
from rabbitmq_rpc.client import RPCClient
import flask
web = flask.Flask(__name__)
web.debug = True
import time

def add(i):
    t1 = time.time()
    client = RPCClient(amqp_url='amqp://yourname:yourpasswd@10.147.17.135:5672/')
    res = client.call_add(0, i)
    t2= time.time()
    print(f"{0} + {i} = {res} RPC Time Cost: {t2-t1:.2f}")
    return res

@web.route('/web/<n>')
def test_web(n):
    res = add(int(n))
    return str(res)
if __name__ == '__main__':
    # Notice, In default, flask enabled threading. 
    # If single-thread is needed, pass in 'threaded=False' option
    web.run(host = '0.0.0.0', use_reloader = False)
```

*Note: **RPCClient** is not thread-safe. This is because pika is not thread-safe. 
So, create a RPCClient object only in one thread. DO NOT use it in multi-threads. *

### Original [README](https://github.com/MidTin/rabbit-rpc)
*Note: replace rabbit_rpc with rabbitmq_rpc*

    ==========
    Rabbit RPC 
    ==========
    
    简述
    ----
    
    这是对 RabbitMQ 的 Pika_ 库进行封装的，一套简易 RPC 客户端/服务端库。
    
    
    安装说明
    --------
    
    ::
    
        pip install rabbit-rpc
        
    
    
    使用事例
    --------
    
    服务端
    ~~~~~~
    
    ::
    
        # project/consumers.py
    
        from rabbit_rpc.consumer import consumer
    
        @consumer(name='add')
        def add(a, b):
            return a + b
    
    
        # project shell
        rabbit_rpc worker --amqp 'amqp://guest:guest@localhost:5672/'
    
    
        # with django
    
        rabbit_rpc worker --amqp 'amqp://guest:guest@localhost:5672/' --django project
        
    
    
    客户端
    ~~~~~~
    
    ::
        
        from rabbit_rpc.client import RPCClient
    
        client = RPCClient(amqp_url='amqp://guest:guest@localhost:5672/')
        ret = client.call_add(1, 1, timeout=1)
    
        # or ignore result
        client.call_add(1, 1, ignore_result=True)
    
        # specify routing_key
        client.call_add(1, 1, routing_key='default')
    
    
    .. _Pika: https://github.com/pika/pika