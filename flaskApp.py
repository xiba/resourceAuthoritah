import resourceInterface
import json

from flask import Flask
from flask import request
from flask import jsonify
app = Flask(__name__)

@app.route('/resources/<fResourceName>', methods=['GET'])
def queryResource(fResourceName):
    replyDict = {}
    if(resourceInterface.isResourceLocked(fResourceName)):
        replyDict = {fResourceName : 'locked'}
    else:
        replyDict = {fResourceName : 'free'}
    return jsonify(replyDict)

@app.route('/resources/<fResourceName>', methods=['POST'])
def acquireResource(fResourceName):
    replyDict = {}
    requestData = request.get_json()

    if('expiry' not in requestData):
        requestData['expiry'] = 5
    if('id' not in requestData):
        replyDict = {'Argument error' : 'ID not provided in request'}
        return jsonify(replyDict)

    expiryVal = requestData['expiry']
    idVal = requestData['id']

    if(resourceInterface.acquireResource(fResourceName, idVal, expiryVal)):
        replyDict = {fResourceName : 'acquired'}
    else:
        replyDict = {fResourceName : 'rejected'}
    return jsonify(replyDict)

if __name__ == '__main__':
    app.run()
