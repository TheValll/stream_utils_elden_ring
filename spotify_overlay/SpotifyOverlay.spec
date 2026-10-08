# -*- mode: python ; coding: utf-8 -*-
import os
import sys


a = Analysis(
    ['overlay.py'],
    pathex=[os.path.join(sys.base_prefix, 'Lib')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter', 'tkinter.font',
        'winrt.windows.foundation', 'winrt.windows.foundation.collections',
        'winrt.windows.system',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SpotifyOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
