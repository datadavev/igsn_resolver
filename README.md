# igsn_resolver

Performs IGSN resolution by leveraging the Handle System API.

![Context Diagram](https://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/datadavev/igsn_resolver/main/UML/context.puml)

Provides a proof of concept for a simple IGSN resolver service implemented using [FastAPI](https://fastapi.tiangolo.com/) and deployable to [deta.sh](https://www.deta.sh/).

A test instance is deployed at [https://ule1dz.deta.dev/](https://ule1dz.deta.dev/). It supports two endpoints, one for redirection, the other for basic metadata. These are described in the API documenation at [https://ule1dz.deta.dev/docs](https://ule1dz.deta.dev/docs).

IGSN identifier strings may be formatted like:

```
au1234
AU1234
igsn:au1234
10273/au1234
igsn:10273/au1234
```

The service will also accept DOIs identifier strings, for example:

```
10.1594/PANGAEA.930327
doi:10.1594/PANGAEA.930327
```

The `/.info/{identifier}` endpoint will return metadata from the handle system about the identifier. For example:

```
curl "https://ule1dz.deta.dev/.info/au1234" | jq '.'
[
  {
    "original": "au1234",
    "scheme": "igsn",
    "normalized": "igsn:10273/au1234",
    "handle": "10273/au1234",
    "target": "http://www.ga.gov.au/sample-catalogue/10273/AU1234",
    "ttl": 86400,
    "timestamp": "2015-07-22T05:19:38Z"
  }
]
```

Multiple identifiers (up to 50) may be sent to the `/.info/` endpoint using a semi-colon as a delimiter. For example:

```
curl "https://ule1dz.deta.dev/.info/au1234;10.1594/PANGAEA.930327" | jq '.'
[
  {
    "original": "au1234",
    "scheme": "igsn",
    "normalized": "igsn:10273/au1234",
    "handle": "10273/au1234",
    "target": "http://www.ga.gov.au/sample-catalogue/10273/AU1234",
    "ttl": 86400,
    "timestamp": "2015-07-22T05:19:38Z"
  },
  {
    "original": "10.1594/PANGAEA.930327",
    "scheme": "doi",
    "normalized": "doi:10.1594/PANGAEA.930327",
    "handle": "10.1594/PANGAEA.930327",
    "target": "https://doi.pangaea.de/10.1594/PANGAEA.930327",
    "ttl": 86400,
    "timestamp": "2021-06-10T01:14:56Z"
  }
]
```

The resolve endpoint `/{identifier}` accepts a single identifier string and returns a redirect (status code 307) to the target address listed by the handle system. The behavior of this method can be modified by an optional `Accept-Profile` header sent by the client.

If the client includes an `Accept-Profile` header of `https://igsn.org/.info` the response is the same as a call to the `/.info/{identifier}` endpoint.

If the client includes an `Accept-Profile` header of `https://schema.datacite.org/` then the redirect response is to the handle system resolve address, which will subsequently return a redirect to the known target.

This approach enables correct resolution of some resource content types (such as RDF formats) in the DOI system which otherwise return metadata about the identifier rather than the identified resource. The IGSN infrastructure is in the process of migrating to using DOI infrastructure provided by DataCite, and a service such as this will be necessary for correct resolution of IGSN identifiers when that change is implemented.

For example, the DOI identifier `doi:10.1594/PANGAEA.930327` has a target of `https://doi.pangaea.de/10.1594/PANGAEA.930327`. Resolving this with the handle system for a content type of `text/html` results in the expected redirect:

```
curl -q -v -H "Accept: text/html" "https://hdl.handle.net/10.1594/PANGAEA.930327"
...
< HTTP/2 302
< vary: Accept
< location: https://doi.pangaea.de/10.1594/PANGAEA.930327
```

If instead a content-type of `application/ld+json` is requested, the location of DataCite metadata is returned instead of the identified resource:

```
curl -q -v -H "Accept: application/ld+json" "https://hdl.handle.net/10.1594/PANGAEA.930327"
...
< HTTP/2 302
< vary: Accept
< location: https://data.crosscite.org/10.1594%2FPANGAEA.930327
```

Resolving the same identifier with this `igsn-resolver` service results in the expected location:

```
curl -q -v -H "Accept: application/ld+json" "https://ule1dz.deta.dev/10.1594/PANGAEA.930327"
...
< HTTP/1.1 307 Temporary Redirect
< Link: <https://ule1dz.deta.dev/10.1594/PANGAEA.930327>; rel="canonical", </.info/doi:10.1594/PANGAEA.930327>; type="application/json"; rel="alternate"; profile="https://igsn.org/info", <https://hdl.handle.net/PANGAEA.930327/10.1594>; rel="alternate" profile="https://schema.datacite.org/"
< Location: https://doi.pangaea.de/10.1594/PANGAEA.930327
```
(note the `Link` header response which provides a hint to the client about alternate locations and profiles for accessing information about the identified resource).

The DataCite metadata can still be retrieved by specifically requesting that format:

```
curl -q -v -H "Accept: application/ld+json" \
  -H "Accept-Profile: https://schema.datacite.org/" \
  "https://ule1dz.deta.dev/10.1594/PANGAEA.930327"
...
< HTTP/1.1 307 Temporary Redirect
< Link: <https://ule1dz.deta.dev/10.1594/PANGAEA.930327>; rel="canonical", </.info/doi:10.1594/PANGAEA.930327>; type="application/json"; rel="alternate"; profile="https://igsn.org/info", <https://hdl.handle.net/PANGAEA.930327/10.1594>; rel="alternate" profile="https://schema.datacite.org/"
< Location: https://hdl.handle.net/PANGAEA.930327/10.1594  
```

## Development

After cloning this repo, create a virtual environment and install development dependencies:

```
pip install -r dev_requirements.txt
```

Then run a local instance on port 8000 by:
```
cd app
uvicorn main:app --reload
```

A push to `main` on the origin repo will result in a re-deployment to `deta.sh`.

Tests can be run with `pytest`, e.g.:

```
pytest
================================ test session starts =================================
platform darwin -- Python 3.10.5, pytest-7.1.2, pluggy-1.0.0
rootdir: /Users/vieglais/Documents/Projects/IGSN/igsn_resolver
plugins: anyio-3.6.1, asyncio-0.19.0
asyncio: mode=strict
collected 13 items

tests/test_igsnresolve.py .............                                        [100%]

================================= 13 passed in 1.33s =================================
```
