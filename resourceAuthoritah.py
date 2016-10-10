import resourceInterface
import json
import time
import random
import sys
from flask import Flask
from flask import request
from flask import jsonify
from functools import wraps
from datetime import datetime
app = Flask('resourceAuthoritah')

def nocache(func):
    @wraps(func)
    def no_cache(*args, **kwargs):
        response = func(*args, **kwargs)
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

@nocache
@app.route('/resources/<fResourceName>', methods=['GET'])
def queryResource(fResourceName):
    if(request.content_type != 'application/json'):
        return "", 400

    replyDict = {'resource' : fResourceName}
    if(resourceInterface.isResourceLocked(fResourceName)):
        replyDict[fResourceName] = 'locked'
    else:
        replyDict[fResourceName] = 'free'
    return jsonify(**replyDict)

@nocache
@app.route('/resources/<fResourceName>', methods=['POST'])
def acquireResource(fResourceName):
    if(request.content_type != 'application/json'):
        return "", 400

    replyDict = {'resource' : fResourceName}
    requestData = request.get_json()

    numberOfLockingAttempts = 0
    sleepDurationInSeconds = 0
    if('timeout' in requestData and requestData['timeout'] > 0):
        timeoutWindowToRetry = requestData['timeout']
        sleepDurationInSeconds = max(0.1, timeoutWindowToRetry / 10)#nothing shorter than 100 milliseconds, 10 attempts sounds good enough
        sleepDurationInSeconds = min(1, sleepDurationInSeconds) #shouldn't sleep for too long
        sleepDurationInSeconds += random.random() #some jitter
        numberOfLockingAttempts = timeoutWindowToRetry // sleepDurationInSeconds

    if('expiry' not in requestData):
        requestData['expiry'] = 5
    elif(requestData['expiry'] > 120 or requestData['expiry'] < 1): #whatever limit, should be configured according to the usecase of the server
        replyDict['error'] = 'Expiration value of ' + str(requestData['expiry']) + ' is out of bound'
        return jsonify(**replyDict)

    if('id' not in requestData):
        replyDict['error'] = 'ID not provided in request'
        return jsonify(**replyDict)

    expiryVal = requestData['expiry']
    idVal = requestData['id']

    #if resource is locked, check if there's a deadlock, return if yes
    if(resourceInterface.acquireResource(fResourceName, idVal, expiryVal)): #resource locked
        return jsonify(**replyDict) #succeded in acquiring lock

    resourceInterface.addReverseEdge(idVal, fResourceName)

    if(resourceInterface.detectDeadlock(idVal, fResourceName)):
        replyDict['error'] = 'deadlock, consider relinquishing resources'
        resourceInterface.removeReverseEdge(idVal, fResourceName)
        return jsonify(**replyDict)

    #if the user specified a timeout, keep trying for that length of time
    while(numberOfLockingAttempts > 0):
        if(resourceInterface.acquireResource(fResourceName, idVal, expiryVal)):
            resourceInterface.removeReverseEdge(idVal, fResourceName)
            return jsonify(**replyDict)
        numberOfLockingAttempts -= 1
        time.sleep(sleepDurationInSeconds)

    resourceInterface.removeReverseEdge(idVal, fResourceName)

    #Nothing to do but retry, cri moar
    replyDict['error'] = 'resource is already locked'
    return jsonify(**replyDict)

@nocache
@app.route('/resources/<fResourceName>', methods=['DELETE'])
def releaseResource(fResourceName):
    if(request.content_type != 'application/json'):
        return "", 400

    replyDict = {'resource' : fResourceName}
    requestData = request.get_json()
    if('id' not in requestData):
        replyDict['error'] = 'ID not provided in request'
        return jsonify(**replyDict)

    isDeleted = resourceInterface.releaseResource(fResourceName, requestData['id'])
    if(not isDeleted):
        replyDict['error'] = 'Wrong id'
    return jsonify(**replyDict)

if __name__ == '__main__':
    app.run()
