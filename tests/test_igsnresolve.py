"""
Tests for the igsnresolve lib

Ensure that the app folder is on your python path.
"""

import os
import sys
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"../app")
sys.path.append(app_path)

import pytest
import httpx
import igsnresolve


@pytest.mark.parametrize("v,ex",[
    ("au1243", ("10273", "AU1243")),
    ("igsn:au1243", ("10273", "AU1243")),
    ("10273/au1243", ("10273", "AU1243")),
    ("igsn:10273/au1243", ("10273", "AU1243")),
    ("igsn: 10273/au1243", ("10273", "AU1243")),
    ("igsn:1111/au1243", ("1111", "AU1243")),
])
def test_IGSNInfo_parse(v, ex):
    igsn = igsnresolve.IGSNInfo(original=v)
    prefix, value = igsn.parse()
    assert prefix == ex[0]
    assert value == ex[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("v,ex",[
    ("au1243", "http://pid.geoscience.gov.au/sample/AU1243"),
    ("igsn:au1243", "http://pid.geoscience.gov.au/sample/AU1243",),
    ("10273/au1243", "http://pid.geoscience.gov.au/sample/AU1243",),
    ("igsn:10273/au1243", "http://pid.geoscience.gov.au/sample/AU1243",),
    ("igsn: 10273/au1243", "http://pid.geoscience.gov.au/sample/AU1243",),
    ("igsn:1111/au1243", None),
])
async def test_IGSNInfo_resolve(v, ex):
    igsn = igsnresolve.IGSNInfo(original=v)
    async with httpx.AsyncClient(timeout=1.0) as client:
        res = await igsn.resolve(client)
        assert igsn.target == ex


@pytest.mark.asyncio
@pytest.mark.parametrize("v,ex",[
        (
            (
                "au1243",
                "igsn:au1243",
                "10273/au1243",
                "igsn:10273/au1243",
                "igsn: 10273/au1243",
                "igsn:1111/au1243"
            ),
            (
                "http://pid.geoscience.gov.au/sample/AU1243",
                "http://pid.geoscience.gov.au/sample/AU1243",
                "http://pid.geoscience.gov.au/sample/AU1243",
                "http://pid.geoscience.gov.au/sample/AU1243",
                "http://pid.geoscience.gov.au/sample/AU1243",
                None
            )
        )
    ]
)
async def test_IGSNInfo_resolvemany(v, ex):
    res = await igsnresolve.resolveIGSNs(v)
    for i in range(0, len(v)):
        assert res[i].target == ex[i]

