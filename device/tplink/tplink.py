import socket
import time
import subprocess
import os

def sendCommond(tplink_ip, tplink_port, content):
    command = content
    max_retries = 3
    try:
        retries = 0
        while retries < max_retries:
            try:
                command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                command_socket.connect((tplink_ip, tplink_port))
                print("Successful connect")
                command_socket.send(command.encode('utf8'))
                print("Successful send")
                response1 = command_socket.recv(1024).decode('utf8')
                print(response1)
            except socket.timeout:
                retries += 1
                print("Timeout occurred. Retrying ({}/{})...".format(retries, max_retries))
                time.sleep(1)
            except ConnectionResetError:
                retries += 1
                print("Connection reset. Retrying ({}/{})...".format(retries, max_retries))
                time.sleep(1)
                
    except socket.error as e:
        print(f"Error:{e}")
    finally:
        command_socket.close()
        
def send(tplink_ip, content):
    # simulate the HS100
    js_file_path = "./device/tplink/simulator/simulator_hs100.js"
    command_simulation = ["node", js_file_path]
    process_simulation = subprocess.Popen(command_simulation)
    
    # send the command
    command = ["tplink-smarthome-api", "send", tplink_ip, content]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if "Error" in result.stderr:
            localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
            file = 'TpLink-HS100-Crash' + ":" + localtime + '.txt'
            outputfold = './output/crash/tplink'
            with open(os.path.join(outputfold, file), 'w') as f:
                f.writelines(content)
        else:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Exec failed: ", e)
    except Exception as e:
        print("Error: ", e)
    finally:
        process_simulation.terminate()

    
def main():
    content = '{"system":{"get_sysinfo":{}},"cnCloud":{"get_info":{}}}'
    for i in range(len(content)):
        content_update = content.strip()[:i] + content.strip()[i + 1:]
        time.sleep(1)
        send('192.168.100.20', content_update)

if __name__ == "__main__":
    main()
