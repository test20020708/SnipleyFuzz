import subprocess
import time
import signal
import os
import matplotlib.pyplot as plt
import threading
import math
import sys
sys.path.append('./Fuzzing/IoT-Fuzzing')

# List of Python files to execute in parallel
python_files_first_round = ["./scripts/comparison/IoTFuzzing-Scripts/yeelight.py",
                            "./scripts/comparison/IoTFuzzing-Scripts/xiaomi_camera.py",
                            "./scripts/comparison/IoTFuzzing-Scripts/xiaomi_plug.py"]

python_files_second_round = ["./scripts/comparison/Snippet-Scripts/Snipuzz_yeelight.py",
                            "./scripts/comparison/Snippet-Scripts/Snipuzz_xiaomi_camera.py",
                            "./scripts/comparison/Snippet-Scripts/Snipuzz_xiaomi_plug.py"]
python_files = [python_files_first_round, python_files_second_round]
information = {}
record_flag = [0, 0]
close_flag = [0, 0]
stop_flag = [0, 0]
crash_time = {}

time_slot_global = 60 * 10
time_slot_number = 9

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
        
        
def Record_information(index):
    print("**** start to exec Record_information")
    # Recode information
    global information, record_flag, python_files, time_slot_global, time_slot_number
    information_single = []
    folder = './scripts/comparison/share/'
    
    print("initial state")
    record = {}
    for file in python_files[index]:
        file_name = file.split("/")[-1].split(".")[0] + ".txt"
        while(1):
            if os.path.exists(folder + file_name):
                info_single = {}
                with open(folder + file_name, 'r') as f:
                    for line in f:
                        parts = line.strip().split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key == 'seed-number':
                                info_single["seed-number"] = int(value)
                            elif key == 'path-number':
                                info_single["path-number"] = int(value)
                            elif key == 'mutation-number':
                                info_single["mutation-number"] = float(value)
                break
            else:
                continue
        record[file.split("/")[-1].split(".")[0]] = info_single
        print(file.split("/")[-1].split(".")[0] + "'information has been recorded!")
        
    information_single.append(record)
    
    for i in range(time_slot_number):
        time.sleep(time_slot_global)
        print(str(i + 1) + "round!")
        record = {}
        for file in python_files[index]:
            file_name = file.split("/")[-1].split(".")[0] + ".txt"
            while(1):
                if os.path.exists(folder + file_name):
                    info_single = {}
                    with open(folder + file_name, 'r') as f:
                        for line in f:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                if key == 'seed-number':
                                    info_single["seed-number"] = int(value)
                                elif key == 'path-number':
                                    info_single["path-number"] = int(value)
                                elif key == 'mutation-number':
                                    info_single["mutation-number"] = float(value)
                    break
                else:
                    continue
            record[file.split("/")[-1].split(".")[0]] = info_single
            print(file.split("/")[-1].split(".")[0] + "'information has been recorded!")
            
        information_single.append(record)
    
    information[str(index)] = information_single
    record_flag[index] = 1


def stop(max_execution_time, processes, index):
    print("**** start to exec stop")
    # Wait for a certain time and then stop all processes
    time.sleep(max_execution_time)
    global close_flag, record_flag
    close_flag[index] = 1
    
    if max_execution_time != 0:
        while(1):
            if record_flag[index] == 0:
                continue
            else:
                break
    
    close_all_terminals()
    for i in range(len(processes)):
        close()
        i += 1
    
    stop_processes(processes)
    print("Finish!")
    
    
def crash_process(index):
    print("**** start to exec crash_process")
    global stop_flag, close_flag, python_files, crash_time
    folder = './scripts/comparison/share/'
    start_time = time.time()
    crash_time_single = {}
    
    while(1):
        crash_number = []
        # record the crash information
        if close_flag[index] == 1:
            break
        for file in python_files[index]:
            file_name = file.split("/")[-1].split(".")[0] + ".txt"
            while(1):
                if os.path.exists(folder + file_name):
                    with open(folder + file_name, 'r') as f:
                        for line in f:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                if key == 'crash-number':
                                    crash_number.append(int(value))
                    break
                else:
                    continue
        for i in range(len(crash_number)):
            if crash_number[i] == 1:
                finish_time = time.time()
                crash_time_single[python_files[index][i].split("/")[-1].split(".")[0]] = (finish_time - start_time) / 3600
                python_files[index].remove(python_files[index][i])
        
        crash_time[str(index)] = crash_time_single
        
        if len(python_files[index]) == 0:
            stop_flag[index] = 1
            break
        

def main():
    print("*** Start to exec ablation experiment! ***")
    global python_files, stop_flag, information, crash_time, time_slot_global, time_slot_number
    folder = './scripts/comparison/share'
    
    yeelight_information = {}
    yeelight_information["crash"] = {}
    yeelight_information["path"] = {}
    yeelight_information["seed"] = {}
    yeelight_information["number"] = {}
    
    xiaomi_plug_information = {}
    xiaomi_plug_information["crash"] = {}
    xiaomi_plug_information["path"] = {}
    xiaomi_plug_information["seed"] = {}
    xiaomi_plug_information["number"] = {}
    
    xiaomi_camera_information = {}
    xiaomi_camera_information["crash"] = {}
    xiaomi_camera_information["path"] = {}
    xiaomi_camera_information["seed"] = {}
    xiaomi_camera_information["number"] = {}
    
    for i in range(len(python_files)):
        # Remove residual files.
        for file in python_files[i]:
            file_name = file.split("/")[-1].split(".")[0] + ".txt"
            if "yeelight" in file_name:
                yeelight_information["path"][file.split("/")[-1].split(".")[0]] = []
                yeelight_information["seed"][file.split("/")[-1].split(".")[0]] = []
                yeelight_information["number"][file.split("/")[-1].split(".")[0]] = []
            if "xiaomi_plug" in file_name:
                xiaomi_plug_information["path"][file.split("/")[-1].split(".")[0]] = []
                xiaomi_plug_information["seed"][file.split("/")[-1].split(".")[0]] = []
                xiaomi_plug_information["number"][file.split("/")[-1].split(".")[0]] = []
            if "xiaomi_camera" in file_name:
                xiaomi_camera_information["path"][file.split("/")[-1].split(".")[0]] = []
                xiaomi_camera_information["seed"][file.split("/")[-1].split(".")[0]] = []
                xiaomi_camera_information["number"][file.split("/")[-1].split(".")[0]] = []
            if os.path.exists(folder + file_name):
                os.remove(folder + file_name)
                
        processes = []
        # Start a process for each Python file
        for filename in python_files[i]:
            process = run_python_file(filename)
            if process:
                processes.append(process)
                
        # create three threads
        thread_one = threading.Thread(target = Record_information, args = (i, ))
        thread_two = threading.Thread(target = crash_process, args = (i, ))
        thread_three = threading.Thread(target = stop, args = (time_slot_number * time_slot_global, processes, i))
        
        # start the threads
        thread_one.start()
        thread_two.start()
        thread_three.start()
        
        # process the threads
        while(1):
            alive = thread_one.is_alive() or thread_two.is_alive() or thread_three.is_alive()
            if stop_flag[i] == 1 or not alive:
                if alive:
                    stop(0, processes, i)
                print(information[str(i)])
                print(crash_time[str(i)])
                if len(crash_time[str(i)]) != 0:
                    for key in list(crash_time[str(i)].keys()):
                        if "yeelight" in key:
                            yeelight_information["crash"][key] = crash_time[str(i)][key]
                        if "xiaomi_plug" in key:
                            xiaomi_plug_information["crash"][key] = crash_time[str(i)][key]
                        if "xiaomi_camera" in key:
                            xiaomi_camera_information["crash"][key] = crash_time[str(i)][key]
                for record in information[str(i)]:
                    for key in list(record.keys()):
                        if "yeelight" in key:
                            yeelight_information["path"][key].append(record[key]["path-number"])
                            yeelight_information["seed"][key].append(record[key]["seed-number"])
                            yeelight_information["number"][key].append(record[key]["mutation-number"])
                        if "xiaomi_plug" in key:
                            xiaomi_plug_information["path"][key].append(record[key]["path-number"])
                            xiaomi_plug_information["seed"][key].append(record[key]["seed-number"])
                            xiaomi_plug_information["number"][key].append(record[key]["mutation-number"])
                        if "xiaomi_camera" in key:
                            xiaomi_camera_information["path"][key].append(record[key]["path-number"])
                            xiaomi_camera_information["seed"][key].append(record[key]["seed-number"])
                            xiaomi_camera_information["number"][key].append(record[key]["mutation-number"])
                break
            
    # Collect all information, Start to construct figure and file
    all_information = [yeelight_information, xiaomi_plug_information, xiaomi_camera_information]
    labels = ["yeelight", "xiaomi_plug", "xiaomi_camera"]
    path = "./output/comparison/"
    for i in range(len(all_information)):
        single_information = all_information[i]
        # Determine the range of the horizontal coordinate
        if len(single_information["crash"]) == 2:
            max_time = math.ceil(max(single_information["crash"].values()))
        else:
            max_time = time_slot_number
        time_points = []
        time_labels = []
        for index in range(max_time + 1):
            time_points.append(index)
            time_labels.append(str(index) + "h")
        # compute the padding length
        list_of_path = list(single_information["path"].values())
        lengths = [len(lst) for lst in list_of_path]
        max_length = max(lengths)
        # padding the path number array and seed number array
        for key in list(single_information["path"].keys()):
            padding_length = max_length - len(single_information["path"][key])
            single_information["path"][key] = single_information["path"][key] + [single_information["path"][key][-1]] * padding_length
            single_information["seed"][key] = single_information["seed"][key] + [single_information["seed"][key][-1]] * padding_length
            
        # generate a file
        file_name_single = "comparison_" + labels[i] + ".txt"
        path_file = "./output/comparison/file_one/"
        with open(path_file + file_name_single, "w") as f:
            for key in list(single_information["seed"].keys()):
                f.writelines("======== " + key + " ========\n")
                if key in single_information["crash"]:
                    f.writelines("is_crash: True\n")
                    f.writelines("crash time: " + str(single_information["crash"][key]) + "\n")
                    max_time_single = math.floor(single_information["crash"][key])
                else:
                    f.writelines("is_crash: False\n")
                    max_time_single = time_slot_number
                for k in range(max_time_single + 1):
                    string = str(k) + "h: (seed number: " + str(single_information["seed"][key][k]) + ", Path number: " + str(single_information["path"][key][k]) + ", Mutation Times: " + str(single_information["number"][key][k]) + ")\n"
                    f.writelines(string)
                f.writelines("\n")
            
        ### the first figure: path number figure
        for key in list(single_information["path"].keys()):
            if "Snipuzz" in key:
                plt.plot(time_points, single_information["path"][key], label = labels[i] + "-Snipuzz", color = 'blue')
            else:
                plt.plot(time_points, single_information["path"][key], label = labels[i], color = 'red')
        # special time
        for key in list(single_information["crash"]):
            if "Snipuzz" in key:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='blue', linewidth=0.5)
            else:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='red', linewidth=0.5)
                
        plt.xlabel('Time')
        plt.ylabel('Path number--' + labels[i])
        plt.xticks(time_points, time_labels, fontsize = 5)
        plt.legend()
        plt.title(labels[i] + ' path number Over Time')
        
        for j in range(len(time_points)):
            for key in list(single_information["path"].keys()):
                plt.text(time_points[j], single_information["path"][key][j], f'({time_points[j]}, {single_information["path"][key][j]})', fontsize=3, verticalalignment='bottom', horizontalalignment='right')
        
        figure_name = "comparison_path_" + labels[i] + ".pdf"
        plt.savefig(path + figure_name)
        plt.close()
        
        ### the second figure: seed number figure
        for key in list(single_information["seed"].keys()):
            if "Snipuzz" in key:
                plt.plot(time_points, single_information["seed"][key], label = labels[i] + "-Snipuzz", color = 'blue')
            else:
                plt.plot(time_points, single_information["seed"][key], label = labels[i], color = 'red')
        # special time
        for key in list(single_information["crash"]):
            if "Snipuzz" in key:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='blue', linewidth=0.5)
            else:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='red', linewidth=0.5)
                
        plt.xlabel('Time')
        plt.ylabel('Seed number--' + labels[i])
        plt.xticks(time_points, time_labels, fontsize = 5)
        plt.legend()
        plt.title(labels[i] + ' seed number Over Time')
        
        for j in range(len(time_points)):
            for key in list(single_information["seed"].keys()):
                plt.text(time_points[j], single_information["seed"][key][j], f'({time_points[j]}, {single_information["seed"][key][j]})', fontsize=3, verticalalignment='bottom', horizontalalignment='right')
        
        figure_name = "comparison_seed_" + labels[i] + ".pdf"
        plt.savefig(path + figure_name)
        plt.close()
        
        ### the third figure: mutation number figure
        for key in list(single_information["number"].keys()):
            if "Snipuzz" in key:
                plt.plot(time_points, single_information["number"][key], label = labels[i] + "-Snipuzz", color = 'blue')
            else:
                plt.plot(time_points, single_information["number"][key], label = labels[i], color = 'red')
        # special time
        for key in list(single_information["crash"]):
            if "Snipuzz" in key:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='blue', linewidth=0.5)
            else:
                plt.axvline(x = single_information["crash"][key], linestyle='--', color='red', linewidth=0.5)
                
        plt.xlabel('Time')
        plt.ylabel('Mutation Times number--' + labels[i])
        plt.xticks(time_points, time_labels, fontsize = 5)
        plt.legend()
        plt.title(labels[i] + ' Mutation Times number Over Time')
        
        for j in range(len(time_points)):
            for key in list(single_information["number"].keys()):
                plt.text(time_points[j], single_information["number"][key][j], f'({time_points[j]}, {single_information["number"][key][j]})', fontsize=3, verticalalignment='bottom', horizontalalignment='right')
        
        figure_name = "comparison_number_" + labels[i] + ".pdf"
        plt.savefig(path + figure_name)
        plt.close()
        
    
if __name__ == "__main__":
    main()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               