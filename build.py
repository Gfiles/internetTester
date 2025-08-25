import os
import subprocess
from datetime import datetime

# --- Configuration ---
# Import version from the main app to keep it in one place.
from app import VERSION

APP_NAME = "InternetTester"
DEVELOPER_NAME = "Gavin Goncalves"  # <-- IMPORTANT: Change this to your name/company
MAIN_SCRIPT = "app.py"
FILE_DESCRIPTION = "Internet Speed Test and Logging Tool"

# --- Generate Version File ---
# PyInstaller uses this file to add metadata to the .exe.
# The version format is (major, minor, patch, build).
# We'll use the date for the version numbers.
now = datetime.now()
major, minor, patch = map(int, VERSION.split('.'))
build = now.hour * 10000 + now.minute * 100 + now.second

version_info_content = f"""
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{DEVELOPER_NAME}'),
        StringStruct(u'FileDescription', u'{FILE_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{VERSION}.{build}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'© {DEVELOPER_NAME}. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{VERSION}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

version_file_path = "version.txt"
with open(version_file_path, "w", encoding="utf-8") as f:
    f.write(version_info_content)

print(f"Generated '{version_file_path}' with version {VERSION}")

# --- PyInstaller Build Command ---
pyinstaller_command = [
    'pyinstaller', '--name', APP_NAME, '--onefile', '--clean',
    '--version-file', version_file_path,
    '--add-data', 'templates;templates', '--add-data', 'static;static',
    '--hidden-import', 'apscheduler.schedulers.background',
    '--hidden-import', 'apscheduler.executors.default',
    '--hidden-import', 'apscheduler.jobstores.default',
    MAIN_SCRIPT
]

print("\nRunning PyInstaller...")
try:
    subprocess.run(pyinstaller_command, check=True, text=True, capture_output=True)
    print("Build successful!")
    print(f"Executable created at: {os.path.join('dist', f'{APP_NAME}.exe')}")
except subprocess.CalledProcessError as e:
    print(f"Build failed!\nError:\n{e.stderr}")
finally:
    if os.path.exists(version_file_path):
        os.remove(version_file_path)