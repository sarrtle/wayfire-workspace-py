need patchelf installed
```bash
sudo pacman -S patchelf
```

sync:
```bash
uv sync
```

compile:
> [!NOTE]
> You might want to use the venv directly instead of uvx because it can't find dependencies and it is using some sort of global dependencies that this project doesn't need.
```bash
.venv/bin/python3 -m nuitka \
  --standalone \
  --onefile \
  --static-libpython=yes \
  --lto=yes \
  --clang \
  --remove-output \
  --output-dir=build \
  utility.py
```

```bash
.venv/bin/python3 -m nuitka \
  --standalone \
  --onefile \
  --static-libpython=yes \
  --lto=yes \
  --clang \
  --remove-output \
  --output-dir=build \
  listener.py
```
