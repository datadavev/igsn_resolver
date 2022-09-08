'''
Script to generate igsn_prefixes.json

This script gathers prefix entries from https://doidb.wdc-terra.org/igsn and generates a JSON file containing the same information.
'''

import json
import logging
import re
import click
import dateutil.parser
import httpx
import bs4

SERVICE_URL="https://doidb.wdc-terra.org/igsn/prefixeslists"
USER_AGENT="IGSNResolver/1.0.0"
DATE_FORMAT="%Y-%m-%d %H:%M "

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)s:%(levelname)s: %(message)s"

def getLogger():
    return logging.getLogger("gp")


def get_igsn_prefix_page(page:int=1, size:int=50)->str:
    L = getLogger()
    L.info("Retrieving page %s...", page)
    url = SERVICE_URL
    params = {
        "page": page,
        "size": size
    }
    headers = {
        "User-agent": USER_AGENT,
        "Accept": "application/json;q=0.9, */*;q=0.8"
    }    
    response = httpx.get(url, params=params, headers=headers)
    L.debug(response.url)
    if response.status_code not in [200, ]:
        raise ValueError("Unable to retrieve page:%s", page)
    return response.text

def parse_prefix_page(html_txt:str)->dict:
    L = getLogger()
    res = {"entries":[], "pages":0}
    soup = bs4.BeautifulSoup(html_txt, features="html.parser")
    try:
        table = soup.find("table")
        for row in table.find_all("tr"):
            entry = row.find_all("td")
            if len(entry) >= 3:
                res['entries'].append({
                    "prefix":entry[0].text,
                    "allocator":entry[1].text,
                    "date":dateutil.parser.parse(entry[2].text).isoformat()
                })
            elif len(entry) == 1:
                # last row, with pages
                txt = entry[0].text
                L.debug(txt)
                match = re.search(".*Page [0-9]{1,2} of ([0-9]{1,2})", txt)
                L.debug(match.groups())
                res["pages"] = int(match.group(1))
    except AttributeError as e:
        L.error(e)
        # reraise here to terminate app instead of continuing under error condition
        raise(e)
    return res

@click.command()
@click.option(
    "--loglevel", envvar="T_LOGLEVEL", default="INFO", help="Specify logging level", show_default=True
)
def main(loglevel):
    loglevel = loglevel.upper()
    logging.basicConfig(
        level=LOG_LEVELS.get(loglevel, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    results = []
    c_page = 1
    page_text = get_igsn_prefix_page(page=c_page)
    parsed = parse_prefix_page(page_text)
    results = parsed.get("entries", [])
    while c_page < parsed.get("pages", 0):
        c_page += 1
        page_text = get_igsn_prefix_page(page=c_page)
        parsed = parse_prefix_page(page_text)
        results += parsed.get("entries", [])
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()