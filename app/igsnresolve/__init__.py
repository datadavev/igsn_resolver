"""
An IGSN identifier resolver implementation.
Copyright (C) <2024>  Dave Vieglais

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
DATACITE_API = "https://api.datacite.org"
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
    messages: typing.List[str] = []
    metadata: typing.Optional[dict] = None
    _prefix: typing.Union[None, str] = pydantic.PrivateAttr(None)
    _value: typing.Union[None, str] = pydantic.PrivateAttr(None)

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
            #self._prefix = DEFAULT_PREFIX
            self._prefix = None
            self._value = parts[0]
        if self.scheme is None:
            #if self._prefix.startswith("10."):
            #    self.scheme = "doi"
            #else:
            self.scheme = "igsn"
        return self._prefix, self._value

    def normalize(self, v: str = None) -> (str, str):
        """
        Populates self.normalized and returns prefix, value
        """
        if v is not None and (self._value is None or self._prefix is None):
            self.parse(v=v)
        if self.handle is None or self.handle == '':
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

    async def resolve_datacite(self, client: httpx.AsyncClient, full_metadata:bool=False) -> bool:
        """
        Lookup the target for the provided original IGSN
        """
        if self._value is None or self._prefix is None:
            _ = self.parse()
        headers = {"Accept": "application/vnd.api+json"}
        params = {
            #"query": f"id:10.*/{self._value.lower()}",
            "query": f"suffix:{self._value.lower()}",
            "resource-type-id": "physical-object",
        }
        if not full_metadata:
            params["fields[dois]"] = "id,url,updated"
        url = f"{DATACITE_API}/dois"
        try:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                entries = data.get("data", [])
                if len(entries) == 0:
                    self.messages.append("Warning: no match found")
                    return False
                if len(entries) > 1:
                    self.messages.append("Warning: more than one match, returning first only")
                self.handle = entries[0].get("id", None)
                _parts = self.handle.split("/",1)
                if len(_parts) > 1:
                    self._prefix = _parts[0]
                self.target = entries[0].get("attributes", {}).get("url", None)
                self.timestamp = entries[0].get("attributes", {}).get("updated", None)
                self.normalize()
                if full_metadata:
                    self.metadata = entries[0]
                return True
        except Exception as e:
            self.messages.append(str(e))
        return False


async def resolve(igsn: typing.Union[str, IGSNInfo], full_metadata:bool=False) -> IGSNInfo:
    """
    Given an IGSN string or IGSNInfo instance, return
    a populated IGSNInfo structure.
    """
    if isinstance(igsn, str):
        info = IGSNInfo(original=igsn)
    else:
        info = igsn
    igsn.normalize()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if info._prefix is not None:
            _ = await info.resolve(client)
        else:
            _ = await info.resolve_datacite(client, full_metadata=full_metadata)
    return info


async def resolveIGSNs(igsn_strs: typing.List[str], full_metadata:bool=None) -> typing.List[IGSNInfo]:
    igsns = []
    for igsn_str in igsn_strs:
        igsns.append(IGSNInfo(original=igsn_str))
    client = httpx.AsyncClient(timeout=TIMEOUT)
    try:
        tasks = []
        for igsn in igsns:
            if igsn._prefix is not None:
                tasks.append(igsn.resolve(client))
            else:
                tasks.append(igsn.resolve_datacite(client, full_metadata=full_metadata))
        await asyncio.gather(*tasks)
    finally:
        await client.aclose()
    return igsns
