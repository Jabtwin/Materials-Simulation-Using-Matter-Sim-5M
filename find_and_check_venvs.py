import os
import subprocess
import sys

def main():
    print("=" * 60)
    print("SEARCHING FOR VIRTUAL ENVIRONMENTS...")
    print("This script ONLY searches and checks. It does NOT install anything.")
    print("This process may take a few minutes. Please wait...")
    print("=" * 60)

    # Start searching from the current User directory (e.g., C:\Users\hm-gpham)
    user_dir = os.environ.get("USERPROFILE", "C:\\")
    
    # Skip system or heavy directories to speed up the search
    exclude_dirs = {
        'AppData', 'Application Data', 'Local Settings', 'Windows', 
        'Program Files', 'Program Files (x86)', '.cache', 'node_modules',
        '.git', 'anaconda3', 'miniconda3'
    }
    
    found_venvs = []
    
    print(f"Scanning directory: {user_dir}")
    
    # Walk through the directories
    for root, dirs, files in os.walk(user_dir):
        # Filter out unwanted directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for d in dirs:
            # Look for common virtual environment folder names
            if d.lower() in ['.venv', 'venv', 'env', 'mattersim_env']:
                venv_path = os.path.join(root, d)
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                # If python.exe exists inside Scripts, it is a valid venv
                if os.path.exists(python_exe):
                    found_venvs.append(venv_path)

    if not found_venvs:
        print("\n[!] No virtual environments (.venv, venv) were found.")
        input("Press Enter to exit...")
        return

    print(f"\n[OK] Found {len(found_venvs)} virtual environment(s)!")
    print("-" * 60)
    
    best_venv = None

    for venv in found_venvs:
        print(f"\nChecking environment: {venv}")
        python_exe = os.path.join(venv, "Scripts", "python.exe")
        
        # Check if mattersim library exists without installing anything
        try:
            result = subprocess.run(
                [python_exe, "-c", "import mattersim; print('MATTERSIM_FOUND')"],
                capture_output=True, text=True, timeout=10
            )
            if "MATTERSIM_FOUND" in result.stdout:
                print("  => [PERFECT] 'mattersim' is installed in this environment!")
                best_venv = venv
            else:
                print("  => [MISSING] 'mattersim' is NOT in this environment.")
        except Exception as e:
            print("  => [ERROR] Could not verify this environment.")

    print("\n" + "=" * 60)
    if best_venv:
        print("CONCLUSION: FOUND THE CORRECT PROJECT VIRTUAL ENVIRONMENT!")
        print(f"Path: {best_venv}")
        print("\nTo use it, copy and run the following command in PowerShell:")
        print(f"& '{best_venv}\\Scripts\\Activate.ps1'")
    else:
        print("CONCLUSION: None of the found environments have 'mattersim'.")
        print("You will need to install the libraries in your chosen environment.")
    print("=" * 60)
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
