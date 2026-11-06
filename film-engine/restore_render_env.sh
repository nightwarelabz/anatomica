#!/bin/bash
# Eevee headless needs EGL; VM replacements wipe system packages - reinstall from the kept debs.
sudo dpkg -i ~/workspace/debs/libegl1*.deb ~/workspace/debs/libegl-mesa0*.deb ~/workspace/debs/libgl1-mesa-dri*.deb
