"""
A basic IGSN resolver implementation.

This service receives an IGSN identifier and looks up the target
address using the [hdl.handle.net API](http://www.handle.net/proxy_servlet.html),
then either redirects the client to the target or presents
basic metadata about the identifier.

Run me like: `uvicorn main:app --reload`
"""
import logging.config
import typing
import fastapi
import fastapi.responses
import fastapi.middleware.cors
import igsnresolve

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
L = logging.getLogger("resolver")

MAX_PER_REQUEST = 50
INFO_PROFILE = "https://igsn.org/info"
DATACITE_PROFILE = "https://schema.datacite.org/"

app = fastapi.FastAPI(
    title="IGSN Resolver",
    description=__doc__,
    version="0.3.0",
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

@app.get("/")
async def main_root():
    return fastapi.responses.RedirectResponse(url="/docs")


@app.get("/info/{igsn:path}", response_model=igsnresolve.IGSNInfo)
async def igsn_info(
    igsn: str, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    """
    Return info about an IGSN from the handle system
    """
    info = await igsnresolve.resolveIgsn(igsn)
    return info


@app.get("/infos/{igsn_str:path}")
async def igsn_info(
    igsn_str: str, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    """
    Return info from the handle system about one or more IGSNs (delimited by semi-colon).

    A request with more than 50 identifiers raises a 400 error.
    """
    if igsn_str.count(";") > MAX_PER_REQUEST:
        return fastapi.HTTPException(status_code=400, detail="Too many items in request")
    igsn_strs = igsn_str.split(";")
    return await igsnresolve.resolveIGSNs(igsn_strs)


@app.get("/{igsn:path}")
async def resolve(
    igsn: str, accept_profile: typing.Union[str, None] = fastapi.Header(default=None)
):
    """
    Resolve the provided IGSN and redirect to the target.

    If an `Accept-Profile` header with value `https://igsn.org/info` is provided,
    then this method behaves the same as a `/info/` request.

    If an `Accept-Profile` header with value `https://schema.datacite.org/` is provided,
    then the request is redirected to `hdl.handle.net`.
    """
    if accept_profile == DATACITE_PROFILE:
        info = igsnresolve.IGSNInfo(original=igsn)
        prefix, value = info.parse()
        url = f"https://hdl.handle.net/{prefix}/{value}"
        _link = [
            f'<{info.target}>; rel="canonical"',
            f'</info/{info.normalized}>; type="application/json"; rel="alternate"; profile="{INFO_PROFILE}"',
            f'<{url}>; rel="alternate" profile="{DATACITE_PROFILE}"',
        ]
        headers = {
            "Link": ", ".join(_link)
        }
        return fastapi.responses.RedirectResponse(url, headers=headers)
    try:
        info = await igsnresolve.resolveIgsn(igsn)
        if info.target is not None:
            _link = [
                f'<{info.target}>; rel="canonical"',
                f'</info/{info.normalized}>; type="application/json"; rel="alternate"; profile="{INFO_PROFILE}"',
                f'<https://hdl.handle.net/{info.handle}>; rel="alternate" profile="{DATACITE_PROFILE}"',
            ]
            headers = {
                "Link": ", ".join(_link)
            }
            if accept_profile == INFO_PROFILE:
                return info
            return fastapi.responses.RedirectResponse(info.target, headers=headers)
        raise fastapi.HTTPException(status_code=404, detail=dict(info))
    except Exception as e:
        L.exception(e)
        raise fastapi.HTTPException(status_code=500, detail="Error processing request.")



