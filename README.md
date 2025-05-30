need patchelf installed
sudo pacman -S patchelf

sync:
uv sync

compile:
uvx nuitka \
  --standalone \
  --onefile \
  --static-libpython=yes \
  --lto=yes \
  --clang \
  --remove-output \
  --output-dir=build \
  utility.py

uvx nuitka \
  --standalone \
  --onefile \
  --static-libpython=yes \
  --lto=yes \
  --clang \
  --remove-output \
  --output-dir=build \
  listener.py
