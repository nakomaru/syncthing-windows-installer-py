# Syncthing User-Level Installer for Windows

A direct Python script to install and update [Syncthing](https://syncthing.net/) for the current user.

## Features

- **User-Level Install:** Puts the binary in `%LocalAppData%\Programs\Syncthing`.
- **Background Startup:** Sets up a Scheduled Task and a VBS wrapper to run Syncthing invisibly at logon.
- **Simple Updater:** Run the script anytime to check for and install updates from GitHub.
- **Firewall Sync:** Automatically updates the `syncthing.exe` firewall rules to point to your user install path.
- **Clean Uninstall:** Use the `--uninstall` flag to remove the program, tasks, and firewall rules while keeping your sync data.

## Credits

This tool implements the **Non-Administrative (Current User) Installation** logic inspired by [Bill Stewart's Syncthing Windows Setup](https://github.com/Bill-Stewart/SyncthingWindowsSetup). It provides a transparent, script-based alternative to compiled installers.

## Usage

**Administrator privileges are required** for the script to manage the Firewall and Task Scheduler. The script will automatically prompt for elevation if needed.

### Install or Update
Run this from your **normal user** terminal. The script will handle elevation for you.
```powershell
python setup_syncthing.py
```

### Uninstall
This removes the binary, the logon task, and the firewall rules. It **does not** delete your configuration or synced folders.
```powershell
python setup_syncthing.py --uninstall
```

## How it Works

1. **Version Check:** Compares your local binary against the latest release on GitHub.
2. **Binary Install:** Downloads and extracts `syncthing.exe` to your user programs folder.
3. **Logon Persistence:** Creates a root-level Scheduled Task that uses `wscript.exe` and a silent VBS launcher.
4. **Network:** Updates or creates inbound firewall rules for `syncthing.exe` to ensure local discovery works.
