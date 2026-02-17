import sys
import platform

with open("env_info.txt", "w") as f:
    f.write(f"Python Version: {sys.version}\n")
    f.write(f"Platform: {platform.platform()}\n")
    f.write(f"Executable: {sys.executable}\n")
