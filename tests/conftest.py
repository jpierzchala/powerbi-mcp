import asyncio
import logging
import warnings
import pytest

from .network_diag import CORE_POWERBI_DOMAINS, probe_domains

@pytest.fixture(scope="session", autouse=True)
def network_diagnostics():
    logging.basicConfig(level=logging.INFO, force=True)
    res = asyncio.run(probe_domains(CORE_POWERBI_DOMAINS))
    lines = ["=== Power BI Network Preflight (via proxy) ==="]
    for r in res:
        if r["step"] == "target":
            lines.append(
                f"OK    {r['host']} status={r['status']} via={r.get('via')}"
            )
        elif r["step"] == "proxy":
            lines.append(
                f"BLOCK {r['host']} proxy_status={r['status']} msg={r['message']}"
            )
        else:
            lines.append(f"ERR   {r['host']} err={r.get('error')}")
    warnings.warn("\n".join(lines))
