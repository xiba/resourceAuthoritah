##Resource Authoritah is a centralized resource lock manager.

####We should respect it; and its authority.

#####Description of the service and the API:
This is a basic flask web service. It only accepts/responds with application/json content. At the heart of it lies **Redis.set(name=fResourceName, value=fID, nx=True, ex=fExpiry)**  

The entire thing is testable through vanilla python *unittest* (**python testFlaskApp.py**).  

Three operations are offered through different methods on the same url:  

1. '/resources/\<fResourceName\>', methods=['GET']  

    If fResourceName is a currently locked resource, returns **fResourceName:locked** in the response body (json, remember).  

    Else, it returns **fResourceName:free**  

2. '/resources/\<fResourceName\>', methods=['POST']  

    Expects an **id** in the request, denoting the identity of the client. Maintaining it is currently the client's responsibility (bad decision).  

    Expects two optional fields, **timeout** and **expiry**.    

    **expiry** denotes the TTL for the lock (locks expire after a while in case the owners die) (value clamped to [1, 120], returns an error on invalid values).  

    **timeout** how much time should be spent retrying to acquire the lock if it's not free.  

    Returns an error field in the response body (json, remember) if it fails to acquire the lock.  

3. '/resources/\<fResourceName\>', methods=['DELETE']  

    Expects an **id** in the request, denoting the identity of the client. Must be the same **id** the resource was locked with (primitive authorization and to avoid a client releasing a resource that it used to own).  

    Returns an error field in the response body if the resource isn't locked with that id.


####Deployment and dependencies:
Deployment was given the least priority (given the simplicity of the app and the context of its development).  

Dependencies are:  

1. redis  
2. flask  
3. py-redis  


####TODO (ordered):  

- Deadlock detection (in progress on branch **deadlock-detection**, with a bug cornered but not yet squashed)
- Resource names should be moved to request bodies to allow for arbitrary binary names (or we can keep them in the url but make sure to encode them first (size limit tho))
- Error codes should be standardized
- Expiry dates should be sent back as portable timestamps and not just as request offsets (to account for lost time till they're set)
- Client IDs should be generated and signed on the server
- The json pseudo-protocol we're using should be documented inside the app and testable
- Look into Redis connection handling (global instance or create every time or pool them or what)
- Redis connections should be configurable through the app's configuration
- Redis db should have authentication
- Profile performance
- Figure out deployment (docker maybe? initial draft on branch **dockerDeployment**)
- Turn the project from a centralized lock manager to a distributed one (check **redlock**)
