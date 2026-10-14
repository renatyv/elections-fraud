"""HTTP client on httpx2 with retries and forced IPv4."""

import socket
import time

import httpx2

from sloref.config import BASE_URL

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HTTP_TIMEOUT = 30.0
RETRIES = 3
RETRY_DELAY = 5.0  # s, grows with the attempt number
TRANSPORT_RETRIES = 2  # httpx2 retry at the connection level


def force_ipv4() -> None:
    """The *.gov.si / dvk-rs.si sites drop some IPv6 TLS handshakes from
    outside EU/CIS networks; resolve addresses to IPv4 only."""
    orig = socket.getaddrinfo

    def ipv4_only(*args, **kwargs):
        return [r for r in orig(*args, **kwargs) if r[0] == socket.AF_INET] or \
               orig(*args, **kwargs)

    socket.getaddrinfo = ipv4_only


class FetchError(RuntimeError):
    """Failed to download the file after all retries."""


def build_client() -> httpx2.Client:
    return httpx2.Client(
        base_url=BASE_URL,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        transport=httpx2.HTTPTransport(retries=TRANSPORT_RETRIES),
        follow_redirects=True,
    )


def fetch(client: httpx2.Client, path: str) -> bytes | None:
    """GET <BASE_URL>/<path> with retries.

    Returns the content, None on 404 (file not published yet),
    FetchError on any other network/HTTP error.
    """
    last_exc: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = client.get(f"/{path}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content
        except httpx2.HTTPError as e:
            last_exc = e
        if attempt < RETRIES:
            time.sleep(RETRY_DELAY * attempt)
    raise FetchError(f"{path}: {last_exc}") from last_exc
