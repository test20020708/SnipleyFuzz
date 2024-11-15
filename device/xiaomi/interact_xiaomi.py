import time
from colorama import init, Fore
import sys
import json
import signal
import ast
sys.path.append('./device/xiaomi')
sys.path.append('./device/xiaomi/xiaomi_api')
from xiaomi_api.MiApi import MiService

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Timeout occurred")

# Calculate the edit distance of two string   
def EditDistanceRecursive(str1, str2):
    edit = [[i + j for j in range(len(str2) + 1)] for i in range(len(str1) + 1)]
    for i in range(1, len(str1) + 1):
        for j in range(1, len(str2) + 1):
            if str1[i - 1] == str2[j - 1]:
                d = 0
            else:
                d = 1
            edit[i][j] = min(edit[i - 1][j] + 1, edit[i][j - 1] + 1, edit[i - 1][j - 1] + d)
    return edit[len(str1)][len(str2)]

# Calculate the similarity score of two string
def SimilarityScore(str1, str2):
    ED = EditDistanceRecursive(str1, str2)
    return round((1 - (ED / max(len(str1), len(str2)))) * 100, 2)

class Messenger:
    restore = [] # restoring message sequence (stay the same initial state)
    
    def __init__(self, restoreSeed) -> None:
        self.restore = restoreSeed

    def DryRunSend(self,sequence):  # send a sequence of messages (work for DryRun) Only for test
        for message in sequence.M:
            response = self.sendMessage(message)
            if response == "#error":
                return True
            sequence.R.append(response)
        for message in self.restore.M:
            response = self.sendMessage(message)
            if response == "#error":
                return True
        return sequence
    
    def ProbeSend(self,sequence,index): # send a sequence of messages (work for Probe)
        for i in range(len(sequence.M)):
            response = self.sendMessage(sequence.M[i])
            if response == "#error":
                return "#error"
            elif response == '#crash':
                return '#crash'
            if i == index:
                res = response
        for i in range(len(self.restore.M)):
            resotreResponse = self.sendMessage(self.restore.M[i])
            if resotreResponse == "#error":
                return "#error"
            elif response == '#crash':
                return '#crash'
        return res

    def SnippetMutationSend(self,sequence,index,path_score): # send a sequence of messages (work for SnippetMutate)
        for i in range(len(sequence.M)):
            response = self.sendMessage(sequence.M[i])
            if response == "#error":
                return "#error"
            elif response == '#crash':
                return '#crash'
            if i == index:
                res = response
                content = sequence.M[i].raw["content"].strip()
                print(f"{Fore.BLUE}[Message Content]{content}{Fore.RESET}")
                print(res)

        for i in range(len(self.restore.M)):
            restoreResponse = self.sendMessage(self.restore.M[i])
            if restoreResponse == "#error":
                return "#error"
            elif response == '#crash':
                return '#crash'

        pool = []
        scores = []
        
        for j in range(len(path_score)):
            pool.append(path_score[j]["response"])
            scores.append(path_score[j]["score"])

        # Determine whether the test case triggers a new path
        for i in range(len(pool)):
            c = SimilarityScore(pool[i].strip(), res.strip())
            if c >= scores[i]:
                return ""
        return "#interesting-"+str(index)
        
    def sendMessage(self,message,timeout_time = 0): # send a message
        if "did" in message.headers and "uri" in message.headers:  # socket 
            did = '"' + message.raw["did"].strip() + '"'
            uri =  message.raw["uri"].strip()
            content =  message.raw["content"].strip()
            response = ''
            command = {}
            command["uri"] = uri
            command["content"] = content
            localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
            timeout = 7
            init()
        
            try:
                mi = MiService()
                device = mi.use_device(did)
                bind_id = '"did": ' + did 
                if bind_id not in content:
                    response = "Fail to bind device!" + "\r\n"
                else:
                    try:
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(timeout)
                        response = str(device.send(command)) + "\r\n"
                    except TimeoutError:
                        if timeout_time < 5:
                            print(f"{Fore.RED}[ERROR]{localtime}:Timeout occurred! Retrying ({timeout_time + 1}/{5}).{Fore.RESET}")
                            signal.alarm(0)
                            response = self.sendMessage(message, timeout_time + 1)
                        else:
                            signal.alarm(0)
                            print("Crash!")
                            return "#crash"
                    
                    signal.alarm(0)
                        
                    if "updateTime" in response:
                        data = ast.literal_eval(response)
                        for item in data['result']:
                            item.pop('updateTime', None)
                        response = json.dumps(data, ensure_ascii = False) + "\r\n"
                        
                print(f"{Fore.GREEN}[+]{localtime}:Successful receive response from xiaomi!{Fore.RESET}")
                
            # add timeout feedback！
                
            except Exception as e:
                if timeout_time < 5:
                    print(f"{Fore.RED}[ERROR]{localtime}:{str(e)}! Retrying ({timeout_time + 1}/{5}).{Fore.RESET}")
                    time.sleep(0.5)
                    response = self.sendMessage(message, timeout_time + 1)
                else:
                    print("Crash!")
                    return "#crash"

            return response
        else:
            print("Error : device_id and uri of target should be included in input files")
            return "#error" # error