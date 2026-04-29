SlowApi
A rate limiting library for Starlette and FastAPI adapted from flask-limiter.

Note: this is alpha quality code still, the API may change, and things may fall apart while you try it.

Quick start
Installation
slowapi is available from pypi so you can install it as usual:

$ pip install slowapi
Starlette
    from starlette.applications import Starlette
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app = Starlette()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @limiter.limit("5/minute")
    async def homepage(request: Request):
        return PlainTextResponse("test")

    app.add_route("/home", homepage)
The above app will have a route t1 that will accept up to 5 requests per minute. Requests beyond this limit will be answered with an HTTP 429 error, and the body of the view will not run.

FastAPI
    from fastapi import FastAPI
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Note: the route decorator must be above the limit decorator, not below it
    @app.get("/home")
    @limiter.limit("5/minute")
    async def homepage(request: Request):
        return PlainTextResponse("test")

    @app.get("/mars")
    @limiter.limit("5/minute")
    async def homepage(request: Request, response: Response):
        return {"key": "value"}
This will provide the same result, but with a FastAPI app.

Features
Most feature are coming from (will come from) FlaskLimiter and the underlying limits.

Supported now:

Single and multiple limit decorator on endpoint functions to apply limits
redis, memcached and memory backends to track your limits (memory as a fallback)
support for sync and async HTTP endpoints
Support for shared limits across a set of routes
Support for default global limit
Limitations and known issues
Request argument
The request argument must be explicitly passed to your endpoint, or slowapi won't be able to hook into it. In other words, write:

    @limiter.limit("5/minute")
    async def myendpoint(request: Request)
        pass
and not:

    @limiter.limit("5/minute")
    async def myendpoint()
        pass
Response type
Similarly, if the returned response is not an instance of Response and will be built at an upper level in the middleware stack, you'll need to provide the response object explicitly if you want the Limiter to modify the headers (headers_enabled=True):

@limiter.limit("5/minute")
async def myendpoint(request: Request, response: Response)
return {"key": "value"}
Decorators order
The order of decorators matters. It is not a bug, the limit decorator needs the request argument in the function it decorates (see above). This works

@router.get("/test")
@limiter.limit("2/minute")
async def test(
    request: Request
):
return "hi"
but this doesnt

@limiter.limit("2/minute")
@router.get("/test")
async def test(
    request: Request
):
return "hi"

Examples
Here are some examples of setup to get you started. Please open an issue if you have a use case that is not included here.

The tests show a lot of different use cases that are not all covered here.

Apply a global (default) limit to all routes
    from starlette.applications import Starlette
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["1/minute"])
    app = Starlette()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # this will be limited by the default_limits
    async def homepage(request: Request):
        return PlainTextResponse("Only once per minute")

    app.add_route("/home", homepage)
Exempt a route from the global limit
    @app.route("/someroute")
    @limiter.exempt
    def t(request: Request):
        return PlainTextResponse("I'm unlimited")
Disable the limiter entirely
You might want to disable the limiter, for instance for testing, etc... Note that this disables it entirely, for all users. It is essentially as if the limiter was not there. Simply pass enabled=False to the constructor.

    limiter = Limiter(key_func=get_remote_address, enabled=False)

    @app.route("/someroute")
    @limiter.exempt
    def t(request: Request):
        return PlainTextResponse("I'm unlimited")
You can always switch this during the lifetime of the limiter:

    limiter.enabled = False
Use redis as backend for the limiter
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://<host>:<port>/n")
where the /n in the redis url is the database number. To use the default one, just drop the /n from the url.

There are more examples in the limits docs which is the library slowapi uses to manage storage.