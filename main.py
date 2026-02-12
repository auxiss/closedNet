#!./.venv/bin/python3
from wireguard_manager.InterfaceManager import InterfaceManager
from distribution_layer import group_manager
from distribution_layer import conf_loader
import threading
import time
import socket
import subprocess
import json
import os


class NetManager():
    def __init__(self, config_file: str = "config.json", iface_name: str = 'closednet0', config_dir: str = "/etc/wireguard"):
        self.iface_name = iface_name
        self.config_dir = config_dir
        self.config_file = config_file
        self.interface_manager = InterfaceManager(config_dir)
        self.group = None
        self.interface = None
        self.discovery_thread = None
        self.running = False
        
        # Initialize: load config, setup interface, initialize group
        self._initialize()
    
    def _initialize(self):
        """Initialize the network manager"""
        # Load or create local config
        if not os.path.exists(self.config_file):
            print(f"Config file {self.config_file} not found. Creating new config...")
            token = input("Enter your GitHub token: ").strip()
            username = input("Enter your username: ").strip()
            group_name = input("Enter the group name: ").strip()
            group_key = input("Enter the group key: ").strip()
            conf_loader.create_config_file(token, username, group_name, group_key)
        
        print(f"[*] Loading config from {self.config_file}...")
        config = conf_loader.load_config_file()
        print(f"[+] Config loaded successfully")
        
        # Setup or load WireGuard interface
        if not self.interface_manager.exists(self.iface_name):
            print(f"[*] Creating new WireGuard interface: {self.iface_name}")
            self._create_interface(config)
            print(f"[+] Interface created")
        else:
            print(f"[*] Interface {self.iface_name} already exists")
        
        print(f"[*] Loading interface {self.iface_name}...")
        self.interface = self.interface_manager.load(self.iface_name)
        
        print(f"[*] Bringing up interface {self.iface_name}...")
        self.interface_manager.up(self.iface_name)
        print(f"[+] Interface is now up")
        
        # Initialize group manager
        print(f"[*] Initializing group manager...")
        key_pair = (config["PEM_private_key"].encode(), config["PEM_public_key"].encode())
        self.group = group_manager.Group(
            token=config["token"],
            owner=config["username"],
            group=config["group_name"],
            group_key=config["group_key"].encode(),
            key_pair=key_pair,
            public=True
        )
        print(f"[+] Group manager initialized for group '{config['group_name']}'")
        
        # Post our info
        print(f"[*] Detecting public IPv6 address...")
        ipv6 = self._find_public_ipv6()
        if ipv6:
            print(f"[+] Found public IPv6: {ipv6}")
        else:
            print(f"[-] Could not detect public IPv6")
        
        wg_pubkey = self.interface.show().get("public_key", "")
        if ipv6 and wg_pubkey:
            print(f"[*] Posting endpoint information to group...")
            self.group.create_and_post(f"{ipv6}:51820", wg_pubkey)
            print(f"[+] Endpoint posted successfully")
        
        # Start peer discovery thread
        print(f"[*] Starting peer discovery thread...")
        self.start_peer_discovery()
        print(f"[+] Peer discovery thread started")
    
    def _create_interface(self, config: dict):
        """Create a new WireGuard interface"""
        # Generate basic interface config
        try:
            print("    [*] Generating WireGuard keys...")
            result = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True,
                check=True
            )
            private_key = result.stdout.strip()
            
            # Generate public key from private key
            result = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            )
            public_key = result.stdout.strip()
            print("    [+] Keys generated successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to generate WireGuard keys: {e}")
        
        # Create interface config
        interface_config = f"""[Interface]
PrivateKey = {private_key}
Address = 10.0.0.1/24
ListenPort = 51820

"""
        
        print("    [*] Writing interface config to disk...")
        self.interface_manager.create(self.iface_name, interface_config)
        print("    [+] Interface config created")
    
    def _find_public_ipv6(self) -> str | None:
        """Find public IPv6 address of the system"""
        try:
            # Try to get IPv6 using socket
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            s.connect(("2001:4860:4860::8888", 80))  # Google's public DNS
            ipv6 = s.getsockname()[0]
            s.close()
            return ipv6
        except Exception:
            return None

    def start_peer_discovery(self):
        """Start the peer discovery thread"""
        if self.discovery_thread is None or not self.discovery_thread.is_alive():
            self.running = True
            self.discovery_thread = threading.Thread(target=self._peer_discovery_thread, daemon=True)
            self.discovery_thread.start()

    def stop_peer_discovery(self):
        """Stop the peer discovery thread"""
        self.running = False
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.discovery_thread.join(timeout=5)

    def _peer_discovery_thread(self):
        """Background thread: continuously discover and update peers"""
        print("[*] Peer discovery thread started")
        config = conf_loader.load_config_file()
        known_members = config.get("members", [])
        
        while self.running:
            try:
                # Get known members from group
                members_info = self.group.get_known_members(known_members)
                
                if members_info:
                    print(f"[*] Found {len(members_info)} known member(s), updating WireGuard...")
                
                # Add/update peers in WireGuard
                for member in members_info:
                    self._add_or_update_peer_live(member)
                    print(f"    [+] Updated peer: {member['name']}")
                
                # Sleep before next discovery
                time.sleep(30)  # Poll every 30 seconds
            except Exception as e:
                print(f"[-] Error in peer discovery: {e}")
                time.sleep(30)

    def _add_or_update_peer_live(self, member_info: dict):
        """Add or update a peer in live WireGuard interface"""
        try:
            payload = member_info["payload"]
            endpoint = payload["endpoint"]
            wg_pk = payload["wg_pk"]
            allowed_ips = "10.0.0.0/24"  # Adjust as needed
            
            # Use wg set to add/update peer
            subprocess.run(
                ["wg", "set", self.iface_name, "peer", wg_pk, 
                 "endpoint", endpoint, "allowed-ips", allowed_ips],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"[-] Failed to add/update peer: {e}")

    def add_peer(self, name: str, rsa_pub_key: str):
        """Add a peer to the local config"""
        print(f"[*] Adding peer '{name}' to config...")
        config = conf_loader.load_config_file()
        members = config.get("members", [])
        
        # Check if member already exists
        if any(m["name"] == name for m in members):
            print(f"[-] Member '{name}' already exists")
            return
        
        members.append({"name": name, "rsa_public_key": rsa_pub_key})
        config["members"] = members
        
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)
        
        print(f"[+] Member '{name}' added to config")

    def remove_peer(self, name: str):
        """Remove a peer from config and live WireGuard if up"""
        print(f"[*] Removing peer '{name}' from config...")
        config = conf_loader.load_config_file()
        members = config.get("members", [])
        
        # Remove from config
        original_count = len(members)
        members = [m for m in members if m["name"] != name]
        
        if len(members) == original_count:
            print(f"[-] Member '{name}' not found")
            return
        
        config["members"] = members
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)
        
        # Remove from live interface if it's up
        if self.interface and self.interface._is_up():
            try:
                # Get the peer's public key from the interface
                iface_data = self.interface.show()
                for peer_pk in iface_data.get("peers", {}):
                    # We'd need to track name->pubkey mapping for this
                    # For now, just log the intention
                    pass
                print(f"[+] Member '{name}' removed from config. Run 'wg set' manually to remove from live interface if needed.")
            except Exception as e:
                print(f"[-] Error removing peer from live interface: {e}")
        else:
            print(f"[+] Member '{name}' removed from config")


if __name__ == "__main__":
    # Example usage
    try:
        print("[*] Starting closedNet Network Manager...")
        manager = NetManager()
        print(f"[+] NetManager initialized with interface {manager.iface_name}")
        print("[*] Press Ctrl+C to stop")
        
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        print(f"[*] Bringing down interface {manager.iface_name}...")
        manager.stop_peer_discovery()
        manager.interface_manager.down(manager.iface_name)
        print("[+] Interface brought down")
        print("[+] Shutdown complete")
    except Exception as e:
        print(f"[-] Error: {e}")
