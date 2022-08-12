"""
A basic IGSN resolver implementation.

This service receives an IGSN identifier and looks up the target
address using the [hdl.handle.net API](http://www.handle.net/proxy_servlet.html),
then either redirects the client to the target or presents
basic metadata about the identifier.

Run me like: `uvicorn main:app --reload`
"""
import logging
import typing
import fastapi
import fastapi.responses
import fastapi.middleware.cors
import igsnresolve

L = logging.getLogger("resolver")

app = fastapi.FastAPI(
    title="IGSN Resolver",
    description=__doc__,
    version="0.1.0",
    contact={
        "name":"Dave Vieglais",
        "url": "https://github.com/datadavev/"
    },
    license_info={
        "name":"Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
    }
)
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=[
        "*",
    ],
    allow_headers=[
        "*",
    ],
)


@app.get("/favicon.ico")
async def favicon():
    raise fastapi.HTTPException(status_code=404)


@app.get("/info/{igsn}", response_model=igsnresolve.IGSNInfo)
async def igsn_info(
    igsn: str, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    info = await igsnresolve.resolveIgsn(igsn)
    return info


@app.get("/{igsn}")
async def resolve(
    igsn: str, request: fastapi.Request, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    try:
        info = await igsnresolve.resolveIgsn(igsn)
        if info.target is not None:
            headers = {
                "Link": f'</info/{info.normalized}>; rel="alternate"'
            }
            return fastapi.responses.RedirectResponse(info.target, headers=headers)
        raise fastapi.HTTPException(status_code=404, detail=dict(info))
    except Exception as e:
        L.exception(e)
        raise fastapi.HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def main_root():
    return fastapi.responses.RedirectResponse(url="/docs")
