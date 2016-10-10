import redis
import queue
import time

def isResourceLocked(fResourceName):
    '''Returns true if said resource is locked. Note that we don't check if the resource exists.'''
    r = redis.Redis() #TODO: get server config from the flask app
    return True if r.get(fResourceName) else False

def acquireResource(fResourceName, fValue, fExpiry):
    '''Attempts to acqurie the lock. Returns None on failure'''
    r = redis.Redis() #TODO: get server config from the flask app
    setResult = None

    valueIfExists = r.get(fResourceName)
    if( valueIfExists != None and valueIfExists.decode('utf-8') == fValue): #same owner wants to update TTL
        setResult = r.set(name=fResourceName, value=fValue, ex=fExpiry)
    else:
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

def addReverseEdge(fClient, fResource):
    r = redis.Redis()
    r.sadd(fClient, fResource)
    pass

def removeReverseEdge(fClient, fResource):
    r = redis.Redis()
    r.srem(fClient, fResource)
    pass

def detectDeadlock(fInitialID, fRequestedResource):
    '''Searches for cycles in the resource ownership graph'''
    if(not isResourceLocked(fRequestedResource)):
        return False

    r = redis.Redis()
    visitedSet = set()
    nodeQueue = queue.Queue() #contains 3-tuples, first is a str for nodeName, second is either resource/client, third is parent
    nodeQueue.put((fInitialID, 'client', fInitialID))

    while(not nodeQueue.empty()):
        currentNode = nodeQueue.get()
        visitedSet.add(currentNode[0])
        if(currentNode[1] == 'resource'):
            currentResourceOwner = r.get(currentNode[0])
            if(currentResourceOwner == None): #resource is already free (eg its entry in its owner's list is stale)
                r.srem(currentNode[2], currentNode[0]) #update its owner/client's set
                continue
            if(currentResourceOwner.decode('utf-8') == fInitialID):
                return True
            if(currentResourceOwner.decode('utf-8') not in visitedSet):
                nodeQueue.put((currentResourceOwner.decode('utf-8'), 'client', currentNode[0], ))
        else:
            for resource in r.sscan_iter(currentNode[0]):
                if(resource.decode('utf-8') not in visitedSet):
                    nodeQueue.put((resource.decode('utf-8'), 'resource', currentNode[0], ))

    return False
