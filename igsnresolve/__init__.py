"""
Implements method for fetching the handle resolved target for an IGSN
"""
import typing
import httpx
import pydantic


class IGSNInfo(pydantic.BaseModel):
    original: str
    normalized: typing.Union[None, str] = None
    handle: typing.Union[None, str] = None
    target: typing.Union[None, str] = None
    ttl: typing.Union[None, int] = None
    timestamp: typing.Union[None, str] = None


def cleanIgsn(igsn: str) -> str:
    igsn = igsn.strip()
    igsn = igsn.upper()
    if igsn.startswith("10273/"):
        igsn = igsn.replace("10273/", "")
    if igsn.startswith("IGSN:"):
        igsn = igsn.replace("IGSN:", "")
        igsn = igsn.strip()
    return igsn


async def _resolveIgsn(client: httpx.AsyncClient, igsn: str) -> httpx.Response:
    """
    Info about the handle api is at: http://www.handle.net/proxy_servlet.html
    """
    headers = {"Accept": "application/json"}
    params = {"type": "URL"}
    base_url = "https://hdl.handle.net/api/handles/10273/"
    url = f"{base_url}{igsn}"
    return await client.get(url, headers=headers, params=params)


async def resolveIgsn(igsn: str) -> IGSNInfo:
    result = IGSNInfo(original=igsn)
    igsn = cleanIgsn(igsn)
    result.normalized = igsn
    async with httpx.AsyncClient() as client:
        response = await _resolveIgsn(client, igsn)
        if response.status_code == 200:
            info = response.json()
            if info.get("responseCode", 100) == 1:
                result.handle = info.get("handle", None)
                vals = info.get("values", [])
                if len(vals) < 1:
                    return result
                result.target = vals[0].get("data", {}).get("value", None)
                result.ttl = vals[0].get("ttl", None)
                result.timestamp = vals[0].get("timestamp", None)
    return result
