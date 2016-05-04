from tornado.ioloop import IOLoop

class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    Credit: http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

@Singleton
class CallbackHandling:
    """singleton to manage the creation and removal of callbacks for the various python scripts that are part of the werewolves site"""

    def __init__(self):
        self.callbacks = {}
        self.iol = IOLoop.current() # will only work for single threaded, non switching loops.
        return

    def add_callback(self, id, callback_handler):
        if id in self.callbacks:
            callback_reference = len(self.callbacks[id])
        else:
            self.callbacks[id] = {}
            callback_reference = 0

        self.callbacks[id][callback_reference] = callback_handler

        return callback_reference

    def remove_callback(self, id, callback_reference):
        self.iol.remove_timeout(timeout=self.callbacks[id][int(callback_reference)])
        self.callbacks[id].pop(int(callback_reference))

    def cleanup(self):
        raise NotImplementedError



callback_handler = CallbackHandling.Instance()