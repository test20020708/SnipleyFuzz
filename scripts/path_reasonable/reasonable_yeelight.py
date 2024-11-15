import os
import sys
import time
import random
import time
import string
import threading
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binom

import pandas as pd
from scipy.cluster import hierarchy
from colorama import init, Fore

sys.path.append(r'..')
sys.path.append('./device/yeelight')
sys.path.append('./Fuzzing/IoT-Fuzzing')

from interact_yeelight import Messenger, SimilarityScore
from seed import Message, Seed

# Global var
queue = []
restoreSeed = '' # restoring message sequence
outputfold = ''
history_combination = [] # mutation index and type
crash_number = 0
number_array = []
round = 0
path_score = []
finish_flag = False
        
def stop():
    global finish_flag
    time.sleep(60 * 60)
    finish_flag = True

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
                pi[j] = p

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
    global queue, restoreSeed, path_score
    m = Messenger(restoreSeed)
    
    print(oldSeed.M[index].raw["Content"])
    
    response1 = m.sendMessage(oldSeed.M[index])
    time.sleep(1)
    response2 = m.sendMessage(oldSeed.M[index])
    
    path_and_score = {}
    path_and_score["response"] = response1
    path_and_score["score"] = SimilarityScore(response1.strip(), response2.strip())
    path_score.append(path_and_score)
    

def writeOutput(seed):
    global outputfold
    localtime = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    file = 'yeelight-Crash-' + str(crash_number) + ":" + localtime + '.txt'

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


# has been tested: Success!
def SnippetMutate(seed, restoreSeed):
    
    m = Messenger(restoreSeed)
    
    for i in range(len(seed.M)):
        pool = seed.PR[i]
        poolIndex = seed.PI[i]
        similarityScores = seed.PS[i]
    
        # update the number of times the message was used and the interval
        seed.M[i].number_used_message += 1
        seed.M[i].interval_message = 0
        for j in range(len(seed.M)):
            if j != i:
                seed.M[j].interval_message += 1
                
        print(f"{Fore.BLUE}Start to exec SnippetMutate process for Message{i}! {i+1}/{len(seed.M)}{Fore.RESET}")
        
        featureList = []
        for j in range(len(pool)):
            featureList.append(getFeature(pool[j].strip(), similarityScores[j]))
            
        df = pd.DataFrame(featureList)
        cluster = hierarchy.linkage(df, method='average', metric='euclidean')
        
        seed.ClusterList.append(cluster)
        
        mutatedSnippet = []
        for index in range(len(cluster)):
            snippetsList = formSnippets(poolIndex, cluster, index)
            snippet_all_info_array = {}
            snippet_info_array = []
            print(f"{Fore.BLUE}Start to exec SnippetMutate process for snippet in cluster round{index}! {index + 1}/{len(cluster)}{Fore.RESET}")
            
            # Initialize the snippet property for message
            for snippet in snippetsList:
                if "Fail to bind device" in pool[poolIndex[snippet[0]]]:
                    continue
                snippet_info = {}
                snippet_info["fragment"] = snippet
                snippet_info["number"] = 0
                snippet_info["shapley"] = 0
                snippet_info_array.append(snippet_info)
            snippet_all_info_array["snippets"] = snippet_info_array
            snippet_all_info_array["number"] = 0
            snippet_all_info_array["interested"] = 0
            seed.M[i].snippet.append(snippet_all_info_array)
            
            for snippet_index in range(len(seed.M[i].snippet[index]["snippets"])):
                snippet = seed.M[i].snippet[index]["snippets"][snippet_index]
                fragment = snippet["fragment"]
                seed.M[i].snippet[index]["snippets"][snippet_index]["number"] += 1
        
                if fragment not in mutatedSnippet:
                    mutatedSnippet.append(fragment)
                    
        seed.Snippet.append(mutatedSnippet)
    return 0


def advanced_mutate(queue, restoreSeed, snippet_index_single):
    
    m = Messenger(restoreSeed)
    
    global history_combination, path_score

    seed_index = 0
    seed = queue[seed_index]
    
    message_index = 0
    message = seed.M[message_index]
    
    cluster_round = 0
    snippets = message.snippet[cluster_round]["snippets"]
    
    number_mutation_segment = 1
    
    mutation_index = snippet_index_single
    mutation_index_array = []
    mutation_index_array.append(mutation_index)
    mutation_types = []
    mutation_types.append(random.randint(0, 6))
    
    # performing the corresponding mutation process
    tempMessage = queue[seed_index].M[message_index].raw["Content"]
    length_message = len(tempMessage)
    for i in range(number_mutation_segment):
        queue[seed_index] = mutation_generation(queue[seed_index], message_index, snippets[mutation_index_array[i]]["fragment"], mutation_types[i], length_message)
    
    flag = True
    
    if responseHandle(queue[seed_index], m.SnippetMutationSend(queue[seed_index], message_index, path_score)) == False:
        flag = False 
        queue[seed_index].M[message_index].raw["Content"] = tempMessage
        queue[seed_index].M[message_index].snippet[cluster_round]["snippets"][mutation_index_array[0]]["shapley"] += 1

    
    queue[seed_index].M[message_index].raw["Content"] = tempMessage
    print(f"{Fore.BLUE}There is no interseted in this advance mutation process!{Fore.RESET}")
        
    return flag



# has been tested: Success!               
def mutation_generation(seed, message_index, snippet, pick, length):
    print("*mutation generation")
    message = seed.M[message_index].raw["Content"]
    value = len(message) - length
    snippet[0] = snippet[0] + value
    snippet[1] = snippet[1] + value
    
    
    if pick == 0:
        # ========  BitFlip  ========
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            asc = asc + (chr(255 - ord(message[o])))
        message = message[:snippet[0]] + asc + message[snippet[1] + 1:]
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 1:
        # ========  Empty ==========
        message = message[:snippet[0]] + message[snippet[1] + 1:]
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
        
    elif pick == 2:
        # ========  Repeat ========
        t = random.randint(2, 5)
        message = message[:snippet[0]] + message[snippet[0]:snippet[1] + 1] * t + message[snippet[1] + 1:]
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
        
    elif pick == 3:
        # ======== Random Bytes Flip ===========
        index_array = []
        for index in range(snippet[0], snippet[1] + 1):
            index_array.append(index)
        mutation_number = random.randint(1, snippet[1] - snippet[0] + 1)
        mutation_array = random.sample(index_array, mutation_number)
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            if o in mutation_array:
                asc = asc + (chr(255 - ord(message[o])))
            else:
                asc = asc + message[o]
        message = message[:snippet[0]] + asc + message[snippet[1] + 1:]
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 4:
        # ========  Random Bytes delete ========
        index_array = []
        message_front = message[:snippet[0]]
        message_behind = message[snippet[1] + 1:]
        for index in range(snippet[0], snippet[1] + 1):
            index_array.append(index)
        mutation_number = random.randint(1, snippet[1] - snippet[0] + 1)
        mutation_array = random.sample(index_array, mutation_number)
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            if o in mutation_array:
                continue
            else:
                asc = asc + message[o]
        message = message_front + asc + message_behind
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 5:
        # ========  Random Bytes increase(Type one) ========
        index_array = []
        message_front = message[:snippet[0]]
        message_behind = message[snippet[1] + 1:]
        for index in range(snippet[0], snippet[1] + 1):
            index_array.append(index)
        mutation_number = random.randint(1, snippet[1] - snippet[0] + 1)
        mutation_array = random.sample(index_array, mutation_number)
        asc = ""
        mutation_type = random.randint(0, 2)
        if mutation_type == 0:
            for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
                if o in mutation_array:
                    asc = asc + message[o] + str(random.randint(0, 9))
                else:
                    asc = asc + message[o]
        elif mutation_type == 1:
            for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
                if o in mutation_array:
                    asc = asc + message[o] + random.choice(string.ascii_letters)
                else:
                    asc = asc + message[o]
        else:
            for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
                if o in mutation_array:
                    asc = asc + message[o] + random.choice(string.punctuation)
                else:
                    asc = asc + message[o]
        message = message_front + asc + message_behind
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 6:
        # ========  Random Bytes increase(Type one) ========
        index_array = []
        message_front = message[:snippet[0]]
        message_behind = message[snippet[1] + 1:]
        for index in range(snippet[0], snippet[1] + 1):
            index_array.append(index)
        mutation_number = random.randint(1, snippet[1] - snippet[0] + 1)
        mutation_array = random.sample(index_array, mutation_number)
        mutation_types = []
        for _ in range(mutation_number):
            mutation_types.append(random.randint(0,2))
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            if o in mutation_array:
                asc = asc + message[0]
                index_char = mutation_array.index(o)
                if mutation_types[index_char] == 0:
                    asc = asc + str(random.randint(0, 9))
                elif mutation_types[index_char] == 1:
                    asc = asc + random.choice(string.ascii_letters)
                else:
                    asc = asc + random.choice(string.punctuation)
            else:
                asc = asc + message[o]
        message = message_front + asc + message_behind
        seed.M[message_index].raw["Content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
        
    return seed


def main():
    global queue, restoreSeed, outputfold, number_array, round, finish_flag
    
    init()

    restorefile = './device/yeelight/yeelight_file/restoreSeed.txt'
    outputfold = './output/crash/yeelight'
    recordfile = './device/yeelight/yeelight_file/yeelight_ProbeRecord.txt'
    inputfold = './device/yeelight/yeelight_file/initial_seed'
    
    restoreSeed = readInputFile(restorefile)
    print(f"{Fore.BLUE}Successful read from the restorefile!{Fore.RESET}")
    
    queue = readInputFold(inputfold)
    queue = readRecordFile(recordfile)
    update_path_score(queue[0])
    
    # update the information
    thread = threading.Thread(target = stop)
    thread.start()
        
    i = 0
    while i < len(queue):
        if not queue[i].isMutated:
            SnippetMutate(queue[i], restoreSeed)
            queue[i].isMutated = True
        i = i + 1
    
    snippet_length = len(queue[0].M[0].snippet[0]["snippets"])
    
    while (1):
        if finish_flag:
            break
        for i in range(snippet_length):
            print(f"{Fore.BLUE}Start to exec advanced_mutate process! the {i}/{snippet_length - 1} {Fore.RESET}")
            advanced_mutate(queue, restoreSeed, i)
    
    print(f"{Fore.RED}********finish!!!!!********{Fore.RESET}")
    shapley = []
    labels = []
    
    for i in range(snippet_length):
        shapley.append(queue[0].M[0].snippet[0]["snippets"][i]["shapley"])
        labels.append("Sinppet" + str(i))
    
    path = "./output/path_reasonable/"
    file_name = "reasonable_yeelight.txt"
    with open(path + file_name, "w") as f:
        f.writelines("======== yeelight ========\n")
        for i in range(snippet_length):
            f.writelines(labels[i] + " : " + str(shapley[i]) + "\n")
            
    
    
if __name__ == '__main__':
    main()