# supercache
Easy to use and intuitive caching for functions.

## Usage
```python
from supercache import cache

# Cache all parametes other than print_output, and keep the result for 60 seconds
@cache(timeout=60, ignore=['print_output'])
def func(a, b=None, print_output=True):
    sleep(10)
    if print_output:
        print(a)
    return a

# Writes value to cache
func(1, 2, False)

# Reads value from cache
func(1, 2)

# Removes value from cache
cache.delete(func, 1, 2)


# Only cache the first argument, and ignore anything extra
@cache(keys=[0])
def func(a, b=None, *args):
    sleep(10)
    return a

# Writes value to cache
func(1)

# Reads value from cache
func(1, 2, 3, 4, 5, 6, 7)
```

### Supported Types
```python
# Functions
@cache()
def function():
    pass

# Methods
class Class(object):
    @cache()
    def method(self):
        pass

# Generators/iterators
@cache()
def generator():
    yield

# Lambdas
func = cache()(lambda: None)
```

## API Reference

### cache(_keys=None, ignore=None, timeout=None, size=None, precalculate=False_)

#### keys
Set which parameters of the function to use in generating the cache key. All available parameters will be used by default.

These can be in the format of `int`, `str`, `slice` (useful for `*args`), or `regex` (useful for `**kwargs`)

#### ignore
Set which parameters to ignore when generating the cache key. This will override any settings provided in `keys`.

These can also be in the format of `int`, `str`, `slice` or `regex`

#### timeout
Set how many seconds until the cache is invalidated.

#### size
Set the maximum size of the cache in bytes. This a soft limit, where the memory will be allocated first, then older cache will be deleted until it is back under the limit.

The latest execution will always be cached, even if the maximum size is set to smaller than the result.

#### precalculate
If the function being cached is a generator, setting this to `True` will convert the output to a `tuple` when first called, instead of returning the iterator.

The reason for this is the generator caching has a lot of overhead, which could become very noticable when calling a simple generator thousands of times.

### cache.delete(_func=None, *args, **kwargs_)
- `cache.delete()`: Delete all cached data.
- `cache.delete(func)`: Delete all cached data for `func`.
- `cache.delete(func, 1, b=2)`: Delete the cached data for `func(1, b=2)`.

### cache.hits(_func=None, *args, **kwargs_)
Return a count of how many times the cache was read for the given parameters.

- `cache.hits()`: Number of total cache hits.
- `cache.hits(func)`: Number of cache hits for `func`.
- `cache.hits(func, 1, b=2)`: Number of cache hits specifically for `func(1, b=2)`.

### cache.misses(_func=None, *args, **kwargs_)
Return a count of how many times the cache was generated for the given parameters.

- `cache.misses()`: Number of total cache misses.
- `cache.misses(func)`: Number of cache misses for `func`.
- `cache.misses(func, 1, b=2)`: Number of cache misses specifically for `func(1, b=2)`.

## Limitations
- Unable to cache if unhashable arguments are used
- Python will assign the same hash to two classes with the same inheritance if they are both initialised on the same line (fortunately this shouldn't ever happen outside of testing)
- `classmethods`, `staticmethods` and `properties` can only be cached if the cache decorator is executed first
- Probably not very threadsafe
