import Interface
import os
from pathlib import Path
from utils import run_command

# manage config files + interface lifecycle
class InterfaceManager:
    def __init__(self, config_dir: str = "/etc/wireguard"):
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

    def list_interfaces(self) -> list[str]:
        """Return interface names based on *.conf files"""
        if not os.path.exists(self.config_dir):
            return []
        
        configs = []
        for file in os.listdir(self.config_dir):
            if file.endswith('.conf'):
                configs.append(file[:-5])  # Remove .conf extension
        return sorted(configs)

    def exists(self, name: str) -> bool:
        """Check if interface config exists"""
        config_path = os.path.join(self.config_dir, f"{name}.conf")
        return os.path.isfile(config_path)

    def load(self, name: str) -> Interface.Interface:
        """Return Interface object (does not bring it up)"""
        if not self.exists(name):
            raise FileNotFoundError(f"Interface config {name} not found")
        return Interface.Interface(name)

    def up(self, name: str) -> None:
        """wg-quick up"""
        if self.load(name)._is_up():
            print(f"Interface {name} is already up")
            return 0
        if not self.exists(name):
            raise FileNotFoundError(f"Interface config {name} not found")
        
        try:
            run_command(f"wg-quick up {name}")
        except Exception as e:
            raise RuntimeError(f"Failed to bring up interface {name}: {e}")

    def down(self, name: str) -> None:
        """wg-quick down"""
        if not self.load(name)._is_up():
            print(f"Interface {name} is already down")
            return 0
        if not self.exists(name):
            raise FileNotFoundError(f"Interface config {name} not found")
        
        try:
            run_command(f"wg-quick down {name}")
        except Exception as e:
            raise RuntimeError(f"Failed to bring down interface {name}: {e}")

    def create(self, name: str, config_text: str) -> None:
        """Create config file"""
        config_path = os.path.join(self.config_dir, f"{name}.conf")
        
        if os.path.exists(config_path):
            raise FileExistsError(f"Interface config {name} already exists")
        
        try:
            with open(config_path, 'w') as f:
                f.write(config_text)
            # Set restrictive permissions (600)
            os.chmod(config_path, 0o600)
        except Exception as e:
            raise RuntimeError(f"Failed to create interface config {name}: {e}")

    def delete(self, name: str) -> None:
        """Delete config file (interface must be down)"""
        if not self.exists(name):
            raise FileNotFoundError(f"Interface config {name} not found")
        
        # Check if interface is up
        try:
            iface = self.load(name)
            if iface._is_up():
                raise RuntimeError(f"Interface {name} is still up, bring it down first")
        except:
            pass
        
        config_path = os.path.join(self.config_dir, f"{name}.conf")
        try:
            os.remove(config_path)
        except Exception as e:
            raise RuntimeError(f"Failed to delete interface config {name}: {e}")
