import time
import threading
import queue
import functools

class LockNames():
    names = {}

class ThreadAtomLock(object):
    '''
    适用于需要原子操作的函数。直接修饰该函数即可
    用法：
    @ThreadAtomLock()
    def func(a,b,c):
        ...
    则该func在多线程的调用中会被自动加锁
    '''
    def __init__(self, lockname = "default"):
        self.lockname = lockname
        if lockname in LockNames.names:
            self.lock = LockNames.names[lockname]
        else:
            LockNames.names[lockname] = threading.Lock()
            self.lock = LockNames.names[lockname]

    def __call__(self, func):
        def _atom(*arg, **kw):
            self.lock.acquire()
            try:
                v = func(*arg, **kw)
            except Exception as e:
                self.lock.release()
                raise
            self.lock.release()
            return v
        return _atom
    
    def __enter__(self):
        self.lock.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

class ThreadPool(object):
    '''
    定义线程池类。
    参数：
        pool_size为线程池中能够容纳的线程个数。
        bReturnObj:修饰的函数是否返回ThreadPool对象，返回的对象可以用于调用join，等待所有线程结束
    使用方法：
        @ThreadPool(3, bReturnObj = True)
        def func(a,b,c):
            ...
        for i in range(n):
            th_obj = func(a,b,c)
        th_obj.join() # 等待所有线程结束
        在调用func时，func会使用多线程执行，但一次最多开启3个线程。当线程池中有线程结束后，
        才允许新的线程加入线程池
    '''
    def __init__(self, pool_size=-1, bReturnObj = False):
        if pool_size <= 0:
            pool_size = os.cpu_count()
        self.pool_size = pool_size
        self.flag_pool = queue.Queue(pool_size)
        self._thread_in_pool = [None]*pool_size
        self.lock = threading.Lock()
        self.bRetObj = bReturnObj
    def _allocate_empty_pos(self):
        for i,th in enumerate(self._thread_in_pool):
            if th is None:
                return i
        return None


    def __call__(self, func):
        def _run_thread_func(th_pos, func, *args, **kwargs):
            func(*args, **kwargs)
            self._thread_in_pool[th_pos] = None
            self.flag_pool.get()
        @functools.wraps(func)
        def thread_func(*args, **kwargs):
            self.flag_pool.put('V')
            th_pos = 0
            th_pos = self._allocate_empty_pos()
            if th_pos is None:
                raise Exception("Error pos")
            th = threading.Thread(target=_run_thread_func, args=(th_pos, func, *args), kwargs=kwargs)
            self._thread_in_pool[th_pos] = th
            th.start()
            if self.bRetObj:
                return self
        return thread_func

    def join(self):
        while any(self._thread_in_pool):
            time.sleep(0.05)
__all__ = ["ThreadAtomLock", "ThreadPool"]
