''' Unit tests for the app'''

import json
import time
import os
import unittest
import resourceAuthoritah
import redis
import sys
from multiprocessing import Pool, Process
import requests

def acquireLock(fTimePointOfAttack, fResourceName, fID, fExpirationTimeOfLock=30, fTimeoutWindow=0):
    '''attempts to acquire a lock using the requests module (so it won't need any shared data). Returns True if it did'''
    time.sleep(fTimePointOfAttack - time.time())
    replyObject = requests.post('http://127.0.0.1:5000/resources/' + fResourceName, json={"expiry": fExpirationTimeOfLock, "id" : fID, "timeout" : fTimeoutWindow})
    jsonReply = replyObject.json()
    return True if "error" not in jsonReply else False

def acquireAndReleaseLock(fTimePointOfAttack, fResourceName, fID, fExpirationTimeOfLock=30, fTimeoutWindow=0, fExtraResourcesToFree = []):
    '''Attempts to acquire then release a lock using the requests module (sp ot won't need any shared data). Returns true on success'''
    couldAcquire = acquireLock(fTimePointOfAttack, fResourceName, fID, fExpirationTimeOfLock, fTimeoutWindow)
    if(not couldAcquire):
        for r in fExtraResourcesToFree:
            replyObject = requests.delete('http://127.0.0.1:5000/resources/' + r, json={"id" : fID})
        return False

    for r in fExtraResourcesToFree:
        replyObject = requests.delete('http://127.0.0.1:5000/resources/' + r, json={"id" : fID})
    replyObject = requests.delete('http://127.0.0.1:5000/resources/' + fResourceName, json={"id" : fID})
    jsonReply = replyObject.json()
    return True if 'error' not in jsonReply else False

class ResourceAuthoritahTestCase(unittest.TestCase):
    def setUp(self):
        self.redisInstance = redis.Redis()
        for key in self.redisInstance.keys():
            self.redisInstance.delete(key)

        resourceAuthoritah.app.config['TESTING'] = True
        self.app = resourceAuthoritah.app.test_client()
        self.resourceName = 'resourceNAME'

    def tearDown(self):
        pass

    def helper_query_lock(self, fResourceName):
        '''Returns the state of the lock'''
        return self.app.get('/resources/' + fResourceName, content_type='application/json')

    def helper_acquire_lock(self, fResourceName, fID = "whatever daaaaad. I'm an adult now", fExpiration=30, fTimeoutWindow=0):
        '''Returns the response object'''
        jsonArgs = dict(id=fID, expiry=fExpiration, timeout=fTimeoutWindow)
        return self.app.post('/resources/' + fResourceName, data=json.dumps(jsonArgs), content_type='application/json')

    def helper_release_lock(self, fResourceName, fID = 'uhhh, I said whatever, now go away'):
        '''Returns the response object'''
        jsonArgs = {'id' : fID}
        return self.app.delete('/resources/' + fResourceName, data=json.dumps(jsonArgs), content_type='application/json')

    def test_get_free_resource(self):
        '''Fetch status of a free lock'''
        replyObject = self.helper_query_lock(self.resourceName)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert(replyBody[self.resourceName] == 'free')

    def test_get_locked_resource(self):
        '''Fetch status of a locked resource'''
        self.redisInstance.set(self.resourceName, 'value')

        replyObject = self.helper_query_lock(self.resourceName)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert(replyBody[self.resourceName] == 'locked')

    def test_acquire_free_resource(self):
        '''Test that you can acquire a free lock'''
        #Note that if the request's roundtrip is too long, this WILL fail
        replyObject = self.helper_acquire_lock(self.resourceName, 'my id', 3)

        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

        replyObject = self.helper_query_lock(self.resourceName)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert(replyBody[self.resourceName] == 'locked')

    def test_expiration_works(self):
        '''Test that locks do expire and become available after the predetermined length of time'''
        myID = 'still not Batman'
        expirationLength = 1
        replyObject = self.helper_acquire_lock(self.resourceName, myID, expirationLength)

        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

        replyObject = self.helper_query_lock(self.resourceName)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert(replyBody[self.resourceName] == 'locked')

        time.sleep(expirationLength)

        replyObject = self.helper_query_lock(self.resourceName)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert(replyBody[self.resourceName] == 'free')

    def test_expiration_limit_exists(self):
        '''There is an upper limit to the expiration field'''
        myID = 'still not Batman'
        expirationLength = 100000000
        replyObject = self.helper_acquire_lock(self.resourceName, myID, expirationLength)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' in replyBody)

        myID = 'still not Batman'
        expirationLength = 0
        replyObject = self.helper_acquire_lock(self.resourceName, myID, expirationLength)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' in replyBody)

        myID = 'still not Batman'
        expirationLength = -1
        replyObject = self.helper_acquire_lock(self.resourceName, myID, expirationLength)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' in replyBody)

    def test_releasing_free_resource(self):
        '''Test freeing something that is already free'''

        myID = 'still not batman'
        replyObject = self.helper_release_lock(self.resourceName, myID)

        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

    def test_releasing_locked_resource(self):
        '''Test freeing something that is locked (I own it)'''

        myID = 'still not batman'
        self.helper_acquire_lock(self.resourceName, myID, 3)
        replyObject = self.helper_release_lock(self.resourceName, myID)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

    def test_attempt_acquire_locked_resource(self):
        '''Attempt to acquire a locked lock'''

        replyObject = self.helper_acquire_lock(self.resourceName)
        assert('error' not in json.loads(replyObject.data.decode('utf-8')))
        replyObject = self.helper_acquire_lock(self.resourceName, fID='another client')
        assert('error' in json.loads(replyObject.data.decode('utf-8')))

    def test_release_locked_resource_without_id(self):
        '''Test freeing something that is locked (I don't own it)'''

        myID = 'still not batman'
        self.helper_acquire_lock(self.resourceName, myID, 3)
        replyObject = self.helper_release_lock(self.resourceName, 'another ID')
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' in replyBody)

    def test_sending_wrong_mime_data(self):
        '''Application should only accept application/json'''
        replyObject = self.app.get('/resources/' + self.resourceName, content_type='text/html')
        assert(replyObject.status_code == 400)
        replyObject = self.app.post('/resources/' + self.resourceName, content_type='text/html')
        assert(replyObject.status_code == 400)
        replyObject = self.app.delete('/resources/' + self.resourceName, content_type='text/html')
        assert(replyObject.status_code == 400)

    def test_sending_incomplete_body_to_acquire(self):
        '''You can't acquire a lock without an id'''
        jsonArgs = dict(expiry=3)
        replyObject = self.app.post('/resources/' + self.resourceName, data=json.dumps(jsonArgs), content_type='application/json')
        assert('error' in json.loads(replyObject.data.decode('utf-8')))

    def test_sending_incomplete_body_to_release(self):
        '''You can't release a lock without an id'''
        replyObject = self.helper_acquire_lock(self.resourceName) #make sure it exists
        jsonArgs = dict(expiry=3)
        replyObject = self.app.delete('/resources/' + self.resourceName, data=json.dumps(jsonArgs), content_type='application/json')
        assert('error' in json.loads(replyObject.data.decode('utf-8')))

    def test_wrong_http_methods(self):
        '''Only get, post and delete are supported'''
        replyObject = self.app.put('/resources/' + self.resourceName, content_type='application/json')
        assert(replyObject.status_code == 405)

    def test_concurrent_attempt_to_lock_free_resource_8(self):
        '''This tries to test the mutual exclusion condition when multiple processes are attempting to acquire a lock at the same time'''
        numberOfProcesses = 8
        resourceName = 'acquireLockKey'
        myID = 'me'
        expirationInSeconds = 5
        with Pool(processes=numberOfProcesses) as pool:
            whenToAcquire = time.time() + 5 #give them space to make sure everyone launches at the same time
            multiple_results = [pool.apply_async(acquireLock, (whenToAcquire, resourceName, myID + str(i), expirationInSeconds)) for i in range(numberOfProcesses)]
            multiple_results = [m.get() for m in multiple_results]
            assert(multiple_results.count(True) == 1)

        time.sleep(expirationInSeconds) #to ensure that the lock expired and is now available
        replyObject = self.helper_acquire_lock(resourceName, myID)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

    def test_concurrent_attempt_to_lock_free_resource_100(self):
        '''This tries to test the mutual exclusion condition when multiple processes are attempting to acquire a lock at the same time'''
        numberOfProcesses = 100
        resourceName = 'acquireLockKey'
        myID = 'me'
        expirationInSeconds = 5
        with Pool(processes=numberOfProcesses) as pool:
            whenToAcquire = time.time() + 5 #give them space to make sure everyone launches at the same time
            multiple_results = [pool.apply_async(acquireLock, (whenToAcquire, resourceName, myID + str(i), expirationInSeconds)) for i in range(numberOfProcesses)]
            multiple_results = [m.get() for m in multiple_results]
            assert(multiple_results.count(True) == 1)

        time.sleep(expirationInSeconds) #to ensure that the lock expired and is now available
        replyObject = self.helper_acquire_lock(resourceName, myID)
        replyBody = json.loads(replyObject.data.decode('utf-8'))
        assert('error' not in replyBody)

    def test_caching_is_off(self):
        '''We want to make sure that "quick" successive get requests won't be cached.'''
        myID = 'me'
        for i in range(1000):
            isLocked = json.loads(self.helper_query_lock(self.resourceName).data.decode('utf-8'))[self.resourceName] == 'locked'
            assert(isLocked == False)

            self.helper_acquire_lock(self.resourceName, myID)
            isLocked = json.loads(self.helper_query_lock(self.resourceName).data.decode('utf-8'))[self.resourceName] == 'locked'
            assert(isLocked == True)

            self.helper_release_lock(self.resourceName, myID)
            isLocked = json.loads(self.helper_query_lock(self.resourceName).data.decode('utf-8'))[self.resourceName] == 'locked'
            assert(isLocked == False)

    def test_timeout_argument(self):
        '''Tests the timeout argument in the lock acquisition process'''
        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=2).data.decode('utf-8'))
        assert('error' not in replyObject)

        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=2, fID = 'otherClient').data.decode('utf-8'))
        assert('error' in replyObject)

        time.sleep(2)

        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=2).data.decode('utf-8'))
        assert('error' not in replyObject)

        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=2, fTimeoutWindow=3, fID = 'otherClient').data.decode('utf-8'))
        assert('error' not in replyObject)

    def test_a_client_can_reacquire_resource_to_change_ttl(self):
        '''A client can "re-acquire" a resource. This is useful to change the TTL'''
        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=9).data.decode('utf-8'))
        assert('error' not in replyObject)

        replyObject = json.loads(self.helper_acquire_lock(self.resourceName, fExpiration=20).data.decode('utf-8'))
        assert('error' not in replyObject)

    def test_deadlock_detection_works(self):
        '''Tests if a deadlock will be detected'''
        self.helper_acquire_lock('r2', 'c1', 100, 100)
        self.helper_acquire_lock('r1', 'c2', 100, 100)

        p = Process(target=acquireLock, args=(time.time()+1, 'r1', 'c1', 100, 100))
        p.start()

        time.sleep(2) #to ensure the previous process has registered its request

        replyBody = json.loads(self.helper_acquire_lock('r2', 'c2', 100, 100).data.decode('utf-8'))
        assert('error' in replyBody)
        assert('deadlock' in replyBody['error'])

    def test_deadlock_detection_works_2(self):
        '''Tests if a deadlock will be detected'''

        replyObjects = [self.helper_acquire_lock('r3', 'c1', 100, 100)]
        replyObjects.append(self.helper_acquire_lock('r1', 'c2', 100, 100))
        replyObjects.append(self.helper_acquire_lock('r2', 'c3', 100, 100))

        # at this point all three operations should've succeeded
        for obj in replyObjects:
            assert('error' not in json.loads(obj.data.decode('utf-8')))

        #both of these requests should just hand around till there timeout ends or their resources are available
        pool = Pool(processes=5)
        p1 = pool.apply_async(acquireAndReleaseLock, (time.time()+1, 'r1', 'c1', 100, 7, ['r3']))
        p2 = pool.apply_async(acquireAndReleaseLock, (time.time()+1, 'r2', 'c2', 100, 7, ['r1']))

        time.sleep(2) #to ensure the previous processes have registered their requests

        #this request should create a deadlock as long as the ones before it haven't terminated yet
        replyBody = json.loads(self.helper_acquire_lock('r3', 'c3', 100, 2).data.decode('utf-8'))
        assert('error' in replyBody)
        assert('deadlock' in replyBody['error'])

        p1.get()
        p2.get()

    def test_deadlock_resolution_works(self):
        '''Tests if a deadlock can be resolved by relenquishing resources and retrying'''

        replyObjects = [self.helper_acquire_lock('r3', 'c1', 100, 100)]
        replyObjects.append(self.helper_acquire_lock('r1', 'c2', 100, 100))
        replyObjects.append(self.helper_acquire_lock('r2', 'c3', 100, 100))

        # at this point all three operations should've succeeded
        for obj in replyObjects:
            assert('error' not in json.loads(obj.data.decode('utf-8')))

        #both of these requests should just hand around till there timeout ends or their resources are available
        pool = Pool(processes=5)
        p1 = pool.apply_async(acquireAndReleaseLock, (time.time()+1, 'r1', 'c1', 100, 10, ['r3']))
        p2 = pool.apply_async(acquireAndReleaseLock, (time.time()+1, 'r2', 'c2', 100, 10, ['r1']))

        time.sleep(3) #to ensure the previous processes have registered their requests

        #this request should create a deadlock as long as the ones before it haven't terminated yet
        replyBody = json.loads(self.helper_acquire_lock('r3', 'c3', 100, 1).data.decode('utf-8'))
        assert('error' in replyBody)
        assert('deadlock' in replyBody['error'])

        #relinquish r2 to solve the deadlock
        replyBody = json.loads(self.helper_release_lock('r2', 'c3').data.decode('utf-8'))
        assert('error' not in replyBody)

        assert(p1.get() == True)
        assert(p2.get() == True)

if __name__ == '__main__':
    unittest.main()
