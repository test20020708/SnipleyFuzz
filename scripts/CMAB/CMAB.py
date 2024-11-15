import subprocess
import time
import signal
import os
import matplotlib.pyplot as plt
import threading
import math
import sys

python_file = ["./scripts/CMAB/CMAB_yeelight.py",
               "./scripts/CMAB/CMAB_xiaomi_camera.py",
               "./scripts/CMAB/CMAB_xiaomi_plug.py"]

def run_python_file(filename):
    try:
        current_directory = os.getcwd()
        # Construct the command to execute AppleScript
        applescript_command = [
            'osascript',
            '-e',
            f'tell app "Terminal" to do script "cd {current_directory} && python {filename}"'
        ]
        # Open a new terminal and execute the Python file
        process = subprocess.Popen(applescript_command)
        return process
    except Exception as e:
        print(f"Error occurred while running {filename}: {e}")
        return None
    
def main():
    global python_file
    processes = []
    for filename in python_file:
        process = run_python_file(filename)
        if process:
            processes.append(process)
            
if __name__ == "__main__":
    main()    