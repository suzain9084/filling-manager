import subprocess
from config.config import python_dir
import os

def run_filing_service():
    subprocess.Popen([python_dir , os.path.join("filing_app", "app.py")])

if __name__ == '__main__':
    run_filing_service()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nTerminating the processes. Alvida!")