"""
Implements method for fetching the handle system resolved target for an IGSN
"""
import asyncio
import logging
import typing
import httpx
import pydantic

import time

TIMEOUT = 2.0 #seconds
DEFAULT_PREFIX = "10273"
HANDLE_API = "https://hdl.handle.net/api/handles/"

L = logging.getLogger("igsnresolve")


class IGSNInfo(pydantic.BaseModel):
    original: str
    normalized: typing.Union[None, str] = None
    handle: typing.Union[None, str] = None
    target: typing.Union[None, str] = None
    ttl: typing.Union[None, int] = None
    timestamp: typing.Union[None, str] = None

    def parse(self, v:str = None) -> (str, str):
        """
        Given an IGSN string, try and parse it into prefix, value

        Uses self.original if v is not provided.
        """
        if v is None:
            v = self.original
        L.debug("parse: %s", v)
        igsn = v.strip()
        igsn = igsn.upper()
        if igsn.startswith("IGSN:"):
            igsn = igsn.replace("IGSN:", "")
            igsn = igsn.strip()
        parts = igsn.split("/", 1)
        if len(parts) > 1:
            return parts
        return DEFAULT_PREFIX, igsn

    def normalize(self) -> (str, str):
        """
        Populates self.normalized and returns prefix, value
        """
        p, v = self.parse()
        self.handle = f"{p}/{v}"
        self.normalized = f"IGSN:{self.handle}"
        return p, v

    async def resolve(self, client:httpx.AsyncClient)->bool:
        """
        Lookup the target for the provided original IGSN
        """
        prefix, value = self.normalize()
        headers = {"Accept": "application/json"}
        params = {"type": "URL"}
        url = f"{HANDLE_API}{prefix}/{value}"
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


async def resolveIgsn(igsn_str: str) -> IGSNInfo:
    """
    Given an IGSN string, return a populated IGSNInfo structure.
    """
    igsn = IGSNInfo(original=igsn_str)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        res = await igsn.resolve(client)
    return igsn


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
