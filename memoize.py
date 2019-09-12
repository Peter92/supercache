"""Cache/memoize results from functions.

Author: Peter Hunt
Modified: 11/9/2019
"""
from __future__ import absolute_import

import inspect
import time
from functools import partial
from types import GeneratorType


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass.
    
    Source: six.py
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


class CacheError(Exception):
    pass


class GeneratorCache(object):
    """Cache the results from a generator."""
    def __init__(self, func, *args, **kwargs):
        self.func = func(*args, **kwargs)
        self.cache = []
        self.current = 0
        self.total = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < self.total:
            value = self.cache[self.current]
        else:
            try:
                self.cache.append(next(self.func))
                self.total += 1
            except StopIteration:
                self.current = 0
                raise StopIteration

        result = self.cache[self.current]
        self.current += 1
        return result
    next = __next__


class Memoize(object):
    Data = {}
    def __init__(self, parent, func, group, timeout=None, key_args=None, key_kwargs=None):
        self.parent = parent
        self.func = func
        self.group = group
        self.timeout = timeout
        self.args = key_args
        self.kwargs = key_kwargs

        self.generator = inspect.isgeneratorfunction(self.func)

        self.hash = hash(self.func)
        if self.group not in self.Data:
            self.Data[self.group] = {}
        if self.hash not in self.Data[self.group]:
            self.Data[self.group][self.hash] = {}

    def __repr__(self):
        return self.func.__repr__()

    def __call__(self, *args, **kwargs):
        """Find if the result exists in cache or generate a new result."""
        fingerprint = self.fingerprint(*args, **kwargs)
        try:
            data = self.Data[self.group][self.hash]
        except KeyError:
            data = self.Data[self.group][self.hash] = {}
        
        # Refresh the function
        if fingerprint not in data or self.timeout is not None and time.time() - data[fingerprint][1] > self.timeout:
            if self.generator:
                result = GeneratorCache(self.func, *args, **kwargs)
            else:
                result = self.func(*args, **kwargs)
            data[fingerprint] = (result, time.time())

        # Reset the generator counter
        elif self.generator:
            data[fingerprint][0].current = 0

        return data[fingerprint][0]

    def __get__(self, instance, owner):
        return partial(self.__call__, instance)

    def fingerprint(self, *args, **kwargs):
        """Generate a unique fingerprint for the function."""
        # Generate a dict containing all the values
        func_params, func_args, func_kwargs, func_defaults = inspect.getargspec(self.func)
        if func_defaults is None:
            default_values = {}
        else:
            default_values = dict(zip(reversed(func_params), reversed(func_defaults)))

        hash_list = []

        num_args = len(args)
        for i in self.args:
            # Argument is provided
            if i < num_args:
                hash_list.append(args[i])
            else:
                # Argument is provided as a kwarg
                try:
                    param = func_params[i]
                except IndexError:
                    param = None
                if param in kwargs:
                    hash_list.append(kwargs[param])
                # Argument is not provided
                else:
                    try:
                        hash_list.append(default_values[param])
                    # Skip any KeyError as its an invalid argument TypeError
                    except KeyError:
                        pass

        # Keyword arguments are set as arguments
        # Setup a dict to be used when parsing kwargs
        argument_kwargs = {}
        if self.args:
            i += 1
            while i < num_args:
                param = func_params[i]
                argument_kwargs[param] = args[i]
                i += 1

        for key in self.kwargs:
            # Keyword argument is provided
            if key in kwargs:
                hash_list.append(kwargs[key])
            # Keyword argument is given without a keyword
            elif key in argument_kwargs:
                hash_list.append(argument_kwargs[key])
            # Keyword argument is not provided
            else:
                hash_list.append(default_values.get(key, None))

        try:
            return tuple(map(hash, hash_list))
        except TypeError:
            raise CacheError('cannot cache with unhashable arguments')

    @property
    def cache(self):
        return self.Data[self.group][self.hash]

    @cache.deleter
    def cache(self):
        del self.Data[self.group][self.hash]


class CacheMeta(type):
    def __getitem__(self, item):
        """Set data under the name of a group."""
        return partial(Cache, group=item)

    def __delitem__(self, item):
        """Delete all the memoized data in a group."""
        Memoize.Data[item] = {}


@add_metaclass(CacheMeta)
class Cache(object):
    def __init__(self, args=None, kwargs=None, timeout=None, group=None):
        """Setup the cache.

        Each record unique to the function, with optional arguments
        that will output a different result. For example, print_values
        will not affect the result, but output_json will.

        These can be put in as either arg indexes or kwarg strings.

        Example:
            # Cache on the values of "a", "b", "c" and "d"
            >>> @Cache(args=(0, 1), kwargs=['c', 'd'], timeout=60)
            >>> def func(a, b=2, c=3, **kwargs): pass

        Groups:
            For easier deletion of specific things, a group can be set.
            Either pass in "group" as an argument, or set it at the start
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout
        self.group = group

    def __call__(self, func):
        return Memoize(
            self, func,
            group=self.group,
            timeout=self.timeout,
            key_args=self.args,
            key_kwargs=self.kwargs,
        )


if __name__ == '__main__':
    import uuid

    # Function test
    @Cache()
    def unique_id():
        return uuid.uuid4()
    del unique_id.cache

    first_id = unique_id()
    assert first_id == unique_id()
    del unique_id.cache
    assert first_id != unique_id()

    # Class test (no arguments)
    class Test(object):
        @Cache()
        def unique_id(self):
            return uuid.uuid4()

    first_id = Test().unique_id()
    assert first_id == Test().unique_id()
    
    second_id = Test().unique_id()
    assert second_id == first_id

    # Class test (arguments)
    class Test(object):
        def __init__(self, n):
            self.n = n
        def __hash__(self):
            return hash(self.n)
        @Cache(kargs=['self'])
        def unique_id(self):
            return uuid.uuid4()

    first_id = Test(1).unique_id()
    assert first_id == Test(1).unique_id()
    assert first_id != Test(2).unique_id()

    # Generator test
    @Cache(timeout=5)
    def gen():
        for i in range(3):
            yield i
            yield uuid.uuid4()
    assert 1 in gen()
    assert 1 in gen()
    assert list(gen()) == list(gen())
