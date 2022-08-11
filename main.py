"""
Run me like: `uvicorn main:app --reload`
"""
import typing
import fastapi
import fastapi.responses
import fastapi.middleware.cors
import igsnresolve


app = fastapi.FastAPI()
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
    igsn: str, accept: typing.Union[str, None] = fastapi.Header(default=None)
):
    info = await igsnresolve.resolveIgsn(igsn)
    if info.target is not None:
        return fastapi.responses.RedirectResponse(info.target)
    raise fastapi.HTTPException(status_code=404, detail=dict(info))


@app.get("/")
async def main_root():
    return fastapi.responses.RedirectResponse(url="/docs")
