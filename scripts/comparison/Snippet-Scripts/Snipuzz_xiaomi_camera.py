import os
import sys
import time
import random
import time
import threading
import pandas as pd
from scipy.cluster import hierarchy
from colorama import init, Fore

sys.path.append(r'..')
sys.path.append('./device/xiaomi')
sys.path.append('./Fuzzing/Snipuzz-py')

from interact_xiaomi import Messenger, SimilarityScore
from Seed import Message, Seed

# Global var
queue = []
restoreSeed = '' # restoring message sequence
outputfold = ''
crash_number = 0
round = 0
number_array = []
path_score = []

def info():
    global queue, crash_number,number_array
    while(1):
        seed_number = len(queue)
        number_sum = 0
        for number in number_array:
            number_sum += number
        if len(number_array) != 0:
            average = number_sum / len(number_array)
        else:
            average = 0 
        with open(os.path.join('./scripts/comparison/share', 'Snipuzz_xiaomi_camera.txt'), 'w') as f:
            f.writelines("seed-number: " + str(seed_number) + "\n")
            f.writelines("path-number: " + str(len(path_score)) + "\n")
            f.writelines("crash-number: " + str(crash_number) + "\n")
            f.writelines("mutation-number: " + str(average) + "\n")
        time.sleep(5)

# has been tested: Success!
# read the input file and store it as a seed
def readInputFile(file):
    s = Seed()
    lines = []
    with open(file, 'r') as f:
        lines = f.read().split("\n")
    for i in range(0, len(lines)):
        # Separators for different messages ========
        if "========" in lines[i]: 
            mes = Message()
            for j in range(i + 1, len(lines)):
                if "========" in lines[j]:
                    i = j
                    break
                if ":" in lines[j]:
                    mes.append(lines[j])
            s.append(mes)
    return s


# has been tested: Success!
# read the input fold and store them as seeds
def readInputFold(fold):
    seeds = []
    files = os.listdir(fold)
    for file in files:
        print("Loading file: ", os.path.join(fold, file))
        seeds.append(readInputFile(os.path.join(fold, file)))
    return seeds


# has been tested: Success!
# Write the probe result that has been run into the output
def writeRecord(queue, fold):
    with open(os.path.join(fold, 'xiaomi_camera_ProbeRecord.txt'), 'w') as f:
        for i in range(len(queue)):
            f.writelines("========Seed " + str(i) + "========\n")
            for j in range(len(queue[i].M)):
                
                f.writelines("Message Index-" + str(j) + "\n")  # write the message information
                for header in queue[i].M[j].headers:
                    f.writelines(header + ":" + queue[i].M[j].raw[header] + '\n')
                f.writelines("\n")
                
                f.writelines('Original Response' + "\n")  # write the original response
                f.writelines(queue[i].R[j])
                
                f.writelines('Probe Result:' + "\n")  # write the results of probe
                f.writelines('PI' + "\n")  # PI
                for n in queue[i].PI[j]:
                    f.write(str(n) + " ")
                f.writelines("\n")
                f.writelines('PR and PS' + "\n")
                for n in range(len(queue[i].PR[j])):
                    f.writelines("(" + str(n) + ") " + queue[i].PR[j][n])
                    f.writelines(str(queue[i].PS[j][n]) + "\n")
            f.writelines("\n")
            f.writelines("\n")
    return 0


# has been tested: Success!
# Read the probe results from the record, thus skip the probe process and directly start the mutation test.
def readRecordFile(file):
    queue = []
    with open(os.path.join(file), 'r') as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            if lines[i].startswith("========Seed"):
                seedStart = i + 1
                seedEnd = len(lines)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("========Seed"):
                        seedEnd = j
                        break
                seed = Seed()
                index = seedStart
                
                while index < seedEnd:
                    
                    if lines[index].startswith('Message Index'):
                        message = Message()
                        responseStart = seedEnd
                        for j in range(index, seedEnd):
                            if lines[j].startswith('Original Response'):
                                responseStart = j
                                break
                        for line in lines[index + 1:responseStart - 1]:
                            message.append(line)
                        seed.M.append(message)
                        index = responseStart
                        
                    if lines[index].startswith('Original Response'):
                        index = index + 1
                        seed.R.append(lines[index])
                        
                    if lines[index].startswith('PI'):
                        index = index + 1
                        PIstr = lines[index]
                        PI = []
                        for n in PIstr.strip().split(' '):
                            PI.append(int(n))
                        seed.PI.append(PI)
                        
                    if lines[index].startswith('PR and PS'):
                        index = index + 1
                        ends = seedEnd
                        PR = []
                        PS = []
                        for j in range(index, seedEnd):
                            if lines[j].startswith('Message Index'):
                                ends = j
                                break
                        for j in range(index, ends):
                            if lines[j].startswith("("):
                                PR.append(lines[j][3:])
                            elif lines[j][0].isdigit():
                                PS.append(float(lines[j].strip()))
                        seed.PR.append(PR)
                        seed.PS.append(PS)
                        
                    index = index + 1
                    
                i = index
                queue.append(seed)
                
    return queue


# has been tested: Success!
# Try to use the input given for a complete communication.
# The func is used to test whether the input meets the requirements or whether there are other problems
def dryRun(queue):
    print(f"{Fore.BLUE}Start to exec dryRun Process!{Fore.RESET}")
    global restoreSeed
    m = Messenger(restoreSeed)
    for i in range(0, len(queue)):
        seed = m.DryRunSend(queue[i])
        queue[i] = seed
    return False


def update_path_score(seed):
    global path_score
    for i in range(len(seed.M)):
        responsePool = seed.PR[i]
        scorePool = seed.PS[i]
        for k in range(len(responsePool)):
            path_and_score = {}
            response = responsePool[k]
            if path_score:
                flag = True
                for j in range(len(path_score)):
                    target = path_score[j]["response"]
                    target_score = path_score[j]["score"]
                    c = SimilarityScore(target.strip(), response.strip())
                    if c >= target_score:
                        flag = False
                        break
                if flag:
                    path_and_score["response"] = response
                    path_and_score["score"] = scorePool[k]
                    path_score.append(path_and_score)
            else:
                path_and_score["response"] = response
                path_and_score["score"] = scorePool[k]
                path_score.append(path_and_score)


# has been tested: Success!
# Use heuristics to detect the meaning of each byte in the message (the first step)
def Probe(Seed):
    global restoreSeed, path_score
    
    m = Messenger(restoreSeed)
    for index in range(len(Seed.M)):
        
        responsePool = []
        similarityScore = []
        probeResponseIndex = []
        
        # Calculation of self-similarity scores
        response1 = m.ProbeSend(Seed, index)  # send the probe message   
        time.sleep(1)
        response2 = m.ProbeSend(Seed, index)  # send the probe message twice
        
        print("========" + "Message" + str(index) + "========")
        print("Message" + str(index) + ":(first)" + response1)
        print("Message" + str(index) + ":(second)" + response2)
        print("========" + "Message" + str(index) + "========")
        
        responsePool.append(response1)
        Res_score = SimilarityScore(response1.strip(), response2.strip())
        similarityScore.append(Res_score)
        
        if path_score:
            global_flag = True
            for i in range(0, len(path_score)):
                global_target = path_score[i]["response"]
                global_score = path_score[i]["score"]
                global_c = SimilarityScore(global_target.strip(), response1.strip())
                if global_c >= global_score:
                    global_flag = False
                    break
            if global_flag:
                path_and_score = {}
                path_and_score["response"] = response1
                path_and_score["score"] = Res_score
                path_score.append(path_and_score)
        else:
            path_and_score = {}
            path_and_score["response"] = response1
            path_and_score["score"] = Res_score
            path_score.append(path_and_score)
        
        # probe process
        for i in range(0, len(Seed.M[index].raw["content"])):
           temp = Seed.M[index].raw["content"]
           Seed.M[index].raw["content"] = Seed.M[index].raw["content"].strip()[:i] + Seed.M[index].raw["content"].strip()[i + 1:]  # delete ith byte
           
           # Calculation of self-similarity scores
           response1 = m.ProbeSend(Seed, index)  # send the probe message  
           time.sleep(1)
           response2 = m.ProbeSend(Seed, index)  # send the probe message twice
           print(Seed.M[index].raw["content"])
           print("Mutation" + str(i) + ":(first)" + response1)
           print("Mutation" + str(i) + ":(second)" + response2)
           
           if path_score:
               global_flag = True
               for k in range(0, len(path_score)):
                   global_target = path_score[k]["response"]
                   global_score = path_score[k]["score"]
                   global_c = SimilarityScore(global_target.strip(), response1.strip())
                   if global_c >= global_score:
                       global_flag = False
                       break
               if global_flag:
                   path_and_score = {}
                   path_and_score["response"] = response1
                   path_and_score["score"] = SimilarityScore(response1.strip(), response2.strip())
                   path_score.append(path_and_score)
           
           if responsePool:
               flag = True
               for j in range(0, len(responsePool)):
                   target = responsePool[j]
                   score = similarityScore[j]
                   c = SimilarityScore(target.strip(), response1.strip())
                   if c >= score:
                       flag = False
                       probeResponseIndex.append(j)
                       print("Mutation" + str(i) + " is similar")
                       sys.stdout.flush()
                       break
               if flag:
                    responsePool.append(response1)
                    similarityScore.append(SimilarityScore(response1.strip(), response2.strip()))
                    print("Mutation" + str(i) + " is unique" + "\n")
                    probeResponseIndex.append(j + 1)
            
           Seed.M[index].raw["content"] = temp  # restore the message

        Seed.PR.append(responsePool)
        Seed.PS.append(similarityScore)
        Seed.PI.append(probeResponseIndex)

    return Seed


# has been tested: Success!
# extract features from responses
def getFeature(response, score):
    feature = {}
    feature['a'] = 0  # Letter count in response
    feature['n'] = 0  # Digit count in response
    feature['s'] = 0  # Special character count in response
    length = len(response)
    score = score

    cur = ''
    pre = ''
    for i in range(len(response)):
        if response[i].isdigit():
            cur = 'n'
        elif response[i].isalpha():
            cur = 'a'
        else:
            cur = 's'

        if pre == '':
            pre = cur
        elif pre != cur:
            feature[pre] = feature[pre] + 1
        pre = cur

    feature[cur] = feature[cur] + 1

    return [feature['a'], feature['n'], feature['s'], length, score]


# has been tested
# change the probe index
# form snippet from messages
def formSnippets(pi, cluster, index):
    snippet = []
    for i in range(index):
        c1 = int(cluster[i][0])
        c2 = int(cluster[i][1])
        p = int(cluster[i][3])
        for j in range(len(pi)):
            if pi[j] == c1 or pi[j] == c2:
                pi[j] = len(cluster) + 1 + i

    i = 0
    while i < len(pi)-1:
        j = i
        skip = True
        while j <= len(pi) and skip:
            j = j + 1
            if pi[j] != pi[i]:
                snippet.append([i, j - 1])
                skip = False
            if j == len(pi)-1:
                snippet.append([i, j])
                skip = False
        i = j

    return snippet


# has been tested: Success!
# put the interesting messages into the seed queue
def interesting(oldSeed,index):
    global queue
    global restoreSeed
    m = Messenger(restoreSeed)
    
    print(oldSeed.M[index].raw["content"])

    seed = Seed()
    for i in range(len(oldSeed.M)):
        message = Message()
        seed.M.append(message)
    seed.M[index].headers = oldSeed.M[index].headers
    for i in seed.M[index].headers:
        seed.M[index].raw[i] = oldSeed.M[index].raw[i]
    seed = m.DryRunSend(seed)
    seed = Probe(seed)
    queue.append(seed)
    

def writeOutput(seed):
    global outputfold
    localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    file = 'snipuzz_xiaomi_camera-Crash-' + str(crash_number) + ":" + localtime + '.txt'

    with open(os.path.join(outputfold, file), 'w') as f:
        for i in range(len(seed.M)):
            f.writelines("Message Index-" + str(i) + "\n")  # write the message information
            for header in seed.M[i].headers:
                f.writelines(header + ":" + seed.M[i].raw[header] + '\n')
            f.writelines("\n")
    print("Found a crash @ " + localtime)
    sys.exit()
    

# has been tested: Success!
def responseHandle(seed, info):
    global crash_number
    if info.startswith("#interesting"):
        print("~~Get Interesting in :")
        interesting(seed, int(info.split('-')[1]))
        return False
    if info.startswith("#error"):
        print("~~Something wrong with the target infomation (e.g. IP addresss or port)")
    if info.startswith("#crash"):
        crash_number += 1
        print(f"Crash!!!!  number({str(crash_number)})")
        writeOutput(seed)
    return True


def SnippetMutate(seed, restoreSeed):
    
    m = Messenger(restoreSeed)
    
    for i in range(len(seed.M)):
        pool = seed.PR[i]
        poolIndex = seed.PI[i]
        similarityScores = seed.PS[i]
        
        print(f"{Fore.BLUE}Start to exec SnippetMutate process for Message{i}! {i+1}/{len(seed.M)}{Fore.RESET}")

        featureList = []
        for j in range(len(pool)):
            featureList.append(getFeature(pool[j].strip(), similarityScores[j]))

        df = pd.DataFrame(featureList)
        cluster = hierarchy.linkage(df, method='average', metric='euclidean')

        seed.ClusterList.append(cluster)

        mutatedSnippet = []
        for index in range(len(cluster)):
            print(f"{Fore.BLUE}Start to exec SnippetMutate process for snippet in cluster round{index}! {index + 1}/{len(cluster)}{Fore.RESET}")
            snippetsList = formSnippets(poolIndex, cluster, index)
            for snippet in snippetsList:
                if snippet not in mutatedSnippet:
                    mutatedSnippet.append(snippet)
                    
        seed.Snippet.append(mutatedSnippet)
    return 0


def Havoc(queue, restoreSeed):
    print("*Havoc")
    m = Messenger(restoreSeed)

    t = random.randint(0,len(queue)-1)
    seed = queue[t]

    i = random.randint(0,len(seed.M)-1)
    snippets = seed.Snippet[i]
    message = seed.M[i].raw["content"]
    tempMessage = seed.M[i].raw["content"]

    n = random.randint(0,len(snippets)-1)
    snippet = snippets[n]

    pick = random.randint(0,4)
    
    if pick == 0:  # ========  BitFlip ========
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            asc=asc+(chr(255-ord(message[o])))
        message = message[:snippet[0]] + asc + message[snippet[1] + 1:]
        seed.M[i].raw["content"] = message
        temp = responseHandle(seed, m.SnippetMutationSend(seed,i,path_score))
        seed.M[i].raw["content"] = tempMessage
        return temp

    elif pick == 1: # ========  Empty ==========
        message = seed.M[i].raw["content"]
        message = message[:snippet[0]] + message[snippet[1]+1:]
        seed.M[i].raw["content"] = message
        temp = responseHandle(seed, m.SnippetMutationSend(seed,i,path_score))
        seed.M[i].raw["content"] = tempMessage
        return temp
    
    elif pick == 2: # ========  Repeat ========
        message = seed.M[i].raw["content"]
        t = random.randint(2, 5)
        message = message[:snippet[0]] + message[snippet[0]:snippet[1]] * t + message[snippet[1] + 1:]
        seed.M[i].raw["content"] = message
        temp = responseHandle(seed, m.SnippetMutationSend(seed,i,path_score))
        seed.M[i].raw["content"] = tempMessage
        return temp

    elif pick == 3: # ========  Interesting ========
        interestingString = ['on','off','True','False','0','1']
        interesting = random.randint(0,5)
        t = interestingString[interesting]
        message = seed.M[i].raw["content"]
        message = message[:snippet[0]] + t + message[snippet[1] + 1:]
        seed.M[i].raw["content"] = message
        temp = responseHandle(seed, m.SnippetMutationSend(seed,i,path_score))
        seed.M[i].raw["content"] = tempMessage
        return temp
    
    elif pick == 4: # ======== Random Bytes Flip ===========
        start = random.randint(0,len(message)-1)
        end = random.randint(start,len(message))
        asc = ""
        for o in range(start, end):
            asc=asc+(chr(255-ord(message[o])))
        message = message[:start] + asc + message[end + 1:]
        seed.M[i].raw["content"] = message
        temp = responseHandle(seed, m.SnippetMutationSend(seed,i,path_score))
        seed.M[i].raw["content"] = tempMessage
        return temp

    return True


def main():
    global queue, restoreSeed, outputfold, round, number_array
    
    init()

    restorefile = './device/xiaomi/camera/camera_file/restoreSeed.txt'
    outputfold = './output/crash/xiaomi_camera'
    recordfile = './device/xiaomi/camera/camera_file/xiaomi_camera_ProbeRecord.txt'
    inputfold = './device/xiaomi/camera/camera_file/initial_seed'
    probe_fold = './device/xiaomi/camera/camera_file'
    
    restoreSeed = readInputFile(restorefile)
    print(f"{Fore.BLUE}Successful read from the restorefile!{Fore.RESET}")
    queue = readInputFold(inputfold)

    if recordfile and os.path.exists(recordfile):
        print(f"{Fore.BLUE}ProbeRecord file exists and Probe process has been ignored!{Fore.RESET}")
        queue = readRecordFile(recordfile)
        
        for seed in queue:
            update_path_score(seed)
        
        thread = threading.Thread(target = info)
        thread.start()
        
        for seed in queue:
            seed.display()
            
        if (dryRun(queue)):  # Dry Run
            print('#### Dry run failed, check the inputs or connection.')
            sys.exit()
    else:
        print(f"{Fore.BLUE}Start to exec Probe process!{Fore.RESET}")
        queue = readInputFold(inputfold)
        if (dryRun(queue)):  # Dry Run
            print('#### Dry run failed, check the inputs or connection.')
            sys.exit()
        for i in range(len(queue)):
            print(f"{Fore.BLUE}Start to exec Probe process for seed{i}! {i + 1}/{len(queue)}{Fore.RESET}")
            queue[i] = Probe(queue[i])
            
        # update the information
        thread = threading.Thread(target = info)
        thread.start()
        
        writeRecord(queue, probe_fold)

    skip = False
    number = 0
    while (1):
        if not skip:
            i=0
            while i < len(queue):
                if not queue[i].isMutated:
                    print(f"{Fore.BLUE}Start to exec SnippetMutate process for seed{i}! {i+1}/{len(queue)}{Fore.RESET}")
                    SnippetMutate(queue[i], restoreSeed)
                i=i+1
        skip = True
        number += 1
        print(f"{Fore.BLUE}Start to exec advanced_mutate process! the {round}th round({number}) {Fore.RESET}")
        skip = Havoc(queue, restoreSeed)
        if skip == False:
            round += 1
            number_array.append(number)
            number = 0

if __name__ == '__main__':
    main()