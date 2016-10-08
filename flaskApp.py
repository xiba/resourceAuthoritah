import resourceInterface
import json

from flask import Flask
from flask import request
from flask import jsonify
app = Flask(__name__)

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

@app.route('/resources/<fResourceName>', methods=['POST'])
def acquireResource(fResourceName):
    if(request.content_type != 'application/json'):
        return "", 400

    replyDict = {'resource' : fResourceName}
    requestData = request.get_json()

    if('expiry' not in requestData):
        requestData['expiry'] = 5
    elif(requestData['expiry'] > 120): #whatever limit, should be configured according to the usecase of the server
        replyDict['error'] = 'Expiration value of ' + str(requestData['expiry']) + ' is too large'
        return jsonify(**replyDict)
    if('id' not in requestData):
        replyDict['error'] = 'ID not provided in request'
        return jsonify(**replyDict)

    expiryVal = requestData['expiry']
    idVal = requestData['id']

    if(not resourceInterface.acquireResource(fResourceName, idVal, expiryVal)):
        replyDict['error'] = 'resource is already locked'
    return jsonify(**replyDict)

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
