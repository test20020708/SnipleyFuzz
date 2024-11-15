from colorama import init, Fore
import socket
import time

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
    SocketSender = socket.socket()
    restore = [] # restoring message sequence (stay the same initial state)
    
    def __init__(self, restoreSeed) -> None:
        self.SocketSender = None
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
                content = sequence.M[i].raw["Content"].strip()
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
        
    def sendMessage(self,message,timeout_time = 0, retrytime = 0): # send a message
        if "IP" in message.headers and "Port" in message.headers:  # socket 
            ip = message.raw["IP"].strip()
            port =  int(message.raw["Port"])
            content =  message.raw["Content"]+"\r\n"
            notification_string = '"method":"props"'
            response = ''
            timeout = 5
            max_retries = 3
            localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
            init()
        
            try:
                self.SocketSender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.SocketSender.connect((ip,port))
                self.SocketSender.send(content.encode('utf8'))
                self.SocketSender.settimeout(timeout)
                response = self.SocketSender.recv(1024).decode('utf8')
                if notification_string in response:
                    response = self.SocketSender.recv(1024).decode('utf8')
                print(f"{Fore.GREEN}[+]{localtime}:Successful receive response from yeelight!{Fore.RESET}")
                self.SocketSender.close()
                
            except socket.timeout:
                print(f"{Fore.RED}[ERROR]{localtime}:Time out during the tcp process! Retrying ({timeout_time + 1}/{3}).{Fore.RESET}")
                if timeout_time < 2:   # repeat
                    self.SocketSender.close()
                    time.sleep(0.5)
                    response = self.sendMessage(message, timeout_time + 1, retrytime)
                else:
                    return "#crash"
            except Exception as e:
                if retrytime < max_retries:
                    print(f"{Fore.RED}[ERROR]{localtime}:{str(e)}! Retrying ({retrytime + 1}/{max_retries}).{Fore.RESET}")
                    self.SocketSender.close()
                    time.sleep(0.5)
                    response = self.sendMessage(message, timeout_time, retrytime + 1)
                else:
                    return "#crash"

            return response
        else:
            print("Error : IP and Port of target should be included in input files")
            return "#error" # error