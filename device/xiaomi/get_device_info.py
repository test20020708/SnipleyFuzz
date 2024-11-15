import sys
sys.path.append('./device/xiaomi')
sys.path.append('./device/xiaomi/xiaomi_api')
from xiaomi_api.MiApi import MiService

def main():
    mi = MiService()
    print(mi.get_device_list())
    
if __name__ == "__main__":
    main()