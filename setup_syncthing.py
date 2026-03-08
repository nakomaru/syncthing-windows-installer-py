import os
import sys
import json
import urllib.request
import zipfile
import subprocess
import platform
import ctypes
import re
import argparse
import shutil
from pathlib import Path

# --- DIRECTORY SETUP ---
INSTALL_DIR = Path(os.environ['LOCALAPPDATA']) / "Programs" / "Syncthing"
CONFIG_DIR = Path(os.environ['LOCALAPPDATA']) / "Syncthing"
EXE_PATH = INSTALL_DIR / "syncthing.exe"
VBS_PATH = INSTALL_DIR / "silent_start.vbs"
FIREWALL_RULE_NAME = "syncthing.exe"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    script = os.path.abspath(sys.argv[0])
    # Pass through any arguments (like --uninstall)
    args_str = " ".join(f'"{a}"' for a in sys.argv[1:])
    params = f'/k python "{script}" {args_str}'
    print("Elevating to Administrator to manage Firewall and Tasks...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", params, None, 1)

def get_local_version():
    if not EXE_PATH.exists():
        return None
    try:
        result = subprocess.run([str(EXE_PATH), "--version"], capture_output=True, text=True)
        match = re.search(r'v(\d+\.\d+\.\d+)', result.stdout)
        return match.group(0) if match else None
    except:
        return None

def get_latest_version():
    print("Checking GitHub for the latest version...")
    url = "https://api.github.com/repos/syncthing/syncthing/releases/latest"
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())['tag_name']
    except Exception as e:
        print(f"FAILED to check GitHub: {e}")
        return None

def install_binary(version):
    machine = platform.machine().lower()
    arch = "amd64" if "amd64" in machine or "x86_64" in machine else "386"
    zip_name = f"syncthing-windows-{arch}-{version}.zip"
    url = f"https://github.com/syncthing/syncthing/releases/download/{version}/{zip_name}"
    temp_zip = Path(os.environ['TEMP']) / zip_name

    print(f"Downloading {zip_name}...")
    try:
        urllib.request.urlretrieve(url, temp_zip)
    except Exception as e:
        print(f"FAILED to download: {e}")
        return False

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting to {INSTALL_DIR}...")
    try:
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("syncthing.exe"):
                    with zip_ref.open(member) as source, open(EXE_PATH, "wb") as target:
                        target.write(source.read())
                    break
        os.remove(temp_zip)
        print("Binary extracted successfully.")
        return True
    except Exception as e:
        print(f"FAILED to extract: {e}")
        return False

def manage_firewall(remove=False):
    if remove:
        print("Removing Firewall Rules...")
        subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={FIREWALL_RULE_NAME}"], 
                       capture_output=True)
        return

    print("Synchronizing Firewall Rules...")
    # Update existing "syncthing.exe" rules to our path
    cmd = [
        "netsh", "advfirewall", "firewall", "set", "rule",
        f"name={FIREWALL_RULE_NAME}",
        "new",
        "program=" + str(EXE_PATH)
    ]
    try:
        # This will update BOTH the TCP and UDP rules at once
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"SUCCESS: Existing '{FIREWALL_RULE_NAME}' firewall rules updated to current path.")
    except Exception as e:
        print(f"No existing '{FIREWALL_RULE_NAME}' rules found to update. Creating a new one...")
        # Fallback if the rules don't exist
        fallback_cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={FIREWALL_RULE_NAME}",
            "dir=in",
            "action=allow",
            "program=" + str(EXE_PATH),
            "enable=yes",
            "profile=any"
        ]
        subprocess.run(fallback_cmd, check=True, capture_output=True)

def manage_task(remove=False):
    user_name = os.environ.get('USERNAME', os.getlogin())
    task_name = f"Syncthing_Logon_{user_name}"
    
    if remove:
        print(f"Deleting Scheduled Task: {task_name}")
        subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)
        return

    # Create VBS Wrapper
    vbs_code = f'CreateObject("WScript.Shell").Run """{EXE_PATH}"" --no-browser --no-restart", 0, False'
    with open(VBS_PATH, "w") as f:
        f.write(vbs_code)

    print(f"Registering Scheduled Task for {user_name}...")
    cmd = [
        "schtasks", "/Create", "/F", 
        "/TN", task_name, 
        "/TR", f"wscript.exe \"{VBS_PATH}\"", 
        "/SC", "ONLOGON", 
        "/IT"
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        # Start the task immediately
        print("Starting Syncthing via Task Scheduler...")
        subprocess.run(["schtasks", "/Run", "/TN", task_name], check=True, capture_output=True)
        print("Syncthing is now running silently.")
    except Exception as e:
        print(f"FAILED to manage scheduled task: {e}")

def uninstall():
    print("--- UNINSTALLING SYNCTHING ---")
    # 1. Kill any existing instances
    subprocess.run("taskkill /F /IM syncthing.exe", shell=True, capture_output=True)
    
    # 2. Cleanup Task and Firewall
    manage_task(remove=True)
    manage_firewall(remove=True)
    
    # 3. Remove Program Files (Binary and VBS)
    if INSTALL_DIR.exists():
        print(f"Removing program files at {INSTALL_DIR}...")
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    
    print("\nDONE: Program and tasks removed. Configuration folder was NOT deleted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Syncthing Setup/Update Utility")
    parser.add_argument("--uninstall", action="store_true", help="Remove Syncthing program, firewall rules, and tasks.")
    args = parser.parse_args()

    if not is_admin():
        relaunch_as_admin()
        sys.exit(0)

    if args.uninstall:
        uninstall()
        sys.exit(0)

    print(f"--- SYNCTHING SETUP & UPDATE ---")
    
    local_ver = get_local_version()
    latest_ver = get_latest_version()
    
    if local_ver != latest_ver:
        print(f"Update/Install needed: {local_ver} -> {latest_ver}")
        # Kill running instance before updating
        subprocess.run("taskkill /F /IM syncthing.exe", shell=True, capture_output=True)
        if not install_binary(latest_ver):
            sys.exit(1)
        if not (CONFIG_DIR / "config.xml").exists():
            print("Generating initial configuration...")
            subprocess.run([str(EXE_PATH), "generate", f"--home={CONFIG_DIR}"], capture_output=True)
    else:
        print(f"Already up to date ({local_ver}).")

    manage_firewall()
    manage_task()
    
    print("\nDONE: Syncthing is running in the background.")
    print("Access the Web UI at: http://127.0.0.1:8384")
    print("You can close this window now.")
