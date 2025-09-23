"""
주얼리 AI 생성 시스템 - py2app 설정 파일
macOS .app 번들 생성용
"""
from setuptools import setup

APP = ['ui.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',  # 아이콘 파일이 있다면
    'plist': {
        'CFBundleName': "JewelryAI",
        'CFBundleDisplayName': "JewelryAI",
        'CFBundleIdentifier': "com.jewelryai.app",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHighResolutionCapable': True,
    },
    'packages': ['src'],
    'includes': [
        'sys',
        'os',
        'pathlib',
        'json',
        'datetime',
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'jaraco.text',
        'jaraco',
        'pkg_resources',
    ],
    'excludes': [
        'tkinter',
        'matplotlib'
        'numpy',
        'scipy',
        'pytest',
        'IPython',
        'jupyter',
    ],
}

setup(
    name="JewelryAI",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)