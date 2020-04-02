import six

if six.PY3:
    from threading import Condition

else:
    from threading import _Condition
    from monotonic import monotonic as _time

    class Condition(_Condition):

        def wait_for(self, predicate, timeout=None):
            """Wait until a condition evaluates to True.

            predicate should be a callable which result will be interpreted as a
            boolean value.  A timeout may be provided giving the maximum time to
            wait.

            """
            endtime = None
            waittime = timeout
            result = predicate()
            while not result:
                print(result)
                if waittime is not None:
                    if endtime is None:
                        endtime = _time() + waittime
                    else:
                        waittime = endtime - _time()
                        if waittime <= 0:
                            break
                self.wait(waittime)
                result = predicate()
            return result