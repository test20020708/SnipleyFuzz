import os
import sys
import time
import random
import time
import string
import threading
import math

import numpy as np
from scipy.stats import binom

import pandas as pd
from scipy.cluster import hierarchy
from colorama import init, Fore

sys.path.append(r'..')
sys.path.append('./device/xiaomi')
sys.path.append('./Fuzzing/IoT-Fuzzing')

from interact_xiaomi import Messenger, SimilarityScore
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

def info():
    global queue, crash_number, number_array, path_score
    while(1):
        seed_number = len(queue)
        number_sum = 0
        for number in number_array:
            number_sum += number
        if len(number_array) != 0:
            average = number_sum / len(number_array)
        else:
            average = 0 
        with open(os.path.join('./scripts/ablation/share', 'xiaomi_camera-M-SN.txt'), 'w') as f:
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
    file = 'Xiaomi-camera-M-SN-Crash-' + str(crash_number) + ":" + localtime + '.txt'

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
        poolIndex_tmp = []
        for ii in poolIndex:
            poolIndex_tmp.append(ii)
    
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
                if "Fail to bind device" in pool[poolIndex_tmp[snippet[0]]]:
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


def sim_score_for_seed(seed1, seed2):
    message_list = []
    n = 2
    for message2 in seed2.M:
        message_list.append(message2.raw["content"].strip())

    similarity_score = 0
    for message1 in seed1.M:
        score_list = []
        for content in message_list:
            score_list.append(calculate_ngram_similarity_message(message1.raw["content"].strip(), content, n))
        score_for_message = max(score_list)
        similarity_score += score_for_message
        index = score_list.index(score_for_message)
        message_list.pop(index)
    
    similarity_score /= len(seed1.M)
    return similarity_score


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


def generate_ngrams(text, n):
    # Generates an N-gram of the specified length
    ngrams = []
    text_length = len(text)
    for i in range(text_length - n + 1):
        ngrams.append(text[i:i+n])
    return ngrams


def calculate_ngram_similarity_message(text1, text2, n):
    # Calculate the N-gram similarity between two texts
    ngrams1 = generate_ngrams(text1, n)
    ngrams2 = generate_ngrams(text2, n)
    
    # Computes intersection and union
    intersection = len(set(ngrams1).intersection(ngrams2))
    union = len(set(ngrams1).union(ngrams2))

    # Associative editing distance
    edit_distance = EditDistanceRecursive(text1, text2)
    similarity = (intersection / union) - (edit_distance / max(len(text1), len(text2)))
    return similarity
    

# has been tested: Success!
def seed_potential(queue):

    ratio_PR = 0.1
    ratio_interested = 1 - ratio_PR
    least_probability = 0.2
    
    score_array = []
    potential_array = []
    
    # calculate seed score
    for seed in queue:
        average_PR = 0
        for i in range(len(seed.M)):
            average_PR += len(seed.PR[i])
        average_PR = average_PR / len(seed.M)
        average_interested = seed.number_interested / len(seed.M)
        score = ratio_PR * average_PR + ratio_interested * average_interested
        score_array.append(score)
        
    # calculate seed potential
    for i in range(len(queue)):
        similarity = 0
        for j in range(len(queue)):
            similarity += score_array[j] * sim_score_for_seed(queue[i], queue[j])
        potential_array.append(similarity)
        
    # process the potential
    max_potential = max(potential_array)
    min_potential = min(potential_array)
    if max_potential == min_potential:
        for i in range(len(potential_array)):
            potential_array[i] = 1
    else:
        increase = (1 - least_probability) / (max_potential - min_potential)
        for i in range(len(potential_array)):
            potential_array[i] = least_probability + increase * (potential_array[i] - min_potential)
    
    return potential_array


# has been tested: Success!
def message_potential(seed):

    ratio_PR_message = 0.1
    ratio_interested_message = 1 - ratio_PR_message
    least_probability = 0.05
    n = 2
    
    score_array_message = []
    potential_array_message = []
    
    # calculate message score
    for i in range(len(seed.M)):
        score_message = ratio_PR_message * len(seed.PR[i]) + ratio_interested_message * seed.M[i].number_interested_message
        score_array_message.append(score_message)
        
    # calculate message potential
    for i in range(len(seed.M)):
        similarity = 0
        for j in range(len(seed.M)):
            similarity += score_array_message[j] * calculate_ngram_similarity_message(seed.M[i].raw["content"].strip(), seed.M[j].raw["content"].strip(), n)
        potential_array_message.append(similarity)
        
    # process message potential
    max_potential = max(potential_array_message)
    min_potential = min(potential_array_message)
    if max_potential == min_potential:
        for i in range(len(potential_array_message)):
            potential_array_message[i] = 1
    else:
        increase = (1 - least_probability) / (max_potential - min_potential)
        for i in range(len(potential_array_message)):
            potential_array_message[i] = least_probability + increase * (potential_array_message[i] - min_potential)

    return potential_array_message


def discrete_exponential(p, n_samples):
    samples = np.arange(1, n_samples + 1)
    probabilities = (1 - p)**samples * p
    probabilities /= np.sum(probabilities)
    return np.random.choice(samples, size=1, p=probabilities)


def advanced_mutate(queue, restoreSeed):
    
    m = Messenger(restoreSeed)
    
    global history_combination, path_score
    
    ###
    # Priority should be used for seed selection
    # Factors related to priority include: （1）Similarity to the highest-scoring seed -- the potential of seed
    #                                      （2）Number of times the seed has been used
    #                                      （3）The number of times since the seed was last used
    ###
    ratio_potential = 0.75
    ratio_number = 0.2
    ratio_interval = 1 - ratio_potential - ratio_number
    
    potential = seed_potential(queue)
    number = []
    interval = []
    priority = []
    probability = []
    seed_index_array = []
    for i in range(len(queue)):
        seed_index_array.append(i)
    
    # process the number of times the seed has been used
    for seed in queue:
        number.append(seed.number_used)
    max_number = max(number)
    min_number = min(number)
    if max_number == min_number:
        for i in range(len(number)):
            number[i] = 1
    else:
        increase_number = 1 / (max_number - min_number)
        for i in range(len(number)):
            number[i] = 1 - increase_number * (number[i] - min_number)

    # process the number of times since the seed was last used
    for seed in queue:
        interval.append(seed.interval)
    max_interval = max(interval)
    min_interval = min(interval)
    if max_interval == min_interval:
        for i in range(len(interval)):
            interval[i] = 1
    else:
        increase_interval = 1 / (max_interval - min_interval)
        for i in range(len(interval)):
            interval[i] = increase_interval * (interval[i] - min_interval)      
        
    # caculate the priority of seed
    all_priority = 0
    for i in range(len(queue)):
        priority_seed = ratio_potential * potential[i] + ratio_number * number[i] + ratio_interval * interval[i]
        priority.append(priority_seed)
        all_priority += priority_seed
        
    # caculate the probability of seed
    for i in range(len(queue)):
        probability.append(priority[i] / all_priority)
    
    # choose a seed according to probability
    seed_index = random.choices(seed_index_array, weights = probability, k = 1)[0]
    seed = queue[seed_index]
    
    # update the information of seed
    queue[seed_index].number_used += 1
    queue[seed_index].interval = 0
    for i in range(len(queue)):
        if i != seed_index:
            queue[i].interval += 1
            
    
    ###
    # Priority should be used for message selection
    # Factors related to priority include: (1) Similarity to the highest-scoring message -- the potential of message
    #                                      (2) Numbers of times message has been used
    #                                      (3) Numbers of times since the message was last uesd
    ###
    ratio_potential_message = 0.75
    ratio_number_message = 0.2
    ratio_interval_message = 1 - ratio_potential_message - ratio_number_message
    
    potential_message = message_potential(seed)
    number_message = []
    interval_message = []
    priority_message = []
    probability_message = []
    message_index_array = []
    for i in range(len(seed.M)):
        message_index_array.append(i)
    
    # process the number of times the message has been used
    for i in range(len(seed.M)):
        number_message.append(seed.M[i].number_used_message)
    max_number_message = max(number_message)
    min_number_message = min(number_message)
    if max_number_message == min_number_message:
        for i in range(len(number_message)):
            number_message[i] = 1
    else:
        increase_number_message = 1 / (max_number_message - min_number_message)
        for i in range(len(number_message)):
            number_message[i] = 1 - increase_number_message * (number_message[i] - min_number_message)
        
    # process the number of times since the message was last used
    for i in range(len(seed.M)):
        interval_message.append(seed.M[i].interval_message)
    max_interval_message = max(interval_message)
    min_interval_message = min(interval_message)
    if max_interval_message == min_interval_message:
        for i in range(len(interval_message)):
            interval_message[i] = 1
    else:
        increase_interval_message = 1 / (max_interval_message - min_interval_message)
        for i in range(len(interval_message)):
            interval_message[i] = increase_interval_message * (interval_message[i] - min_interval_message)
    
    # calculate the priority of message
    all_priority_message = 0
    for i in range(len(seed.M)):
        priority_message_single = ratio_potential_message * potential_message[i] + ratio_number_message * number_message[i] + ratio_interval_message * interval_message[i]
        priority_message.append(priority_message_single)
        all_priority_message += priority_message_single
    
    # calculate the probability of message
    for i in range(len(priority_message)):
        probability_message.append(priority_message[i] / all_priority_message)
        
    # choose a message according to probability
    message_index = random.choices(message_index_array, weights = probability_message, k = 1)[0]
    message = seed.M[message_index]
    
    # update the information of message
    queue[seed_index].M[message_index].number_used_message += 1
    queue[seed_index].M[message_index].interval_message = 0
    for i in range(len(seed.M)):
        if i != message_index:
            queue[seed_index].M[i].interval_message += 1
   
    
    ### 
    # selecting the number of clustering rounds according to the binomial distribution
    # The clustering performance is best in the middle rounds.
    ###
    
    ratio_cluster_interested = 0.95
    ratio_cluster_number = 1 - ratio_cluster_interested
    
    cluster_interested = []
    cluster_number = []
    priority_cluster = []
    probability_cluster = []
    cluster_index_array = []
    temp_array = []
    for i in range(len(message.snippet)):
        cluster_index_array.append(i)
        temp_array.append(1)
        
    # process the interested number of a cluster
    for i in range(len(message.snippet)):
        cluster_interested.append(message.snippet[i]["interested"])
    max_cluster_interested = max(cluster_interested)
    min_cluster_interested = min(cluster_interested)
    if max_cluster_interested == min_cluster_interested:
        for i in range(len(message.snippet)):
            cluster_interested[i] = 1
    else:
        cluster_interested_increase = 1 / (max_cluster_interested - min_cluster_interested)
        for i in range(len(message.snippet)):
            cluster_interested[i] = cluster_interested_increase * (cluster_interested[i] - min_cluster_interested)
    
    # process the number of times snippet has been used
    for i in range(len(message.snippet)):
        cluster_number.append(message.snippet[i]["number"])
    max_cluster_number = max(cluster_number)
    min_cluster_number = min(cluster_number)
    if max_cluster_number == min_cluster_number:
        for i in range(len(message.snippet)):
            cluster_number[i] = 1
    else:
        cluster_number_increase = 1 / (max_cluster_number - min_cluster_number)
        for i in range(len(message.snippet)):
            cluster_number[i] = 1 - cluster_number_increase * (cluster_number[i] - min_cluster_number)
    
    # calculate the priority of snippet
    all_priority_cluster = 0
    for i in range(len(message.snippet)):
        priority_cluster_single = ratio_cluster_interested * cluster_interested[i] + ratio_cluster_number * cluster_number[i]
        priority_cluster.append(priority_cluster_single)
        all_priority_cluster += priority_cluster_single
        
    # calculate the probability of message
    for i in range(len(message.snippet)):
        probability_cluster.append(priority_cluster[i] / all_priority_cluster)
    
    if (len(temp_array) == len(cluster_interested) and all(x == y for x, y in zip(temp_array, cluster_interested))) and (len(temp_array) == len(cluster_number) and all(x == y for x, y in zip(temp_array, cluster_number))):
        # setting the parameters of the binomial distribution
        n = len(message.snippet) - 1
        p = 0.5
        
        x = np.arange(0, n + 1)
        pmf = binom.pmf(x, n, p)
        
        cluster_round = random.choices(x, weights = pmf, k = 1)[0]
        snippets = message.snippet[cluster_round]["snippets"]
    else:
        cluster_round = random.choices(cluster_index_array, weights = probability_cluster, k = 1)[0]
        snippets = message.snippet[cluster_round]["snippets"]
        
    # update the information of cluster
    message.snippet[cluster_round]["number"] += 1
    
    # randomly selecting the number of mutation segments
    number_mutation_segment = discrete_exponential(0.35, len(snippets))[0]

    snippet_index_array = []
    for i in range(len(snippets)):
        snippet_index_array.append(i)
    
    Regeneration = True

    while Regeneration == True:
        # Select the fragments that need to be mutated according to the weight
        mutation_index_array = []
        mutation_number = 0   
        while (1) :
            mutation_index = int(random.choice(snippet_index_array))
            while mutation_index in mutation_index_array:
                mutation_index = int(random.choice(snippet_index_array))
            mutation_index_array.append(mutation_index)
            mutation_number += 1
            if mutation_number == number_mutation_segment:
                break
        mutation_index_array = sorted(mutation_index_array)        
        
        # Random selection of mutation types
        mutation_types = []
        for _ in range(number_mutation_segment):
            mutation_types.append(random.randint(0, 6))
                
        history_combination_information = {}
        history_combination_information["mutation_index"] = mutation_index_array
        history_combination_information["mutation_type"] = mutation_types
        
        if history_combination_information in history_combination:
            Regeneration = True
        else:
            Regeneration = False
    
    # performing the corresponding mutation process
    tempMessage = queue[seed_index].M[message_index].raw["content"]
    length_message = len(tempMessage)
    for i in range(number_mutation_segment):
        queue[seed_index] = mutation_generation(queue[seed_index], message_index, snippets[mutation_index_array[i]]["fragment"], mutation_types[i], length_message)
    
    flag = True
    
    if responseHandle(queue[seed_index], m.SnippetMutationSend(queue[seed_index], message_index, path_score)) == False:
        
        # update the history combination
        history_combination_information = {}
        history_combination_information["mutation_index"] = mutation_index_array
        history_combination_information["mutation_type"] = mutation_types
        history_combination.append(history_combination_information)
        flag = False
        
        response = m.sendMessage(queue[seed_index].M[message_index])
        
        queue[seed_index].M[message_index].raw["content"] = tempMessage
    
    queue[seed_index].M[message_index].raw["content"] = tempMessage
    print(f"{Fore.BLUE}There is no interseted in this advance mutation process!{Fore.RESET}")
        
    return flag


# has been tested: Success!               
def mutation_generation(seed, message_index, snippet, pick, length):
    print("*mutation generation")
    message = seed.M[message_index].raw["content"]
    value = len(message) - length
    snippet[0] = snippet[0] + value
    snippet[1] = snippet[1] + value
    
    
    if pick == 0:
        # ========  BitFlip  ========
        asc = ""
        for o in range(min(snippet[0],len(message) - 1), min(snippet[1] + 1, len(message) - 1)):
            asc = asc + (chr(255 - ord(message[o])))
        message = message[:snippet[0]] + asc + message[snippet[1] + 1:]
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 1:
        # ========  Empty ==========
        message = message[:snippet[0]] + message[snippet[1] + 1:]
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
        
    elif pick == 2:
        # ========  Repeat ========
        t = random.randint(2, 5)
        message = message[:snippet[0]] + message[snippet[0]:snippet[1] + 1] * t + message[snippet[1] + 1:]
        seed.M[message_index].raw["content"] = message
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
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 4:
        # ========  Interesting ========
        interestingString = ['siid','piid','True','False','0','1']
        interesting = random.randint(0,5)
        t = interestingString[interesting]
        message = message[:snippet[0]] + t + message[snippet[1] + 1:]
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 5:
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
        seed.M[message_index].raw["content"] = message
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
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
    
    elif pick == 7:
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
        seed.M[message_index].raw["content"] = message
        snippet[0] = snippet[0] - value
        snippet[1] = snippet[1] - value
        return seed
        
    return seed


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
        
        # update the information
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
            queue[i].display()
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
            i = 0
            while i < len(queue):
                if not queue[i].isMutated:
                    queue[i].number_used += 1
                    queue[i].interval = 0
                    for j in range(len(queue)):
                        if j != i:
                            queue[j].interval += 1
                    print(f"{Fore.BLUE}Start to exec SnippetMutate process for seed{i}! {i+1}/{len(queue)}{Fore.RESET}")
                    SnippetMutate(queue[i], restoreSeed)
                    queue[i].isMutated = True
                i = i + 1
        skip = True
        number += 1
        print(f"{Fore.BLUE}Start to exec advanced_mutate process! the {round}th round({number}) {Fore.RESET}")
        skip = advanced_mutate(queue, restoreSeed)
        if skip == False:
            round += 1
            number_array.append(number)
            number = 0
    
if __name__ == '__main__':
    main()