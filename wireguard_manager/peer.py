from datetime import datetime, timedelta
from wireguard_manager import Interface

class Peer:
    def __init__(self, interface: Interface, public_key: str):
        self.interface = interface
        self.public_key = public_key

    def stats(self) -> dict:
        """
        Example:
        {
            "endpoint": "1.2.3.4:51820",
            "latest_handshake": datetime | None,
            "rx_bytes": int,
            "tx_bytes": int,
            "persistent_keepalive": int | None,
        }
        """
        data = self.interface.show()
        if self.public_key not in data["peers"]:
            raise ValueError(f"Peer {self.public_key} not found")
        
        peer_data = data["peers"][self.public_key]
        
        return {
            "endpoint": peer_data["endpoint"],
            "latest_handshake": self._parse_handshake(peer_data["latest_handshake"]),
            "rx_bytes": peer_data["rx_bytes"],
            "tx_bytes": peer_data["tx_bytes"],
            "persistent_keepalive": peer_data["persistent_keepalive"],
        }
    
    def _parse_handshake(self, handshake_str: str | None) -> datetime | None:
        """Parse handshake string to datetime or None"""
        if not handshake_str or handshake_str == "Never":
            return None
        
        try:
            # Try to parse ISO format or common timestamp formats
            return datetime.fromisoformat(handshake_str)
        except:
            try:
                # If it's a Unix timestamp
                return datetime.fromtimestamp(float(handshake_str))
            except:
                return None

    def last_handshake(self) -> datetime | None:
        """Return the time of last handshake"""
        return self.stats()["latest_handshake"]

    def is_connected(self, timeout: timedelta = timedelta(minutes=2)) -> bool:
        """
        True if latest handshake within timeout
        """
        last_hs = self.last_handshake()
        if last_hs is None:
            return False
        
        now = datetime.now()
        return (now - last_hs) <= timeout
