"""Download the full text of the 10 US Congress documents from govinfo.gov.

The external database holds only each document's title and length and short
snippets around each name. This script saves the full pages, so the texts can
be split into paragraphs and searched for the topics Congress investigated.

Each document is one HTML page at
    https://www.govinfo.gov/content/pkg/<doc_id>/html/<doc_id>.htm
with doc_id taken from the congress_documents table. Pages already downloaded
are skipped, and there is a pause between requests to be gentle on the server.

Usage (from the project root; needs an internet connection):
    uv run python -m enron.download_congress

Output: data/external/congress/<doc_id>.htm, and a check that each page's text
length is close to n_chars in congress_documents.
"""

import html
import re
import time
import urllib.request
from contextlib import closing

import pandas as pd

from enron.loaders import connect
from enron.paths import DATA_DIR

OUT = DATA_DIR / "external" / "congress"
URL = "https://www.govinfo.gov/content/pkg/{doc_id}/html/{doc_id}.htm"
PAUSE_SECONDS = 2


def page_text(raw: str) -> str:
    """The readable text of a govinfo page: tags removed, entities decoded."""
    return html.unescape(re.sub(r"<[^>]+>", "", raw))


def download(doc_id: str) -> str:
    request = urllib.request.Request(URL.format(doc_id=doc_id),
                                     headers={"User-Agent": "DTU course project (02805)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as conn:
        docs = pd.read_sql("SELECT doc_id, title, n_chars FROM ext.congress_documents ORDER BY doc_id",
                           conn)

    for doc in docs.itertuples():
        path = OUT / f"{doc.doc_id}.htm"
        if not path.exists():
            print(f"Downloading {doc.doc_id} ...")
            path.write_text(download(doc.doc_id), encoding="utf-8")
            time.sleep(PAUSE_SECONDS)
        n = len(page_text(path.read_text(encoding="utf-8")))
        diff = 100 * (n - doc.n_chars) / doc.n_chars
        print(f"{doc.doc_id}: {n:,} characters (expected {doc.n_chars:,}, {diff:+.1f}%)  {doc.title}")

    print(f"Saved to {OUT}")


if __name__ == "__main__":
    main()
