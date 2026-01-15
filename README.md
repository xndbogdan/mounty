# Mounty

A GTK4 application for managing SMB/CIFS network shares on Linux.

![Screenshot](https://img.shields.io/badge/GTK-4.0-green) ![License](https://img.shields.io/badge/License-MIT-blue)

## Features

- Add and manage network shares
- Test connections before saving
- Mount/unmount shares with one click
- Automount via fstab integration
- Secure credential storage

## Installation

### Arch Linux (AUR)
```bash
yay -S mounty
```

### From Source
```bash
# Dependencies
sudo pacman -S python-gobject gtk4 libadwaita smbclient cifs-utils polkit

# Run
python3 mounty.py
```

## License

MIT
