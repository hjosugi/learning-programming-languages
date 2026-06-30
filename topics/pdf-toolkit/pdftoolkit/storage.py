"""Where files come from and go back to -- local disk or Google Drive.

The web app talks to a *storage provider* through three methods -- ``list``,
``read``, ``write`` -- so "open a file" and "save the edit" work the same
whether the bytes live on disk or in Drive. Two providers ship here:

* :class:`LocalStorage` -- PDFs in a folder.
* :class:`DriveStorage` -- Google Drive over its REST API using **only**
  ``urllib`` (no Google SDK). It needs an OAuth2 access token with a Drive
  scope; everything else (list / download / upload-in-place) is plain HTTPS.

Keeping Drive to stdlib ``urllib`` is deliberate: the toolkit stays
dependency-free, and "smooth Drive connection" becomes a token away rather than
a pile of client libraries.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request


class LocalStorage:
    kind = "local"

    def __init__(self, root: str):
        import os
        self.root = os.path.abspath(root)

    def list(self):
        import os
        out = []
        for name in sorted(os.listdir(self.root)):
            if name.lower().endswith(".pdf") and os.path.isfile(os.path.join(self.root, name)):
                out.append({"id": name, "name": name})
        return out

    def read(self, file_id: str) -> bytes:
        with open(self._safe(file_id), "rb") as fh:
            return fh.read()

    def write(self, file_id: str, data: bytes) -> str:
        with open(self._safe(file_id), "wb") as fh:
            fh.write(data)
        return file_id

    def _safe(self, file_id: str) -> str:
        import os
        # never escape the root: collapse to a basename
        return os.path.join(self.root, os.path.basename(file_id))


class DriveStorage:
    """Google Drive via REST + ``urllib``.

    ``opener`` defaults to :func:`urllib.request.urlopen` and exists so tests
    can inject a fake transport.
    """

    kind = "drive"
    API = "https://www.googleapis.com/drive/v3"
    UPLOAD = "https://www.googleapis.com/upload/drive/v3"

    def __init__(self, token: str, opener=None):
        self.token = token
        self._open = opener or urllib.request.urlopen

    def _request(self, url, data=None, method=None, headers=None):
        merged = {"Authorization": f"Bearer {self.token}"}
        merged.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=merged)
        return self._open(req)

    def list(self):
        query = urllib.parse.urlencode(
            {
                "q": "mimeType='application/pdf' and trashed=false",
                "fields": "files(id,name)",
                "pageSize": "100",
                "orderBy": "modifiedTime desc",
            }
        )
        with self._request(f"{self.API}/files?{query}") as resp:
            files = json.loads(resp.read().decode("utf-8")).get("files", [])
        return [{"id": f["id"], "name": f["name"]} for f in files]

    def read(self, file_id: str) -> bytes:
        url = f"{self.API}/files/{urllib.parse.quote(file_id)}?alt=media"
        with self._request(url) as resp:
            return resp.read()

    def write(self, file_id: str, data: bytes) -> str:
        # Update the existing file's bytes in place (uploadType=media + PATCH).
        url = f"{self.UPLOAD}/files/{urllib.parse.quote(file_id)}?uploadType=media"
        with self._request(url, data=data, method="PATCH",
                           headers={"Content-Type": "application/pdf"}) as resp:
            resp.read()
        return file_id
