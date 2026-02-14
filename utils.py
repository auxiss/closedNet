
def is_root() -> bool:
    """Return True if the current process is running as root (POSIX).

    On non-POSIX platforms where `os.geteuid` is unavailable, returns False.
    """
    import os

    try:
        return os.geteuid() == 0
    except AttributeError:
        return False

def get_public_ip_v6() -> str:
    """Return the machine's public IPv6 address as a string.

    Tries several public IPv6-detection services and validates the result.
    Returns an empty string on failure.
    """
    import urllib.request
    import ipaddress

    services = [
        "https://api6.ipify.org",
        "https://ipv6.icanhazip.com",
        "https://ifconfig.co/ip",
    ]

    for url in services:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode().strip()
        except Exception:
            continue

        if not body:
            continue

        try:
            addr = ipaddress.ip_address(body)
            if addr.version == 6:
                return body
        except Exception:
            continue

    return ""
