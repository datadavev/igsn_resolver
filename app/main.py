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
import urllib.parse
import fastapi
import fastapi.responses
import fastapi.middleware.cors
import opentelemetry.instrumentation.fastapi
import uptrace
import igsnresolve

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
L = logging.getLogger("resolver")

MAX_PER_REQUEST = 50
INFO_PROFILE = "https://igsn.org/info"
DATACITE_PROFILE = "https://schema.datacite.org/"
URL_SAFE_CHARS = ":/%#?=@[]!$&'()*+,;"
VERSION="0.6.0"
DELIMITER = ","

app = fastapi.FastAPI(
    title="IGSN Resolver",
    description=__doc__,
    version=VERSION,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
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
uptrace.configure_opentelemetry(service_name="igsn_resolver",service_version=VERSION)
opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app(app)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    raise fastapi.HTTPException(status_code=404)


@app.get("/", include_in_schema=False)
async def main_root():
    return fastapi.responses.RedirectResponse(url="/docs")


@app.get("/.info/{identifier:path}", response_model=typing.List[igsnresolve.IGSNInfo])
async def igsn_info(
    identifier: str, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    """
    Return info from the handle system about one or more IGSNs (delimited by semi-colon).

    A request with more than 50 identifiers raises a 400 error.
    """
    if identifier.count(DELIMITER) > MAX_PER_REQUEST:
        return fastapi.HTTPException(
            status_code=400, detail="Too many items in request"
        )
    identifier_strs = identifier.split(DELIMITER)
    return await igsnresolve.resolveIGSNs(identifier_strs)


@app.get("/{identifier:path}")
async def resolve(
    request: fastapi.Request,
    identifier: str,
    accept_profile: typing.Union[str, None] = fastapi.Header(default=None),
):
    """
    Resolve the provided IGSN and redirect to the target.

    If an `Accept-Profile` header with value `https://igsn.org/info` is provided,
    then this method behaves the same as a `/info/` request.

    If an `Accept-Profile` header with value `https://schema.datacite.org/` is provided,
    then the request is redirected to `hdl.handle.net`.
    """
    info = igsnresolve.IGSNInfo(original=identifier)
    prefix, value = info.normalize()
    url = urllib.parse.quote(f"https://hdl.handle.net/{prefix}/{value}", safe=URL_SAFE_CHARS)
    _link = [
        f'<{request.url}>; rel="canonical"',
        f'</.info/{info.normalized}>; type="application/json"; rel="alternate"; profile="{INFO_PROFILE}"',
        f'<{url}>; rel="alternate"; profile="{DATACITE_PROFILE}"',
    ]
    headers = {"Link": ", ".join(_link)}
    if accept_profile == DATACITE_PROFILE:
        # Redirect to handle system, which
        headers["Location"] = url
        return fastapi.responses.Response(
            content=info.json(),
            status_code=307,
            headers=headers,
            media_type="application/json",
        )
    try:
        info = await igsnresolve.resolve(info)
        if info.target is not None:
            if accept_profile == INFO_PROFILE:
                return fastapi.responses.JSONResponse(content=info, headers=headers)
            headers["Location"] = urllib.parse.quote(info.target, safe=URL_SAFE_CHARS)
            return fastapi.responses.Response(
                content=info.json(),
                status_code=307,
                headers=headers,
                media_type="application/json",
            )
        raise fastapi.HTTPException(status_code=404, detail=dict(info))
    except Exception as e:
        L.exception(e)
        raise fastapi.HTTPException(status_code=500, detail="Error processing request.")
