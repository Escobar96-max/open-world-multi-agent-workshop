"""
Automated Desktop Shortcut Creation Script
Creates a native Windows .lnk shortcut on the user's Desktop for one-click C2 Command Deck launch.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path


def get_desktop_path() -> Path:
    """Resolve the active user Desktop path."""
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        user_profile = str(Path.home())

    candidates = [
        Path(user_profile) / "Desktop",
        Path(user_profile) / "OneDrive" / "Desktop",
        Path.home() / "Desktop",
    ]

    for p in candidates:
        if p.exists() and p.is_dir():
            return p

    # Fallback default
    fallback = Path(user_profile) / "Desktop"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def create_shortcut(target_bat: Path, project_dir: Path, desktop_dir: Path) -> Path:
    """Create Windows .lnk shortcut using WScript.Shell via temporary VBScript."""
    shortcut_path = desktop_dir / "C2 Command Deck.lnk"
    
    # Select executive icon from shell32 or imageres
    icon_location = r"C:\Windows\System32\shell32.dll,220"
    if not Path(r"C:\Windows\System32\shell32.dll").exists():
        icon_location = r"C:\Windows\System32\imageres.dll,109"

    vbs_content = f"""
Set WshShell = CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{shortcut_path}")
Shortcut.TargetPath = "{target_bat}"
Shortcut.WorkingDirectory = "{project_dir}"
Shortcut.WindowStyle = 1
Shortcut.Description = "Launch Unified C2 Executive Platform (Orion & Nova)"
Shortcut.IconLocation = "{icon_location}"
Shortcut.Save
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".vbs", delete=False) as vbs_file:
        vbs_file.write(vbs_content)
        vbs_temp_path = vbs_file.name

    try:
        cmd = ["cscript", "//nologo", vbs_temp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    finally:
        try:
            os.remove(vbs_temp_path)
        except OSError:
            pass

    return shortcut_path


def main():
    print("===================================================================")
    print("  AUTOMATED DESKTOP SHORTCUT INSTALLER")
    print("  Target: Unified C2 Executive Platform (Orion & Nova)")
    print("===================================================================")

    project_dir = Path(__file__).resolve().parent
    target_bat = project_dir / "Start_C2.bat"

    if not target_bat.exists():
        print(f"[Error] Target launcher batch file not found at: {target_bat}")
        sys.exit(1)

    desktop_dir = get_desktop_path()
    print(f"[Info] Detected active Windows Desktop: {desktop_dir}")
    print(f"[Info] Target launcher path: {target_bat}")
    print(f"[Info] Working directory: {project_dir}")

    shortcut_path = create_shortcut(target_bat, project_dir, desktop_dir)

    if shortcut_path.exists():
        size = shortcut_path.stat().st_size
        print("\n[SUCCESS] Desktop shortcut created successfully!")
        print(f"  Location: {shortcut_path}")
        print(f"  Size: {size} bytes")
        print("  Status: READY FOR DOUBLE-CLICK EXECUTION")
        print("===================================================================")
        sys.exit(0)
    else:
        print("\n[Error] Shortcut file was not created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
