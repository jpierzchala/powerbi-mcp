"""ADOMD.NET library setup and initialization."""

import os
import platform
import sys

from .environment import logger


def setup_adomd_paths():
    """Setup ADOMD.NET search paths and return them."""
    # Prepare ADOMD.NET search paths before importing pyadomd
    env_adomd = os.environ.get("ADOMD_LIB_DIR")

    # Try to use NuGet packages first (if available)
    user_nuget_path = os.path.expanduser(r"~\.nuget\packages")
    nuget_adomd_path = os.path.join(
        user_nuget_path,
        "microsoft.analysisservices.adomdclient.netcore.retail.amd64",
        "19.84.1",
        "lib",
        "netcoreapp3.0",
    )
    nuget_config_path = os.path.join(
        user_nuget_path, "system.configuration.configurationmanager", "9.0.7", "lib", "net8.0"
    )
    nuget_identity_path = os.path.join(user_nuget_path, "microsoft.identity.client", "4.74.0", "lib", "net8.0")
    nuget_identity_abs_path = os.path.join(
        user_nuget_path, "microsoft.identitymodel.abstractions", "6.35.0", "lib", "net6.0"
    )

    adomd_paths = [
        env_adomd,
        nuget_adomd_path if os.path.exists(nuget_adomd_path) else None,
        nuget_config_path if os.path.exists(nuget_config_path) else None,
        nuget_identity_path if os.path.exists(nuget_identity_path) else None,
        nuget_identity_abs_path if os.path.exists(nuget_identity_abs_path) else None,
        r"C:\\Program Files\\Microsoft.NET\\ADOMD.NET\\160",
        r"C:\\Program Files\\Microsoft.NET\\ADOMD.NET\\150",
        r"C:\\Program Files (x86)\\Microsoft.NET\\ADOMD.NET\\160",
        r"C:\\Program Files (x86)\\Microsoft.NET\\ADOMD.NET\\150",
        r"C:\\Program Files (x86)\\MicrosoftOffice\\root\\vfs\\ProgramFilesX86\\Microsoft.NET\\ADOMD.NET\\130",
    ]

    logger.info(
        "Adding ADOMD.NET paths to sys.path: %s",
        ", ".join([p for p in adomd_paths if p]),
    )
    for p in adomd_paths:
        if p and os.path.exists(p):
            sys.path.append(p)

    return adomd_paths


def setup_pythonnet():
    """Setup pythonnet runtime configuration."""
    import pythonnet

    # Choose appropriate runtime based on platform
    # Use coreclr by default on all platforms as it works with our NuGet packages
    pythonnet_runtime = os.environ.get("PYTHONNET_RUNTIME", "coreclr")

    logger.info("Configuring pythonnet runtime: %s for %s", pythonnet_runtime, platform.system())
    try:
        pythonnet.set_runtime(pythonnet_runtime)
    except Exception as e:  # pragma: no cover - best effort
        logger.warning("Failed to set pythonnet runtime: %s", e)
        # Try alternative runtime
        try:
            if platform.system() == "Linux":
                pythonnet.set_runtime("mono")
                logger.info("Fallback to mono runtime")
            else:
                pythonnet.set_runtime("coreclr")
                logger.info("Fallback to coreclr runtime")
        except Exception as e2:  # pragma: no cover - best effort
            logger.warning("Failed to set fallback runtime: %s", e2)


def load_adomd_assemblies(adomd_paths):
    """Load ADOMD.NET assemblies and return status."""

    # Placeholder for AdomdSchemaGuid if the assembly fails to load
    class _DummySchemaGuid:
        Tables = 0

    AdomdSchemaGuid = _DummySchemaGuid

    # Try to load ADOMD.NET assemblies if clr is available and not skipped
    adomd_loaded = False
    skip_adomd_load = os.environ.get("SKIP_ADOMD_LOAD", "0").lower() in ("1", "true", "yes")

    try:
        import clr  # type: ignore
    except ImportError:
        clr = None

    if clr and not skip_adomd_load:
        logger.info("Searching for ADOMD.NET in: %s", ", ".join([p for p in adomd_paths if p]))
        for path in adomd_paths:
            if not path:
                continue
            if os.path.exists(path):
                dll = os.path.join(path, "Microsoft.AnalysisServices.AdomdClient.dll")
                try:
                    sys.path.append(path)
                    clr.AddReference(dll)
                    adomd_loaded = True
                    logger.info("Loaded ADOMD.NET from %s", dll)
                    break
                except Exception as e:  # pragma: no cover - best effort
                    logger.warning("Failed to load ADOMD.NET from %s: %s", dll, e)
                    continue

        if adomd_loaded:
            try:
                from Microsoft.AnalysisServices.AdomdClient import AdomdSchemaGuid as _ASG

                AdomdSchemaGuid = _ASG
                logger.debug("ADOMD.NET types imported")
            except Exception as e:  # pragma: no cover - best effort
                logger.warning("Failed to import AdomdSchemaGuid: %s", e)

    if not adomd_loaded:
        if skip_adomd_load:
            logger.info("ADOMD.NET loading skipped due to SKIP_ADOMD_LOAD environment variable")
        else:
            logger.warning("ADOMD.NET library not found. Pyadomd functionality will be disabled.")

    return adomd_loaded, AdomdSchemaGuid


def import_pyadomd():
    """Import pyadomd and return references."""
    try:
        import clr  # type: ignore
        from pyadomd import Pyadomd  # type: ignore

        logger.debug("pythonnet and pyadomd imported successfully")
        return clr, Pyadomd
    except Exception as e:  # pragma: no cover - runtime environment dependent
        logger.warning("pyadomd not available: %s", e)
        return None, None


def initialize_adomd():
    """Initialize ADOMD.NET components and return all necessary objects."""
    # Setup paths
    adomd_paths = setup_adomd_paths()

    # Setup pythonnet
    setup_pythonnet()

    # Import components
    clr, Pyadomd = import_pyadomd()

    # Load assemblies
    adomd_loaded, AdomdSchemaGuid = load_adomd_assemblies(adomd_paths)

    return clr, Pyadomd, adomd_loaded, AdomdSchemaGuid
