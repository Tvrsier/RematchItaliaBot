import aiohttp

_session: aiohttp.ClientSession | None = None


def get_session() -> aiohttp.ClientSession:
    global _session
    if _session and not _session.closed:
        return _session
    timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)
    connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
    _session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    return _session

async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None