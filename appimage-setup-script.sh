#!/usr/bin/env bash
set -e

echo "=== Lufus AppImage build script ==="

APP_NAME="Lufus"
PY_ENTRY="src/lufus/__main__.py"

echo "== Checking python venv =="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "== Installing Python dependencies =="
pip install --upgrade pip
pip install pyinstaller pyqt6 psutil pyudev

echo "== Downloading linuxdeploy if missing =="

if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f linuxdeploy-plugin-qt-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous/linuxdeploy-plugin-qt-x86_64.AppImage
    chmod +x linuxdeploy-plugin-qt-x86_64.AppImage
fi

echo "== Cleaning old builds =="
rm -rf build dist

echo "== Building binary with PyInstaller =="

pyinstaller "$PY_ENTRY" \
    --name lufus \
    --windowed \
    --paths src \
    --collect-all PyQt6 \
    --collect-all psutil \
    --hidden-import lufus.drives.autodetect_usb \
    --hidden-import lufus.drives.states \
    --add-data "src/lufus/gui:lufus/gui" \
    --noconfirm

echo "== Preparing AppDir =="
mkdir -p AppDir/usr/bin
rm -rf AppDir/usr/bin/*
cp -r dist/lufus/* AppDir/usr/bin/

echo "== Creating desktop file if missing =="

if [ ! -f AppDir/lufus.desktop ]; then
cat > AppDir/lufus.desktop <<EOF
[Desktop Entry]
Name=Lufus
Exec=lufus
Icon=lufus
Type=Application
Categories=Utility;
EOF
fi

echo "== Setting up icon =="

mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

if [ -f src/lufus/gui/assets/lufus.png ]; then
    cp src/lufus/gui/assets/lufus.png AppDir/usr/share/icons/hicolor/256x256/apps/lufus.png
elif [ -f AppDir/lufus.png ]; then
    cp AppDir/lufus.png AppDir/usr/share/icons/hicolor/256x256/apps/lufus.png
else
    if command -v convert >/dev/null 2>&1; then
        convert -size 256x256 xc:gray AppDir/usr/share/icons/hicolor/256x256/apps/lufus.png
    else
        touch AppDir/usr/share/icons/hicolor/256x256/apps/lufus.png
    fi
fi

echo "== Verifying build contents =="
ls AppDir/usr/bin

echo "== Building AppImage =="

ARCH=x86_64 ./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    --executable AppDir/usr/bin/lufus \
    --desktop-file AppDir/lufus.desktop \
    --output appimage

echo ""
echo "✅ Build complete!"
echo "Output:"
ls *.AppImage
