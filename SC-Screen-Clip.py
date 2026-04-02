# sc_clipboard_toast_watcher.py
# Watches a folder for new screenshots, copies each to the clipboard,
# crops & resizes a centred square, and shows a Windows toast with the thumbnail.

import io
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, List

from PIL import Image, ImageGrab
from watchfiles import Change, watch

# --- Configuration ---
APP_ID = os.environ.get("APP_ID", "JAF.SCShots")  # AUMID-like identifier
WATCH_DIRS = [
    Path(os.environ.get("WATCH_DIR", r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\screenshots")),
    Path(os.environ.get("WATCH_DIR", r"C:\Program Files\Roberts Space Industries\StarCitizen\PTU\screenshots")),
]
EXTS = {".png", ".jpg", ".jpeg", ".webp"}
TOAST_PX = int(os.environ.get("TOAST_PX", "256"))  # square toast image size
FORCE_POWERSHELL = False

# --- Clipboard (Windows) ---
# Requires pywin32
import win32clipboard as wcb
import win32con


def pil_image_to_dib_bytes(img: Image.Image) -> bytes:
    """
    Convert a PIL Image to CF_DIB byte payload (BMP without 14-byte file header).
    """
    with io.BytesIO() as output:
        # Use 32-bit for wide compatibility; convert to BGRA via BMP encoder
        img.convert("RGBA").save(output, format="BMP")
        data = output.getvalue()
    # Strip BMP file header (first 14 bytes) to get DIB
    return data[14:]


def copy_image_to_clipboard(img: Image.Image) -> None:
    """
    Put a PIL image onto the Windows clipboard as CF_DIB.
    """
    dib = pil_image_to_dib_bytes(img)
    # CF_DIB expects global memory; pywin32 handles allocation when given bytes.
    wcb.OpenClipboard()
    try:
        wcb.EmptyClipboard()
        wcb.SetClipboardData(win32con.CF_DIB, dib)
    finally:
        wcb.CloseClipboard()


def copy_file_image_to_clipboard(path: Path) -> None:
    """
    Open an image file robustly and push to clipboard.
    """
    with Image.open(path) as img:
        # Ensure the file is fully decoded before closing
        img.load()
        copy_image_to_clipboard(img)


# --- Image utilities ---

def centre_square_crop(img: Image.Image) -> Image.Image:
    """
    Crop a centred square from any image.
    """
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def make_toast_thumbnail_from_clipboard(max_px: int) -> Optional[Path]:
    """
    Read current clipboard image (bitmap or file list), centre-square crop, resize,
    save PNG to a temp folder, return its path; None if no image found.
    """
    # PIL can return an Image or a list of file paths
    src = ImageGrab.grabclipboard()
    if src is None:
        return None

    if isinstance(src, list):
        # Prefer the first valid image file
        for p in src:
            pth = Path(p)
            if pth.is_file() and pth.suffix.lower() in EXTS:
                try:
                    with Image.open(pth) as im:
                        im.load()
                        img = im.convert("RGBA")
                        break
                except Exception:
                    continue
        else:
            return None
    elif isinstance(src, Image.Image):
        img = src.convert("RGBA")
    else:
        return None

    # Centre-square crop then resize
    sq = centre_square_crop(img)
    sq.thumbnail((max_px, max_px), Image.LANCZOS)

    outdir = Path(tempfile.gettempdir()) / "sc_toast"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "thumb.png"
    sq.save(out, "PNG")
    return out


# --- Toast notifications ---
def toast_via_burnttoast(image_path: Path, title: str, body: str) -> bool:
    """
    Show a toast using the BurntToast PowerShell module.
    Works even on older BurntToast versions (no New-BTAppId needed).
    Uses -AppLogo for a small square image.
    """
    # We import the module and call New-BurntToastNotification.
    # -AppId is optional; omit it to avoid version differences.
    ps = f"""
$ErrorActionPreference = 'Stop'
Import-Module BurntToast -ErrorAction Stop
$img = "{str(image_path.resolve())}"
New-BurntToastNotification -Text @({title!r}, {body!r}) -AppLogo $img | Out-Null
"""
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
            check=True, capture_output=True, text=True
        )
        return True
    except Exception as e:
        print(f"BurntToast toast failed: {e}")
        return False

def file_uri(p: Path) -> str:
    return "file:///" + str(p.resolve()).replace("\\", "/")


def toast_via_winsdk(image_path: Path, title: str, body: str) -> bool:
    try:
        from winsdk.windows.ui.notifications import ToastNotificationManager, ToastNotification
        from winsdk.windows.data.xml.dom import XmlDocument
    except Exception:
        return False

    xml = f"""
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{title}</text>
      <text>{body}</text>
      <image placement="inline" src="{file_uri(image_path)}"/>
    </binding>
  </visual>
</toast>
""".strip()

    try:
        doc = XmlDocument()
        doc.load_xml(xml)
        notifier = ToastNotificationManager.create_toast_notifier(APP_ID)
        notifier.show(ToastNotification(doc))
        return True
    except Exception as e:
        print("WinSDK toast failed:", e)
        return False


def toast_via_powershell(image_path: Path, title: str, body: str) -> bool:
    ps = rf'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType=WindowsRuntime]

$xml = @"
<toast>
  <visual>
    <binding template='ToastGeneric'>
      <text>{title}</text>
      <text>{body}</text>
      <image placement='inline' src='{file_uri(image_path)}'/>
    </binding>
  </visual>
</toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_ID}')
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
$notifier.Show($toast)
'''
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception as e:
        print("PowerShell toast failed:", e)
        return False

def show_toast_with_thumbnail(title: str, body: str, size_px: int) -> bool:
    thumb = make_toast_thumbnail_from_clipboard(size_px)
    if not thumb:
        print("No image on clipboard to display.", flush=True)
        return False

    # 1) Try BurntToast (most reliable on your machine)
    if toast_via_burnttoast(thumb, title, body):
        return True

    # 2) Fall back to WinRT (winsdk) …
    if not FORCE_POWERSHELL and toast_via_winsdk(thumb, title, body):
        return True

    # 3) … or raw PowerShell WinRT path
    return toast_via_powershell(thumb, title, body)

# --- Filesystem watching ---

def file_is_stable(path: Path, checks: int = 4, interval: float = 0.25) -> bool:
    """
    Consider a file 'stable' when its size stops changing and PIL can open it.
    """
    last = -1
    for _ in range(checks):
        if not path.exists():
            return False
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last and size > 0:
            # size steady; do a quick decode test
            try:
                with Image.open(path) as im:
                    im.verify()
                return True
            except Exception:
                pass
        last = size
        time.sleep(interval)
    # final decode attempt
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def handle_new_image(path: Path) -> None:
    """
    Copy image to clipboard and show toast with centred square thumbnail.
    """
    try:
        copy_file_image_to_clipboard(path)
        print(f"Copied to clipboard: {path.name}")
        # Produce toast from clipboard image (as requested)
        ok = show_toast_with_thumbnail(
            title="Star Citizen Screenshot",
            body=path.name,
            size_px=TOAST_PX,
        )
        if ok:
            print(f"Toast shown: {path.name}")
        else:
            print(f"Failed to show toast for: {path.name}")
    except Exception as e:
        print(f"Error handling {path}: {e}")


def watch_folders(folders: List[Path]) -> None:
    for f in folders:
        f.mkdir(parents=True, exist_ok=True)
    print(f"Watching:\n {'\n'.join(['\t'+str(f) for f in folders])}")
    for changes in watch(*folders):
        for change, p in changes:
            pth = Path(p)
            if change == Change.added and pth.suffix.lower() in EXTS:
                if file_is_stable(pth):
                    handle_new_image(pth)


# --- Entry point ---

if __name__ == "__main__":
    try:
        watch_folders(WATCH_DIRS)
    except KeyboardInterrupt:
        print("Stopped.")
