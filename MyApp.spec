# -*- mode: python ; coding: utf-8 -*-
from kivy_deps import sdl2, glew

block_cipher = None

a = Analysis(['MyApp.py'],
             pathex=[],
             binaries=[],
             datas=[('MyApp.kv', '.')],
             hiddenimports=['plyer.facades.filechooser'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

a.datas += [(r'Images\4882066.jpg',r'C:\Users\Adm-7C\PycharmProjects\odimV2\Images\4882066.jpg', "DATA")]
a.datas += [(r'Images\bomb.png',r'C:\Users\Adm-7C\PycharmProjects\odimV2\Images\bomb.png', "DATA")]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
          name='ODIM',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon=r'C:\Users\Adm-7C\PycharmProjects\odimV2\Images\bomb.ico')

# icone = https://www.flaticon.com/free-icon/bomb_595582#
# commande terminal setup  pyinstaller 4.10 = pyinstaller.exe --onedir .\MyApp.spec
# fichier de version =  create-version-file version.yaml --outfile ODIM_version.txt "ne fonctionne pas in fine"
