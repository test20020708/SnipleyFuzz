import subprocess
import time
import signal
import os
import threading

python_file = ["./Fuzzing/IoT-Fuzzing/IoTFuzz_xiaomi_camera.py",
               "./Fuzzing/IoT-Fuzzing/IoTFuzz_xiaomi_plug.py",
               "./Fuzzing/IoT-Fuzzing/IoTFuzz_yeelight.py"]
stop_flag = False
start_time = 0
crash_time = {}
max_execution_time = 24 * 60 * 60

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
    
    
def stop_processes(processes):
    try:
        # Send SIGINT signal to all processes
        for process in processes:
            if process.poll() is None:  # Check if the process is running
                os.kill(process.pid, signal.SIGKILL)
    except Exception as e:
        print(f"Error occurred while stopping processes: {e}")


def close_all_terminals():
    try:
        applescript_command = '''
            osascript -e 'tell application "Terminal" to close every window'
        '''
        subprocess.run(applescript_command, shell=True)
    except Exception as e:
        print(f"Error occurred while closing all terminals: {e}")
        
        
def close():
    try:
        applescript_command = '''
            osascript -e 'tell application "System Events" to keystroke return'
        '''
        subprocess.run(applescript_command, shell=True)
    except Exception as e:
        print(f"Error occurred while closing all terminals: {e}")
        
def process_crash():
    global python_file, stop_flag, crash_time, start_time
    folder = './scripts/ability_find_crash/share/'
    
    while(1):
        for file in python_file:
            file_name = file.split("/")[-1].split("IoTFuzz_")[-1].split(".")[0] + ".txt"
            crash_number = 0
            while(1):
                if os.path.exists(folder + file_name):
                    with open(folder + file_name, 'r') as f:
                        for line in f:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                if key == 'crash-number':
                                    crash_number = int(value)
                    break
                else:
                    continue
                
            if crash_number != 0:
                finish_time = time.time()
                crash_time[file.split("/")[-1].split("IoTFuzz_")[-1].split(".")[0]] = finish_time - start_time    
            
            if stop_flag == True:
                break       
                
                
def stop(max_execution_time, processes):
    print("**** start to exec stop")
    global stop_flag
    # Wait for a certain time and then stop all processes
    time.sleep(max_execution_time)
    stop_flag = True
    
    close_all_terminals()
    stop_processes(processes)
    print("Finish!")
    
                               
def main():
    print("*** Start to exec ability_find_crash experiment! ***")
    global python_file, start_time, max_execution_time, crash_time
    
    processes = []
    # Start a process for each Python file
    for filename in python_file:
        process = run_python_file(filename)
        if process:
            processes.append(process)
    
    start_time = time.time()
    
    thread_one = threading.Thread(target = process_crash)
    thread_two = threading.Thread(target = stop, args = (max_execution_time, processes))
    
    # start the threads
    thread_one.start()
    thread_two.start()
    
    while(1):
        alive = thread_one.is_alive() or thread_two.is_alive()
        if len(crash_time) == len(python_file) or not alive:
            if alive:
                stop(0, processes)
            break
    
    # generate a file
    file_name = "IoT-Fuzzing-ability.txt"
    path = "./output/ability_find_crash/"
    with open(path + file_name, "w") as f:
        if len(crash_time) == 0:
            f.writelines("In the specified time, no crash input was detected.\n")
        else:
            for key in list(crash_time.keys()):
                f.writelines("======== " + key + " ========\n")
                f.writelines("crash time: " + str(crash_time[key]) + "\n")

    
if __name__ == "__main__":
    main()