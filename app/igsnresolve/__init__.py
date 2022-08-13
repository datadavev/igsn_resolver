"""
Implements method for fetching the handle system resolved target for an IGSN
"""
import asyncio
import logging
import typing
import re
import httpx
import pydantic


TIMEOUT = 2.0  # seconds
DEFAULT_PREFIX = "10273"
HANDLE_API = "https://hdl.handle.net/api/handles/"
SCHEME_PATTERN = re.compile("^([\w]{2,4}):", re.IGNORECASE)

L = logging.getLogger("igsnresolve")


class IGSNInfo(pydantic.BaseModel):
    original: str
    scheme: typing.Union[None, str] = None
    normalized: typing.Union[None, str] = None
    handle: typing.Union[None, str] = None
    target: typing.Union[None, str] = None
    ttl: typing.Union[None, int] = None
    timestamp: typing.Union[None, str] = None
    _prefix: typing.Union[None, str] = None
    _value: typing.Union[None, str] = None

    class Config:
        underscore_attrs_are_private = True

    def parse(self, v: str = None) -> (str, str):
        """
        Given an IGSN string, try and parse it into prefix, value

        Uses self.original if v is not provided.
        """
        if v is None:
            if self._value is not None and self._prefix is not None:
                return self._prefix, self._value
        if v is not None:
            self.original = v
        identifier = self.original.strip()
        _scheme_match = SCHEME_PATTERN.match(identifier)
        if _scheme_match is not None:
            self.scheme = _scheme_match.group(1)
            self.scheme = self.scheme.lower()
            identifier = identifier[_scheme_match.end() :]
            identifier = identifier.strip()
        parts = identifier.split("/", 1)
        if len(parts) > 1:
            self._prefix = parts[0]
            self._value = parts[1]
        else:
            self._prefix = DEFAULT_PREFIX
            self._value = parts[0]
        if self.scheme is None:
            if self._prefix.startswith("10."):
                self.scheme = "doi"
            else:
                self.scheme = "igsn"
        return self._prefix, self._value

    def normalize(self, v: str = None) -> (str, str):
        """
        Populates self.normalized and returns prefix, value
        """
        if self._value is None or self._prefix is None:
            self.parse(v=v)
        self.handle = f"{self._prefix}/{self._value}"
        self.normalized = f"{self.scheme}:{self.handle}"
        return self._value, self._prefix

    async def resolve(self, client: httpx.AsyncClient) -> bool:
        """
        Lookup the target for the provided original IGSN
        """
        if self._value is None or self._prefix is None:
            _ = self.normalize()
        headers = {"Accept": "application/json"}
        params = {"type": "URL"}
        url = f"{HANDLE_API}{self._prefix}/{self._value}"
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            info = response.json()
            if info.get("responseCode", 100) == 1:
                self.handle = info.get("handle", None)
                vals = info.get("values", [])
                if len(vals) < 1:
                    return False
                self.target = vals[0].get("data", {}).get("value", None)
                self.ttl = vals[0].get("ttl", None)
                self.timestamp = vals[0].get("timestamp", None)
        return True

async def resolve(igsn: typing.Union[str, IGSNInfo]) -> IGSNInfo:
    """
    Given an IGSN string or IGSNInfo instance, return
    a populated IGSNInfo structure.
    """
    if isinstance(igsn, str):
        info = IGSNInfo(original=igsn)
    else:
        info = igsn
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        _ = await info.resolve(client)
    return info


async def resolveIGSNs(igsn_strs: typing.List[str]) -> typing.List[IGSNInfo]:
    igsns = []
    for igsn_str in igsn_strs:
        igsns.append(IGSNInfo(original=igsn_str))
    client = httpx.AsyncClient(timeout=TIMEOUT)
    try:
        tasks = []
        for igsn in igsns:
            tasks.append(igsn.resolve(client))
        await asyncio.gather(*tasks)
    finally:
        await client.aclose()
    return igsns
