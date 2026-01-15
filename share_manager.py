import json
import os
import subprocess
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from enum import Enum


class ShareStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    MOUNTED = "mounted"
    ERROR = "error"


@dataclass
class Share:
    id: str
    server: str
    share_name: str
    username: str
    password: str
    mount_point: str
    automounted: bool = False
    
    @property
    def unc_path(self) -> str:
        return f"//{self.server}/{self.share_name}"
    
    @property
    def display_name(self) -> str:
        return f"{self.unc_path} → {self.mount_point}"


class ShareManager:
    FSTAB_PATH = "/etc/fstab"
    FSTAB_START_MARKER = "### Mounty-Start"
    FSTAB_END_MARKER = "### Mounty-End"
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "mounty"
        self.shares_file = self.config_dir / "shares.json"
        self.credentials_dir = self.config_dir / "credentials"
        self.shares: list[Share] = []
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        # Secure credentials directory
        os.chmod(self.credentials_dir, 0o700)
        
        self.load_shares()
    
    def load_shares(self) -> None:
        if self.shares_file.exists():
            try:
                with open(self.shares_file, 'r') as f:
                    data = json.load(f)
                    self.shares = [Share(**s) for s in data]
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading shares: {e}")
                self.shares = []
        else:
            self.shares = []
    
    def save_shares(self) -> None:
        with open(self.shares_file, 'w') as f:
            json.dump([asdict(s) for s in self.shares], f, indent=2)
    
    def generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def add_share(self, share: Share) -> None:
        self.shares.append(share)
        self.save_shares()
    
    def update_share(self, share: Share) -> None:
        for i, s in enumerate(self.shares):
            if s.id == share.id:
                self.shares[i] = share
                break
        self.save_shares()
    
    def remove_share(self, share: Share) -> tuple[bool, str]:
        if share.automounted:
            success, msg = self.remove_from_fstab(share)
            if not success:
                return False, msg

        cred_file = self.credentials_dir / f"{share.id}.cred"
        if cred_file.exists():
            cred_file.unlink()
        
        self.shares = [s for s in self.shares if s.id != share.id]
        self.save_shares()
        return True, "Share removed successfully"
    
    def test_share(self, share: Share) -> tuple[bool, str]:
        import tempfile
        auth_file = None
        try:
            auth_file = tempfile.NamedTemporaryFile(mode='w', suffix='.auth', delete=False)
            auth_file.write(f"username={share.username}\n")
            auth_file.write(f"password={share.password}\n")
            auth_file.close()
            os.chmod(auth_file.name, 0o600)
            
            cmd = [
                "smbclient",
                f"//{share.server}/{share.share_name}",
                "-A", auth_file.name,
                "-c", "dir",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                return True, "Connection successful"
            
            error_lower = output.lower()
            if "nt_status_logon_failure" in error_lower:
                return False, "Authentication failed - check username/password"
            elif "nt_status_bad_network_name" in error_lower:
                return False, "Share not found - check share name"
            elif "nt_status_host_unreachable" in error_lower:
                return False, "Cannot reach server - check server address"
            elif "nt_status_connection_refused" in error_lower:
                return False, "Connection refused - check if server is running"
            elif "nt_status_access_denied" in error_lower:
                return False, "Access denied - check permissions"
            elif "nt_status_" in error_lower:
                import re
                match = re.search(r'(NT_STATUS_\w+)', output, re.IGNORECASE)
                if match:
                    return False, f"Connection failed: {match.group(1)}"
            elif "name or service not known" in error_lower or "no route to host" in error_lower:
                return False, "Cannot resolve server - check server address"
            elif "connection timed out" in error_lower:
                return False, "Connection timed out - check network"
            
            error_msg = output.strip()[-200:] if output.strip() else f"Exit code: {result.returncode}"
            return False, f"Connection failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "Connection timed out (15s)"
        except FileNotFoundError:
            return False, "smbclient not installed. Install with: sudo apt install smbclient"
        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            if auth_file and os.path.exists(auth_file.name):
                os.unlink(auth_file.name)
    
    def is_mounted(self, share: Share) -> bool:
        try:
            result = subprocess.run(
                ["findmnt", "-n", share.mount_point],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def mount_share(self, share: Share) -> tuple[bool, str]:
        mount_point = Path(share.mount_point)
        
        if not mount_point.exists():
            try:
                subprocess.run(
                    ["pkexec", "mkdir", "-p", str(mount_point)],
                    check=True
                )
            except subprocess.CalledProcessError as e:
                return False, f"Failed to create mount point: {e}"
        
        cred_file = self.credentials_dir / f"{share.id}.cred"
        self._write_credentials_file(share, cred_file)
        
        try:
            uid = os.getuid()
            gid = os.getgid()
            cmd = [
                "pkexec", "mount", "-t", "cifs",
                share.unc_path,
                str(mount_point),
                "-o", f"credentials={cred_file},uid={uid},gid={gid}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Mounted successfully"
            else:
                return False, f"Mount failed: {result.stderr.strip()}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def unmount_share(self, share: Share) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["pkexec", "umount", share.mount_point],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, "Unmounted successfully"
            else:
                return False, f"Unmount failed: {result.stderr.strip()}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _write_credentials_file(self, share: Share, path: Path) -> None:
        with open(path, 'w') as f:
            f.write(f"username={share.username}\n")
            f.write(f"password={share.password}\n")
        os.chmod(path, 0o600)
    
    def add_to_fstab(self, share: Share) -> tuple[bool, str]:
        cred_file = self.credentials_dir / f"{share.id}.cred"
        self._write_credentials_file(share, cred_file)
        
        mount_point = Path(share.mount_point)
        if not mount_point.exists():
            try:
                subprocess.run(
                    ["pkexec", "mkdir", "-p", str(mount_point)],
                    check=True
                )
            except subprocess.CalledProcessError as e:
                return False, f"Failed to create mount point: {e}"
        
        uid = os.getuid()
        gid = os.getgid()
        fstab_entry = (
            f"{share.unc_path} {share.mount_point} cifs "
            f"credentials={cred_file},uid={uid},gid={gid},_netdev,nofail 0 0"
        )
        
        try:
            with open(self.FSTAB_PATH, 'r') as f:
                content = f.read()
            
            # Check if markers exist
            if self.FSTAB_START_MARKER not in content:
                # Add markers at the end
                if not content.endswith('\n'):
                    content += '\n'
                content += f"\n{self.FSTAB_START_MARKER}\n{self.FSTAB_END_MARKER}\n"
            
            # Insert entry before end marker
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.strip() == self.FSTAB_END_MARKER:
                    new_lines.append(fstab_entry)
                new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
            
            process = subprocess.Popen(
                ["pkexec", "tee", self.FSTAB_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            _, stderr = process.communicate(new_content)
            
            if process.returncode != 0:
                return False, f"Failed to write fstab: {stderr}"
            
            share.automounted = True
            self.update_share(share)
            
            subprocess.run(["pkexec", "mount", share.mount_point], capture_output=True)
            
            return True, "Added to fstab successfully"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def remove_from_fstab(self, share: Share) -> tuple[bool, str]:
        try:
            if self.is_mounted(share):
                self.unmount_share(share)
            
            with open(self.FSTAB_PATH, 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            in_mounty_section = False
            for line in lines:
                stripped = line.strip()
                
                if stripped == self.FSTAB_START_MARKER:
                    in_mounty_section = True
                    new_lines.append(line)
                    continue
                elif stripped == self.FSTAB_END_MARKER:
                    in_mounty_section = False
                    new_lines.append(line)
                    continue
                
                # Skip lines matching this share's UNC path in Mounty section
                if in_mounty_section and share.unc_path in line:
                    continue
                
                new_lines.append(line)
            
            new_content = ''.join(new_lines)
            
            process = subprocess.Popen(
                ["pkexec", "tee", self.FSTAB_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            _, stderr = process.communicate(new_content)
            
            if process.returncode != 0:
                return False, f"Failed to write fstab: {stderr}"
            
            # Update share status
            share.automounted = False
            self.update_share(share)
            
            # Remove credentials file
            cred_file = self.credentials_dir / f"{share.id}.cred"
            if cred_file.exists():
                cred_file.unlink()
            
            return True, "Removed from fstab successfully"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_fstab_entries(self) -> list[str]:
        entries = []
        try:
            with open(self.FSTAB_PATH, 'r') as f:
                lines = f.readlines()
            
            in_mounty_section = False
            for line in lines:
                stripped = line.strip()
                
                if stripped == self.FSTAB_START_MARKER:
                    in_mounty_section = True
                    continue
                elif stripped == self.FSTAB_END_MARKER:
                    in_mounty_section = False
                    continue
                
                if in_mounty_section and stripped and not stripped.startswith('#'):
                    entries.append(stripped)
                    
        except Exception as e:
            print(f"Error reading fstab: {e}")
        
        return entries
