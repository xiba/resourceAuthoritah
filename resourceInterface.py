import redis

def isResourceLocked(fResourceName):
    '''Returns true if said resource is locked. Note that we don't check if the resource exists.'''
    r = redis.Redis() #TODO: get server config from the flask app
    return True if r.get(fResourceName) else False

def acquireResource(fResourceName, fValue, fExpiry):
    '''Attempts to acqurie the lock. Returns None on failure'''
    r = redis.Redis() #TODO: get server config from the flask app
    setResult = r.set(name=fResourceName, value=fValue, nx=True, ex=fExpiry)
    return True if setResult else False

def releaseResource(fResourceName, fValue):
    '''Attempts to release the lock, the passed value must match it's value.'''
    r = redis.Redis() #TODO: get server config from the flask app
    storedValue = r.get(fResourceName)
    if(storedValue == None):
        return True

    if(storedValue.decode('utf-8') != fValue):
        return False

    r.delete(fResourceName)
    return True
