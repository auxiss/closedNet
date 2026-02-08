import subprocess
import peer
from utils import run_command
import json
import re

# manage a live interface and its peers
class Interface:
    def __init__(self, name: str):
        self.name = name

    # ---- Interface state ----

    def _is_up(self) -> bool:
        """Check if interface is currently up"""
        try:
            result = subprocess.run(
                ['ip', 'link', 'show', self.name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and 'UP' in result.stdout
        except Exception:
            return False

    def show(self) -> dict:
        """Raw parsed output of `wg show <iface>`"""
        if self._is_up():
            try:
                output = run_command(f"wg show {self.name}")
                return self._parse_wg_show(output)
            except Exception as e:
                raise RuntimeError(f"Failed to show interface {self.name}: {e}")
        else:
            result = {
                "interface": self.name,
                "state": "down",
                "public_key": None,
                "private_key": None,
                "listening_port": None,
                "peers": {}
            }
            return result  # Return empty data if interface is down
    
    def _parse_wg_show(self, output: str) -> dict:
        """Parse `wg show <iface>` output into structured data"""
        result = {
            "interface": self.name,
            "state": "up",
            "public_key": None,
            "private_key": None,
            "listening_port": None,
            "peers": {}
        }
        
        lines = output.strip().split('\n')
        current_peer = None
        
        for line in lines:
            #print(f"Parsing line: {line}")  # Debug print
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('interface:'):
                result["interface"] = line.split(':', 1)[1].strip()
            elif line.startswith('public key:'):
                result["public_key"] = line.split(':', 1)[1].strip()
            elif line.startswith('private key:'):
                result["private_key"] = line.split(':', 1)[1].strip()
            elif line.startswith('listening port:'):
                result["listening_port"] = int(line.split(':', 1)[1].strip())
            elif line.startswith('peer:'):
                current_peer = line.split(':', 1)[1].strip()
                result["peers"][current_peer] = {
                    "public_key": current_peer,
                    "endpoint": None,
                    "allowed_ips": [],
                    "latest_handshake": None,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                    "persistent_keepalive": None
                }
            elif current_peer and line.startswith('endpoint:'):
                result["peers"][current_peer]["endpoint"] = line.split(':', 1)[1].strip()
            elif current_peer and line.startswith('allowed ips:'):
                ips = line.split(':', 1)[1].strip()
                result["peers"][current_peer]["allowed_ips"] = [ip.strip() for ip in ips.split(',')]
            elif current_peer and line.startswith('latest handshake:'):
                result["peers"][current_peer]["latest_handshake"] = line.split(':', 1)[1].strip()
            elif current_peer and line.startswith('transfer:'):
                transfer = line.split(':', 1)[1].strip()
                parts = transfer.split(',')
                if len(parts) >= 2:
                    rx = parts[0].strip().split()[0]
                    tx = parts[1].strip().split()[0]
                    result["peers"][current_peer]["rx_bytes"] = float(rx)
                    result["peers"][current_peer]["tx_bytes"] = float(tx)
            elif current_peer and line.startswith('persistent keepalive:'):
                keepalive = line.split(':', 1)[1].strip()
                if keepalive != "off":
                    result["peers"][current_peer]["persistent_keepalive"] = int(keepalive.split()[1])
        
        return result

    # ---- Peer management (NO config files) ----

    def add_peer(
        self,
        public_key: str,
        allowed_ips: list[str],
        endpoint: str | None = None,
        persistent_keepalive: int | None = None,
    ) -> None:
        """Add a new peer to the interface"""
        self.create_peer(
            public_key,
            endpoint=endpoint,
            allowed_ips=allowed_ips,
            persistent_keepalive=persistent_keepalive
        )

    def remove_peer(self, public_key: str) -> None:
        """Remove a peer from the interface"""
        try:
            run_command(f"wg set {self.name} peer {public_key} remove")
        except Exception as e:
            raise RuntimeError(f"Failed to remove peer {public_key}: {e}")

    def create_peer(
        self,
        public_key: str,
        *,
        endpoint: str | None = None,
        allowed_ips: list[str] | None = None,
        persistent_keepalive: int | None = None,
    ) -> None:
        """Create a new peer"""
        if not allowed_ips:
            allowed_ips = []
        
        cmd_parts = [f"wg set {self.name} peer {public_key}"]
        
        if allowed_ips:
            ips = ",".join(allowed_ips)
            cmd_parts.append(f"allowed-ips {ips}")
        
        if endpoint:
            cmd_parts.append(f"endpoint {endpoint}")
        
        if persistent_keepalive is not None:
            cmd_parts.append(f"persistent-keepalive {persistent_keepalive}")
        
        try:
            run_command(" ".join(cmd_parts))
        except Exception as e:
            raise RuntimeError(f"Failed to create peer {public_key}: {e}")

    def update_peer(
        self,
        public_key: str,
        *,
        endpoint: str | None = None,
        allowed_ips: list[str] | None = None,
        persistent_keepalive: int | None = None,
    ) -> None:
        """Update an existing peer"""
        # Check if peer exists
        peers = self.show()["peers"]
        if public_key not in peers:
            raise ValueError(f"Peer {public_key} does not exist")
        
        cmd_parts = [f"wg set {self.name} peer {public_key}"]
        
        if allowed_ips is not None:
            ips = ",".join(allowed_ips)
            cmd_parts.append(f"allowed-ips {ips}")
        
        if endpoint is not None:
            cmd_parts.append(f"endpoint {endpoint}")
        
        if persistent_keepalive is not None:
            cmd_parts.append(f"persistent-keepalive {persistent_keepalive}")
        
        try:
            run_command(" ".join(cmd_parts))
        except Exception as e:
            raise RuntimeError(f"Failed to update peer {public_key}: {e}")

    # ---- Peer inspection ----

    def get_peers(self) -> list[str]:
        """Return list of public keys"""
        data = self.show()
        return list(data["peers"].keys())

    def get_peer(self, public_key: str) -> peer.Peer:
        """Return Peer object for given public key"""
        data = self.show()
        if public_key not in data["peers"]:
            raise ValueError(f"Peer {public_key} not found")
        return peer.Peer(self, public_key) 

