import sys
import os
sys.path.append('./device/xiaomi')
sys.path.append('./device/xiaomi/xiaomi_api')
from xiaomi_api.MiApi import MiService

# Global var
# we can adjust the seed by editing the list
command_type = [
    "/miotspec/prop/set",
    "/miotspec/prop/get"
]

def xiaomi_info(name):
    mi = MiService()
    device = mi.find_device(name)
    device_info = device.device_info()
    information = {}
    information["did"] = device_info["did"]
    information["token"] = device_info["token"]
    information["ip"] = device_info["localip"]
    return information

def initial_seed_generation(device_id):
    global command_type
    
    command_message_set = [
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 2, "value": false}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 2, "value": 1}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 13, "value": false}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 4, "value": 5}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 9, "value": true}]}'
    ]

    command_messgae_get = [
        '{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 2}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 13}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 2}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 9}]}',
        '{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 4}]}'
    ]
    
    for i in range(len(command_message_set)):
        content_array = [command_message_set[i], command_messgae_get[i]]
        with open(os.path.join('./device/xiaomi/plug/plug_file/initial_seed', 'xiaomi_' + str(i) + '.txt'), 'w') as f:
            for j in range(2):
                f.writelines("====================  " + str(j) + " ==========================\n")
                f.writelines("\n")
                f.writelines("did:" + device_id + "\n")
                f.writelines("uri:" + command_type[j] + "\n")
                f.writelines("content:" + content_array[j] + "\n")
                f.writelines("\n")
            print("seed" + str(i) + " has been generated!")
    return 0
    
def restoreSeed_generation(device_id):
    with open(os.path.join('./device/xiaomi/plug/plug_file', 'restoreSeed.txt'), 'w') as f:
        f.writelines("====================  0 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 2, "value": false}]}\n')
        f.writelines("\n")
        f.writelines("====================  1 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 2, "value": true}]}\n')
        f.writelines("\n")
        f.writelines("====================  2 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 2, "value": 0}]}\n')
        f.writelines("\n")
        f.writelines("====================  3 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 13, "value": true}]}\n')
        f.writelines("\n")
        f.writelines("====================  4 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 2, "siid": 4, "value": 2}]}\n')
        f.writelines("\n")
        f.writelines("====================  5 ==========================\n")
        f.writelines("\n")
        f.writelines("did:" + device_id + "\n")
        f.writelines("uri:" + command_type[0] + "\n")
        f.writelines('content:{"params": [{"did": "' + device_id + '", "piid": 1, "siid": 9, "value": false}]}\n')
        f.writelines("\n")
    print("restoreSeed has been generated!")
    return 0

def SendCommand(command, name):
    mi = MiService()
    device = mi.find_device(name)
    return device.send(command)

def main():
    device_name = "plug"
    command = {}
    command["uri"] = "/miotspec/prop/get"
    command["content"] = '{"params": [{"did": "732615647", "piid": 1, "siid": 9, "value": true}]}'
    information = xiaomi_info(device_name)
    print(information)
    device_id = information["did"]
    initial_seed_generation(device_id)
    restoreSeed_generation(device_id)
    print(SendCommand(command, device_name))

if __name__ == '__main__':
    main()