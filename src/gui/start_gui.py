import subprocess
import json
import sys
import urllib.parse
from src.drives.find_usb import find_usb

def launch_gui_with_usb_data() -> None:
    usb_devices = find_usb()
    print("Detected USB devices:", usb_devices)

    usb_json = json.dumps(usb_devices)
    encoded_data = urllib.parse.quote(usb_json)

    try:
        subprocess.run([sys.executable, "src/drives/gui.py", encoded_data], check=True)
    except FileNotFoundError as e:
        print(f"Failed to launch GUI: executable or script not found: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"GUI exited with an error (return code {e.returncode}): {e}")
        sys.exit(e.returncode or e)
    except Exception as e:
        print(f"Unexpected error while launching GUI: {e}")
        sys.exit(1)    