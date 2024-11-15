###
# 'Seed' is used to store the seeds for fuzzing process
# 'Seed' attrs - [ M : Message List (Class 'Message')   - to store the list of messages;
#                  R : Response List (String)           - to sotre the list of response messages corresponding to the message list (M) one-to-one by index]
###

class Seed:
    M = [] # Message List
    R = [] # Response List
    
    PR = [] # Probe message response pool 
    PS = [] # Probe message response self-similarity scores (the set)
    PI = [] # the index of response for every probe message
    
    isMutated = False
    number_used = 0
    interval = 1
    number_interested = 0
    
    ClusterList = []  # the final cluster result
    Snippet = [] # the final message snippet
    
    def __init__(self) -> None:
        self.M = []
        self.R = []
        self.PR = []
        self.PS = []
        self.PI = []
        self.isMutated = False
        self.number_used = 0
        self.interval = 1
        self.number_interested = 0
        self.ClusterList = []
        self.Snippet = []
        
    def append(self, message):
        self.M.append(message)
        
    def response(self, response):
        self.R.append(response)
        
    def display(self):
        print("**** Seed Information ****")
        print("Seed number used: " + str(self.number_used))
        print("Seed interested number: " + str(self.number_interested))
        print("Seed last used: " + str(self.interval))
        print("**** Message Information ****")
        for i in range(0, len(self.M)):
            print("=== Message index: ", i + 1)
            for header in self.M[i].headers:
                print(header, ":", self.M[i].raw[header])
            print('Response : ' + self.R[i])
            if self.PR and self.PS and self.PI:
                print('Probe Result:')
                print('PI')
                print(self.PI[i])
                print('PR and PS')
                for n in range(len(self.PR[i])):
                    print("(" + str(n) + ") " + self.PR[i][n])
                    print(self.PS[i][n])
                    
    
###
# 'Message' is used to store the message information
# 'Seed' attrs - [ headers : Header List        (String List)                                   - to store all the headers in the message;
#                  raw : Header and corresponding content (Dictionary - { Header : Content } )  - to sotre the list of response messages corresponding to the message list (M) one-to-one by index]
###

class Message:
    headers = []  # Header List
    raw = {}  # Header and corresponding content
    snippet = []  # code snippet { fragment : [start, end], number : the number of usage, shapley : the shapley value of the snippet }
    
    number_used_message = 0
    interval_message = 1
    number_interested_message = 0

    def __init__(self) -> None:
        self.headers = []
        self.raw = {}
        self.snippet = []
        self.number_used_message = 0
        self.interval_message = 1
        self.number_interested_message = 0

    def append(self, line) -> None:
        if ":" in line:
            sp = line.split(":")
            if sp[0] in self.headers:
                print("Error. Message headers '", sp[0], "' is duplicated.")
            else:
                self.headers.append(sp[0])
                self.raw[sp[0]] = line[(line.index(':') + 1):]