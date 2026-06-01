import sys
import importlib

print("=" * 60)
print("MATTER SIM ENVIRONMENT CHECKER")
print("=" * 60)

# Check Python version
print(f"Current Python version: {sys.version.split(' ')[0]}")
if sys.version_info < (3, 8):
    print("WARNING: Python version should be 3.8 or higher.")
else:
    print("Python Status: OK (Valid)")

print("-" * 60)
print("CHECKING REQUIRED LIBRARIES:")

required_packages = [
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("ase", "ase"),
    ("phonopy", "phonopy"),
    ("torch", "torch"),
    ("loguru", "loguru"),
    ("customtkinter", "customtkinter"),
    ("PIL", "pillow"), # imported as PIL but installed as pillow
    ("mattersim", "mattersim")
]

missing_packages = []

for import_name, install_name in required_packages:
    try:
        module = importlib.import_module(import_name)
        # Try to get version if available
        version = getattr(module, "__version__", "unknown")
        print(f"[OK] Installed: {install_name} (version {version})")
    except ImportError:
        print(f"[  ] MISSING:   {install_name}")
        missing_packages.append(install_name)

print("-" * 60)
if not missing_packages:
    print("CONCLUSION: All required libraries are installed!")
    print("The environment is ready to run the program. No further installation needed.")
else:
    print("CONCLUSION: You need to install the following MISSING libraries:")
    print("\n    pip install " + " ".join(missing_packages) + "\n")

print("=" * 60)
input("Press Enter to exit...")
