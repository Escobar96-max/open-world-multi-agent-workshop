import os
import subprocess
from pathlib import Path

def create_desktop_shortcut():
    userprofile = os.environ.get("USERPROFILE", "C:\\Users\\Asus")
    desktop = Path(userprofile) / "Desktop"
    c2_dir = Path(__file__).resolve().parent
    target_bat = c2_dir / "Start_C2.bat"
    
    # Visual VBS Script to create shortcut with zero dependencies
    vbs_code = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop}\\Antigravity C2 Executive Desk.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "{c2_dir}"
oLink.Description = "Antigravity Unified C2 Executive Desk (Dual-Executive Orion Prime & Nova)"
oLink.IconLocation = "%SystemRoot%\\System32\\shell32.dll,220"
oLink.Save
'''
    temp_vbs = Path(os.environ.get("TEMP", "C:\\Windows\\Temp")) / "make_c2_shortcut.vbs"
    temp_vbs.write_text(vbs_code, encoding="utf-8")
    
    res = subprocess.run(["cscript", "//Nologo", str(temp_vbs)], capture_output=True, text=True)
    shortcut_path = desktop / "Antigravity C2 Executive Desk.lnk"
    
    if shortcut_path.exists():
        print(f"SUCCESS: Desktop shortcut created at {shortcut_path}")
        return True
    else:
        print(f"FAILED: Return code {res.returncode}. Output: {res.stderr or res.stdout}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
