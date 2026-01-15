# Mounty - Network Share Manager

A Linux native GTK4/Adwaita application for managing network shares (SMB/CIFS) with fstab integration for automounting.

![Mounty](https://img.shields.io/badge/Platform-Linux-blue) ![GTK4](https://img.shields.io/badge/GTK-4.0-green) ![Python](https://img.shields.io/badge/Python-3.10+-yellow) ![AUR](https://img.shields.io/badge/AUR-mounty-blue)

## Features

- **Add Network Shares** - Configure SMB/CIFS shares with server, credentials, and mount point
- **Test Connections** - Verify share accessibility before saving
- **Mount/Unmount** - Temporarily mount shares for testing
- **Automount** - Write to `/etc/fstab` for persistent mounting across reboots
- **Secure Credentials** - Stores credentials in `~/.config/mounty/credentials/` with restricted permissions
- **fstab Integration** - Manages entries between `### Mounty-Start` and `### Mounty-End` markers

## Installation

### Arch Linux (AUR)

```bash
# Using yay
yay -S mounty

# Using paru
paru -S mounty

# Manual
git clone https://aur.archlinux.org/mounty.git
cd mounty
makepkg -si
```

### From Source

#### Dependencies

```bash
# Arch Linux
sudo pacman -S python-gobject gtk4 libadwaita smbclient cifs-utils polkit

# Ubuntu/Debian
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 smbclient cifs-utils policykit-1

# Fedora
sudo dnf install python3-gobject gtk4 libadwaita samba-client cifs-utils polkit
```

#### Run from Source

```bash
git clone https://github.com/yourusername/mounty.git
cd mounty
python3 mounty.py
```

## Usage

### Adding a Share

1. Click the **+** button in the header
2. Enter server address (IP or hostname)
3. Enter share name
4. Enter credentials (username/password)
5. Enter local mount point (e.g., `/mnt/myshare`)
6. Click **Test Connection** to verify
7. Click **Save** to add the share

### Mounting Shares

- **Temporary Mount**: Click the "Mount" button on any share
- **Automount**: Click "Enable Automount" to add to fstab for persistent mounting

### fstab Management

Mounty manages entries in `/etc/fstab` between special markers:

```
### Mounty-Start
//server/share /mnt/myshare cifs credentials=/home/user/.config/mounty/credentials/abc123.cred,uid=1000,gid=1000,_netdev,nofail 0 0
### Mounty-End
```

## Configuration

| Path | Description |
|------|-------------|
| `~/.config/mounty/shares.json` | Saved shares configuration |
| `~/.config/mounty/credentials/` | Credential files (chmod 600) |

## Troubleshooting

### "smbclient not installed"
Install the smbclient package for your distribution.

### "Permission denied" when mounting
Mounting requires elevated privileges. The app uses `pkexec` for privilege escalation.

### Connection timeout
- Check the server is reachable (`ping server-address`)
- Check the share name is correct
- Check firewall allows SMB traffic (ports 139, 445)

## Building for AUR

```bash
# Test local build
cp PKGBUILD.local PKGBUILD
makepkg -si

# For AUR submission, use the main PKGBUILD and update:
# 1. source URL to your GitHub releases
# 2. sha256sums (use: makepkg -g)
# 3. Maintainer info
```

## License

MIT
