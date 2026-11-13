from urllib.parse import urlsplit


def official_cpsc(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https"
            and p.hostname in {"cpsc.gov", "www.cpsc.gov"}
            and not p.username
            and not p.password
            and p.port in {None, 443}
            and p.path.startswith("/Recalls/")
        )
    except ValueError:
        return False


def validate_public_url(url: str, allowed_hosts: frozenset[str], addresses: list[str]) -> str:
    import ipaddress

    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.hostname not in allowed_hosts
        or p.username
        or p.password
        or p.port not in {None, 443}
        or not addresses
    ):
        raise ValueError("Untrusted public source")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Private source address blocked")
    return url


async def checked_manufacturer_url(url: str) -> str:
    """Validate every redirect before following. Only CPSC-linked NEWDERY public page supported."""
    import asyncio
    import socket
    from urllib.parse import urljoin

    import httpx

    allowed = frozenset({"www.newdery.com", "newdery.com"})
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
        for _ in range(4):
            host = urlsplit(url).hostname
            # Validate the host before DNS or any remote request.
            if host not in allowed:
                raise ValueError("Untrusted redirect host")
            resolved = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
            validate_public_url(url, allowed, list({str(r[4][0]) for r in resolved}))
            response = await client.head(url)
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            return url
    raise ValueError("Too many redirects")
