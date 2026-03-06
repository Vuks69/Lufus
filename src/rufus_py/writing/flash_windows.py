import subprocess
import os
import glob

def run(cmd):
    subprocess.run(cmd, check=True)

def run_out(cmd) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def _get_wim_size(data_mount) -> int:
    """Check actual install.wim/install.esd size"""
    for pattern in ["install.wim", "install.esd", "INSTALL.WIM", "INSTALL.ESD"]:
        matches = glob.glob(f"{data_mount}/sources/{pattern}")
        if matches:
            return os.path.getsize(matches[0])
    return 0

def _split_wim(data_mount):
    """Split install.wim into 3.8GB chunks for FAT32 compatibility"""
    wim = None
    for pattern in ["install.wim", "INSTALL.WIM"]:
        matches = glob.glob(f"{data_mount}/sources/{pattern}")
        if matches:
            wim = matches[0]
            break
    
    if not wim:
        print("No install.wim found to split")
        return

    print("Splitting install.wim for FAT32 (file > 4GB)...")
    swm_out = wim.replace(".wim", ".swm").replace(".WIM", ".swm")
    run(["sudo", "wimlib-imagex", "split", wim, swm_out, "3800"])
    run(["sudo", "rm", wim])
    print("Split complete")

def flash_windows(device, iso):
    print("Preparing Windows USB")

    run(["sudo", "wipefs", "-a", device])

    # GPT: 512MB FAT32 EFI + rest NTFS data
    sfdisk_script = f"""label: gpt
device: {device}

{device}1 : size=512M, type=U
{device}2 : type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7
"""
    subprocess.run(["sudo", "sfdisk", device], input=sfdisk_script.encode(), check=True)
    run(["sudo", "partprobe"])
    run(["sudo", "udevadm", "settle"])

    efi  = f"{device}1"
    data = f"{device}2"

    # FAT32 EFI partition needs correct label for some firmware
    run(["sudo", "mkfs.vfat", "-F32", "-n", "BOOT", efi])
    run(["sudo", "mkfs.ntfs", "-f", "-L", "WINDOWS", data])

    run(["sudo", "mkdir", "-p", "/tmp/rufus_efi"])
    run(["sudo", "mkdir", "-p", "/tmp/rufus_data"])

    run(["sudo", "mount", efi, "/tmp/rufus_efi"])
    run(["sudo", "mount", data, "/tmp/rufus_data"])

    # Extract full ISO to NTFS data partition
    print("Extracting ISO to data partition...")
    run(["sudo", "7z", "x", iso, "-o/tmp/rufus_data", "-y"])

    # Handle install.wim > 4GB — must split for FAT32 EFI partition copy
    wim_size = _get_wim_size("/tmp/rufus_data")
    print(f"install.wim size: {wim_size / (1024**3):.2f} GB")

    # Copy everything except install.wim to EFI partition
    # EFI partition only needs bootloaders, not the full ISO contents
    print("Setting up EFI partition...")
    
    # Copy EFI bootloader folder
    for efi_dir in ["efi", "EFI"]:
        src = f"/tmp/rufus_data/{efi_dir}"
        if os.path.exists(src):
            run(["sudo", "cp", "-r", src, "/tmp/rufus_efi/"])
            print(f"Copied {efi_dir}/ to EFI partition")
            break
    else:
        print("WARNING: No EFI directory found — may not be UEFI bootable")

    # Copy boot folder to EFI partition
    for boot_dir in ["boot", "BOOT"]:
        src = f"/tmp/rufus_data/{boot_dir}"
        if os.path.exists(src):
            run(["sudo", "cp", "-r", src, "/tmp/rufus_efi/"])
            print(f"Copied {boot_dir}/ to EFI partition")
            break

    # Ensure correct UEFI bootloader path: /EFI/BOOT/BOOTX64.EFI
    _fix_efi_bootloader("/tmp/rufus_efi")

    # Split install.wim on data partition if needed (some tools need it)
    if wim_size > 4 * 1024**3:
        _split_wim("/tmp/rufus_data")

    run(["sudo", "sync"])
    run(["sudo", "umount", "/tmp/rufus_efi"])
    run(["sudo", "umount", "/tmp/rufus_data"])

    print("Windows USB ready")
    return True


def _fix_efi_bootloader(efi_mount):
    """
    Ensure /EFI/BOOT/BOOTX64.EFI exists — required by UEFI spec.
    Windows ISOs put the bootloader at efi/microsoft/boot/efisys.bin
    but UEFI firmware looks for /EFI/BOOT/BOOTX64.EFI as fallback.
    """
    boot_dir = f"{efi_mount}/EFI/BOOT"
    bootx64 = f"{boot_dir}/BOOTX64.EFI"

    # Already correct
    if os.path.exists(bootx64):
        print("BOOTX64.EFI already in place")
        return

    run(["sudo", "mkdir", "-p", boot_dir])

    # Find Microsoft's bootmgfw.efi and copy it as BOOTX64.EFI
    candidates = [
        f"{efi_mount}/EFI/Microsoft/Boot/bootmgfw.efi",
        f"{efi_mount}/efi/microsoft/boot/bootmgfw.efi",
    ]
    for src in candidates:
        if os.path.exists(src):
            run(["sudo", "cp", src, bootx64])
            print(f"Copied {src} -> {bootx64}")
            return

    print("WARNING: Could not find bootmgfw.efi — UEFI boot may fail")
