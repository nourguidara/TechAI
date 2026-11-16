import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def main():
    load_dotenv(dotenv_path=Path('.env'))
    sandbox_email = os.getenv('EMAIL_MODE', 'sandbox') == 'sandbox'
    if sandbox_email:
        os.environ['SMTP_HOST'] = '127.0.0.1'
        os.environ['SMTP_PORT'] = '1025'

    processes = []
    try:
        if sandbox_email:
            processes.append(subprocess.Popen([sys.executable, '-m', 'sandbox.mail_server']))
        processes.append(subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'backend.main:app',
            '--host', '127.0.0.1', '--port', '8000',
        ]))
        processes.append(subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app/Home.py',
            '--server.address', '127.0.0.1',
        ]))
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    finally:
        for p in processes:
            if p.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)
                else:
                    p.terminate()


if __name__ == '__main__':
    main()
