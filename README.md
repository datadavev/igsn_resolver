# igsn_resolver

Performs IGSN resolution by leveraging the Handle System API.

`igsn_resolver` provides a simple proof of concept for an IGSN resolver service implemented using [FastAPI](https://fastapi.tiangolo.com/), and using the [handle.net](https://handle.net/proxy_servlet.html) resolution infrastructure while supporting expected behavior of content negotiation for RDF resource in anticipation of the migration of IGSN to DOI infrastructure hosted by [DataCite](https://datacite.org/).

![Context Diagram](https://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/datadavev/igsn_resolver/main/UML/context.puml)

The service is composed of two components, the API which performs the resolution functions, and a minimal Web UI implemented as a Web Component. The UI component has minimal dependencies and may be deployed in any HTML page.

![Container Diagram](https://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/datadavev/igsn_resolver/main/UML/container.puml)


A test instance of the API is deployed on [Deta](https://www.deta.sh/) at [https://ule1dz.deta.dev/](https://ule1dz.deta.dev/). The UI is deployed using GitHub pages, available at [https://datadavev.github.io/igsn_resolver/](https://datadavev.github.io/igsn_resolver/).


The API supports two endpoints, one for redirection, the other for basic metadata. These methods are described in the API documenation at [https://ule1dz.deta.dev/docs](https://ule1dz.deta.dev/docs) with some examples below.

Identifiers are provided as strings, and the service will attempt to normalize a provided identifier string prior to lookup. Examples of IGSN identifier strings that are recognized include:

```
au1234
AU1234
igsn:au1234
10273/au1234
igsn:10273/au1234
```

Since the service is using the handle system under the hood, DOI idnetifier strings are also accepted, for example:

```
10.1594/PANGAEA.930327
doi:10.1594/PANGAEA.930327
```


### `/.info/{identifier}`

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

Where:
<dl>
  <dt><code>original</code></dt><dd>The provided identifier string.</dd>
  <dt><code>scheme</code></dt><dd>Recognized identifier scheme, either "igsn" or "doi".</dd>
  <dt><code>normalized</code></dt><dd>Normalized representation of the identifier string.</dd>
  <dt><code>handle</code></dt><dd>Handle representation of the identifier string.</dd>
  <dt><code>target</code></dt><dd>Identifier targer as reported by the Handle System.</dd>
  <dt><code>ttl</code></dt><dd>Time to live in seconds, reported by the Handle System.</dd>
  <dt><code>timestamp</code></dt><dd>The entry timestamp as reported by the Handle System.</dd>
</dl>

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

### `/{identifier}`

The resolve endpoint `/{identifier}` accepts a single identifier string and returns a redirect (status code 307) to the target address listed by the handle system. For example:
```
curl -v -q "https://ule1dz.deta.dev/au1234"
...
< HTTP/1.1 307 Temporary Redirect
< Link: 
    <https://ule1dz.deta.dev/au1234>; 
        rel="canonical", 
    </.info/igsn:10273/au1234>; 
        type="application/json"; 
        rel="alternate"; 
        profile="https://igsn.org/info", 
    <https://hdl.handle.net/au1234/10273>; 
        rel="alternate"; 
        profile="https://schema.datacite.org/"
< Location: http://www.ga.gov.au/sample-catalogue/10273/AU1234
```
Note the `Link` header response which provides a hint to the client about alternate locations and profiles for accessing information about the identified resource as described below.

The behavior of this method can be modified by an optional `Accept-Profile` header[^1] sent by the client. 

[^1]: Content Negotiation by Profile is currently a W3C draft, https://www.w3.org/TR/dx-prof-conneg/ 

If the client includes an `Accept-Profile` header of `https://igsn.org/info` the response is the same as a call to the `/.info/{identifier}` endpoint. For example:

```
curl -q -H "Accept-Profile: https://igsn.org/info" \
  "https://ule1dz.deta.dev/au1234"
...
{
  "original": "au1234",
  "scheme": "igsn",
  "normalized": "igsn:10273/au1234",
  "handle": "10273/au1234",
  "target": "http://www.ga.gov.au/sample-catalogue/10273/AU1234",
  "ttl": 86400,
  "timestamp": "2015-07-22T05:19:38Z"
}
```

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
< Link: 
    <https://ule1dz.deta.dev/10.1594/PANGAEA.930327>; 
        rel="canonical", 
    </.info/doi:10.1594/PANGAEA.930327>; 
        type="application/json"; 
        rel="alternate"; 
        profile="https://igsn.org/info", 
    <https://hdl.handle.net/PANGAEA.930327/10.1594>; 
        rel="alternate"; 
        profile="https://schema.datacite.org/"
< Location: https://doi.pangaea.de/10.1594/PANGAEA.930327
```

The DataCite metadata may be retrieved by specifically requesting that format:

```
curl -q -v -H "Accept: application/ld+json" \
  -H "Accept-Profile: https://schema.datacite.org/" \
  "https://ule1dz.deta.dev/10.1594/PANGAEA.930327"
...
< HTTP/1.1 307 Temporary Redirect
< Link: 
    <https://ule1dz.deta.dev/10.1594/PANGAEA.930327>; 
        rel="canonical", 
    </.info/doi:10.1594/PANGAEA.930327>; 
        type="application/json"; 
        rel="alternate"; 
        profile="https://igsn.org/info", 
    <https://hdl.handle.net/PANGAEA.930327/10.1594>; 
        rel="alternate"; 
        profile="https://schema.datacite.org/"
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

A push to `main` on the origin repo will result in a re-deployment to `deta.sh` and deployment of the web interface to GitHub pages.

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

The web component is in the `identifier-resolver` folder. It is implemented in Javascript using [Lit](https://lit.dev/docs/) and may be deployed without building or bundling. See the [`README`](identifier-resolver/README.md) in that folder for details.
