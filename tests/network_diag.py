import asyncio
import os
import ssl
from typing import Optional, Sequence
import aiohttp


CORE_POWERBI_DOMAINS = [
    "api.powerbi.com",
    "login.microsoftonline.com",
    "login.windows.net",
    "analysis.windows.net",
    "aadcdn.msftauth.net",
    "aadcdn.msauth.net",
]


def _get_proxy_url() -> Optional[str]:
    """Return proxy URL from env or default to http://proxy:8080."""
    for env_name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = os.environ.get(env_name)
        if v:
            return v
    return "http://proxy:8080"


async def probe_domains(domains: Sequence[str]):
    """Probe each domain using a GET request via the configured proxy."""
    proxy_url = _get_proxy_url()
    timeout = aiohttp.ClientTimeout(total=15)
    ssl_ctx = ssl.create_default_context()
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(
        timeout=timeout, connector=connector, trust_env=True
    ) as session:
        results = []
        for host in domains:
            url = f"https://{host}/"
            try:
                async with session.get(
                    url, allow_redirects=False, proxy=proxy_url
                ) as resp:
                    results.append(
                        {
                            "host": host,
                            "step": "target",
                            "status": resp.status,
                            "via": resp.headers.get("Via"),
                            "location": resp.headers.get("Location"),
                            "blocked": False,
                        }
                    )
            except aiohttp.ClientHttpProxyError as e:
                results.append(
                    {
                        "host": host,
                        "step": "proxy",
                        "status": e.status,
                        "message": str(e),
                        "blocked": True,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "host": host,
                        "step": "error",
                        "status": None,
                        "error": repr(e),
                        "blocked": None,
                    }
                )
        return results


if __name__ == "__main__":
    results = asyncio.run(probe_domains(CORE_POWERBI_DOMAINS))
    print("=== Power BI Network Preflight (via proxy) ===")
    for r in results:
        if r["step"] == "target":
            print(f"OK    {r['host']} status={r['status']} via={r.get('via')}")
        elif r["step"] == "proxy":
            print(f"BLOCK {r['host']} proxy_status={r['status']} msg={r['message']}")
        else:
            print(f"ERR   {r['host']} err={r.get('error')}")
