import socket
import time
import os
import re

# Global var
# we can adjust the seed by editing the list
command_message = [
    '{"id":1,"method":"set_power","params":["on"]}',
    '{"id":1,"method":"set_ct_abx","params":[3500,"smooth",500]}',
    '{"id":1,"method":"set_adjust","params":["increase", "ct"]}',
    '{"id":1,"method":"set_bright","params":[50]}'
]

result_message = [
    '{"id":2,"method":"get_prop","params":["power", "ct", "bright"]}',
    '{"id":2,"method":"get_prop","params":["ct", "color_mode", "flowing"]}',
    '{"id":2,"method":"get_prop","params":["color_mode", "delayoff", "music_on"]}',
    '{"id":2,"method":"get_prop","params":["flowing", "ct"]}'
]

random_message = [
    '{"id":3,"method":"set_power","params":["off"]}',
    '{"id":3,"method":"get_prop","params":["color_mode", "power"]}',
    '{"id":3,"method":"adjust_ct","params":[20, 500]}',
    '{"id":3,"method":"get_prop","params":["ct"]}'
]

# extract the ip address and the port of the yeelight
def yeelight_info():
    # Set the server address and port number
    server_address = ('239.255.255.250', 1982)
    # Create a UDP socket
    yeelight_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # set the timeout and the maximal number of retry
    timeout = 5
    max_retries = 3
    
    try:
        ssdp_message = "M-SEARCH * HTTP/1.1\r\n" \
                "HOST: 239.255.255.250:1982\r\n" \
                "MAN: \"ssdp:discover\"\r\n" \
                "ST: wifi_bulb\r\n"
        
        retries = 0
        while retries < max_retries:
            yeelight_socket.sendto(ssdp_message.encode('utf-8'), server_address)
            print("Successful!")
            yeelight_socket.settimeout(timeout)
            try:
                response, server_info = yeelight_socket.recvfrom(1024)
                break
            except socket.timeout:
                retries += 1
                print("Timeout occurred. Retrying ({}/{})...".format(retries, max_retries))
                time.sleep(1)
                
        if retries == max_retries:
            print("Max retries reached. No response received.")
        else:
            # extract the ip address and port
            print(response.decode('utf-8'))
            match = re.search(r'yeelight://(\d+\.\d+\.\d+\.\d+):(\d+)', response.decode('utf-8'))
            yeelight_ip = match.group(1)
            yeelight_port = int(match.group(2))
            yeelight_information = {}
            yeelight_information["IP"] = yeelight_ip
            yeelight_information["Port"] = yeelight_port
            return yeelight_information

    except Exception as e:
        print("An error occurred:", e)
        
    finally:
        yeelight_socket.close()


# generation the initial seed
def initial_seed_generation(yeelight_ip, yeelight_port):
    global command_message, result_message, random_message
    for i in range(4):
        content_array = [command_message[i], result_message[i], random_message[i]]
        with open(os.path.join('./device/yeelight/yeelight_file/initial_seed', 'yeelight_' + str(i) + '.txt'), 'w') as f:
            for j in range(3):
                f.writelines("====================  " + str(j) + " ==========================\n")
                f.writelines("\n")
                f.writelines("IP:" + yeelight_ip + "\n")
                f.writelines("Port:" + str(yeelight_port) + "\n")
                f.writelines("Content:" + content_array[j] + "\n")
                f.writelines("\n")
            print("seed" + str(i) + " has been generated!")
    return 0


# generation the restore seed: restart of yeelight
def restoreSeed_generation(yeelight_ip, yeelight_port):
    with open(os.path.join('./device/yeelight/yeelight_file', 'restoreSeed.txt'), 'w') as f:
        f.writelines("====================  0 ==========================\n")
        f.writelines("\n")
        f.writelines("IP:" + yeelight_ip + "\n")
        f.writelines("Port:" + str(yeelight_port) + "\n")
        f.writelines('Content:{"id":1,"method":"set_power","params":["off"]}\n')
        f.writelines("\n")
        f.writelines("====================  1 ==========================\n")
        f.writelines("\n")
        f.writelines("IP:" + yeelight_ip + "\n")
        f.writelines("Port:" + str(yeelight_port) + "\n")
        f.writelines('Content:{"id":2,"method":"set_scene","params":["ct", 5400, 100]}\n')
    print("restoreSeed has been generated!")
    return 0

def sendCommond(yeelight_ip, yeelight_port, content):
    command = content + "\r\n"
    max_retries = 3
    notification_string = '"method":"props"'
    try:
        retries = 0
        while retries < max_retries:
            try:
                command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                command_socket.connect((yeelight_ip, yeelight_port))
                print("Successful connect")
                command_socket.send(command.encode('utf8'))
                print("Successful send")
                response1 = command_socket.recv(1024).decode('utf8')
                if notification_string not in response1:
                    print(response1)
                    return response1
                else:
                    response2 = command_socket.recv(1024).decode('utf8')
                    print(response2)
                    return response2
            except Exception as e:
                retries += 1
                print("Retrying ({}/{})...".format(retries, max_retries) + str(e))
                time.sleep(1)    
    finally:
        command_socket.close()
    
    
def main():
    yeelight_information = yeelight_info()
    yeelight_ip = yeelight_information["IP"]
    yeelight_port = yeelight_information["Port"]
    content = '{"id":1,"method":"set_ct_abx","params":[3500,"smooth",500]'
    sendCommond(yeelight_ip, yeelight_port, content) 
    
if __name__ == "__main__":
    main()
               