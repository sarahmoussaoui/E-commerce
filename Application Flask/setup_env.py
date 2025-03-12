import sqlite3
import random
import posixpath
import shutil
import subprocess
import os


# Step 1: Create virtual environment and install dependencies
def setup_venv():
    venv_dir = "venv"

    # Step 1: Delete the existing virtual environment if it exists
    if os.path.exists(venv_dir):
        print(f"Deleting existing virtual environment at {venv_dir}...")
        shutil.rmtree(venv_dir)
        print(f"Deleted {venv_dir}.")

    # Step 2: Create a new virtual environment
    print("Creating a new virtual environment...")
    subprocess.run(["python", "-m", "venv", venv_dir], check=True)
    print(f"Virtual environment created at {venv_dir}.")

    # Step 3: Install dependencies in the virtual environment
    if os.name == "nt":  # Windows
        pip_path = os.path.join(venv_dir, "Scripts", "pip")
    else:  # Unix or MacOS
        pip_path = os.path.join(venv_dir, "bin", "pip")

    print("Installing dependencies...")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    print("Dependencies installed in the virtual environment.")

    # Step 4: Print instructions to activate the virtual environment
    if os.name == "nt":  # Windows
        activate_script = os.path.join(venv_dir, "Scripts", "activate")
        print(
            f"\nTo activate the virtual environment, run the following command:\n{activate_script}"
        )
    else:  # Unix or MacOS
        activate_script = os.path.join(venv_dir, "bin", "activate")
        print(
            f"\nTo activate the virtual environment, run the following command:\nsource {activate_script}"
        )



# Main execution
if __name__ == "__main__":
    # Setup virtual environment and install dependencies
    setup_venv()

