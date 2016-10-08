import redis

class ResourceDoesNotExist(ValueError):
    pass

def isResourceLocked(fResourceName):
    '''Returns true if said resource is locked. Note that we don't check if the resource exists.'''
    r = redis.Redis(host='127.0.0.1', port=6379, password=None)
    return True if r.get(fResourceName) else False

def acquireResource(fResourceName, fValue, fExpiry):
    '''Attempts to acqurie the lock. Returns None on failure'''
    r = redis.Redis(host='127.0.0.1', port=6379, password=None)
    setResult = r.set(name=fResourceName, value=fValue, nx=True, ex=fExpiry)
    return True if setResult else False
