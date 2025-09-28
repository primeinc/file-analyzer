#!/usr/bin/env python3
"""
Robust Path Utilities

Handles cross-platform path normalization with proper runtime detection
and sanitization using pathvalidate. No more guessing what planet we're on.
"""

import os
import sys
import platform
import re
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Literal
from pathvalidate import sanitize_filename, sanitize_filepath

PathFlavor = Literal["windows", "posix"]

# Regex patterns for path flavor detection
_WIN_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_WIN_UNC = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")

def is_windows() -> bool:
    """Check if running on Windows."""
    return os.name == "nt"

def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"

def is_linux() -> bool:
    """Check if running on Linux (excluding WSL)."""
    return sys.platform.startswith("linux") and not is_wsl()

def is_wsl() -> bool:
    """Check if running under WSL. WSL lies and says it's Linux, so poke harder."""
    if not sys.platform.startswith("linux"):
        return False
    
    # WSL sets these environment variables reliably
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    
    try:
        rel = platform.uname().release.lower()
        ver = platform.uname().version.lower()
        return "microsoft" in rel or "microsoft" in ver or "wsl" in ver
    except Exception:
        return False

# Runtime detection - detect once, use everywhere
RUNTIME = {
    "windows": is_windows(),
    "macos": is_macos(),
    "linux": is_linux(),
    "wsl": is_wsl(),
}

def guess_flavor(p: str) -> PathFlavor:
    """
    Detect path flavor from the path string itself.
    Don't assume input matches runtime - people paste paths between systems.
    """
    if _WIN_DRIVE.match(p) or _WIN_UNC.match(p):
        return "windows"
    
    # /mnt/c/... is Windows-on-WSL; treat as windows-origin
    if p.startswith("/mnt/") and len(p) >= 6 and p[5].isalpha() and p[6] in ("/", "\\"):
        return "windows"
    
    return "posix"

def win_to_wsl_posix(p: str) -> str:
    """Convert Windows path to WSL POSIX format. C:\\Users\\me -> /mnt/c/Users/me"""
    pw = PureWindowsPath(p)
    
    if str(pw).startswith("\\\\"):  # UNC path
        # \\server\share\dir -> /mnt/unc/server/share/dir (WSL convention)
        parts = [x for x in pw.parts if x not in ("\\", "/")]
        if len(parts) >= 2:
            return "/mnt/unc/" + "/".join([parts[0].lstrip("\\/"), *parts[1:]])
        return "/mnt/unc/" + parts[0].lstrip("\\/") if parts else "/mnt/unc/"
    
    # Regular drive path
    if pw.drive:
        drive = pw.drive[:-1].lower()  # 'C:' -> 'c'
        rest = "/".join(pw.parts[1:]) if len(pw.parts) > 1 else ""
        return f"/mnt/{drive}/{rest}".rstrip("/") or f"/mnt/{drive}"
    
    # Fallback for relative paths
    return "/" + "/".join(pw.parts)

def wsl_posix_to_win(p: str) -> str:
    """Convert WSL POSIX path to Windows format. /mnt/c/Users/me -> C:\\Users\\me"""
    if p.startswith("/mnt/") and len(p) > 6 and p[5].isalpha() and p[6] == "/":
        drive = p[5].upper()
        rest = p[7:]
        return str(PureWindowsPath(f"{drive}:\\" + rest))
    
    # Handle UNC paths
    if p.startswith("/mnt/unc/"):
        rest = p[len("/mnt/unc/"):]
        parts = rest.split("/")
        if len(parts) >= 2:
            return "\\\\" + parts[0] + "\\" + parts[1] + ("\\" + "\\".join(parts[2:]) if len(parts) > 2 else "")
    
    raise ValueError(f"Not a WSL-mounted Windows path: {p}")

def normalize_to_local(p: str, root: Path | None = None) -> Path:
    """
    Normalize path to current OS canonical form with proper sanitization.
    
    Args:
        p: Input path string
        root: Optional root directory to resolve relative paths and enforce jail
        
    Returns:
        Normalized Path object
        
    Raises:
        ValueError: If path escapes allowed root
    """
    src_flavor = guess_flavor(p)
    
    # Convert to current-OS flavor if needed
    if RUNTIME["windows"] and src_flavor == "posix":
        if p.startswith("/mnt/"):
            try:
                p = wsl_posix_to_win(p)
            except ValueError:
                # Not a WSL path, treat as regular POSIX
                pass
    elif (RUNTIME["wsl"] or RUNTIME["linux"] or RUNTIME["macos"]) and src_flavor == "windows":
        p = win_to_wsl_posix(p)
    
    # Sanitize by the filesystem we're actually going to touch
    platform_name = "Windows" if RUNTIME["windows"] else "POSIX"
    p = sanitize_filepath(p, platform=platform_name)
    
    # Create Path object
    path_obj = Path(p)
    
    # Resolve relative paths against safe root if given
    if not path_obj.is_absolute() and root:
        path_obj = root / path_obj
    
    # Canonicalize
    try:
        path_obj = path_obj.resolve()
    except (OSError, RuntimeError):
        # Fallback for broken symlinks or permission issues
        path_obj = path_obj.absolute()
    
    # Enforce jail if root is set
    if root:
        root = root.resolve()
        try:
            path_obj.relative_to(root)
        except ValueError:
            raise ValueError(f"Path escapes allowed root: {path_obj} not under {root}")
    
    return path_obj

def sanitize_filename_safe(name: str) -> str:
    """Sanitize filename for current platform."""
    platform_name = "Windows" if RUNTIME["windows"] else "POSIX"
    return sanitize_filename(name, platform=platform_name)

def get_safe_path(base_dir: Path, *parts: str) -> Path:
    """
    Create a safe path under base_dir by joining sanitized parts.
    
    Args:
        base_dir: Base directory (must exist)
        *parts: Path components to join
        
    Returns:
        Safe path under base_dir
    """
    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize each part
    safe_parts = []
    for part in parts:
        if part:  # Skip empty parts
            safe_parts.append(sanitize_filename_safe(part))
    
    # Join and normalize
    if safe_parts:
        result_path = base_dir / Path(*safe_parts)
        return normalize_to_local(str(result_path), root=base_dir)
    else:
        return base_dir

def ensure_dir_exists(path: Path) -> Path:
    """Ensure directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path

# Runtime info for debugging
def get_runtime_info() -> dict:
    """Get runtime environment information for debugging."""
    return {
        "runtime": RUNTIME,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
        },
        "os": {
            "name": os.name,
            "cwd": os.getcwd(),
            "env_vars": {
                "WSL_INTEROP": os.environ.get("WSL_INTEROP"),
                "WSL_DISTRO_NAME": os.environ.get("WSL_DISTRO_NAME"),
                "PATH": os.environ.get("PATH", "")[:200] + "..." if len(os.environ.get("PATH", "")) > 200 else os.environ.get("PATH", ""),
            }
        }
    }