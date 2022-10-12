'''
已完成
'''
from hash.hash import computeHash
import json

class proofOfWork:
    def __init__(self, difficulty=1):
        self.difficulty = difficulty
        self._continue = -1

    def changeDifficulty(self, difficulty):
        self.difficulty = difficulty

    def getAnswer(self):
        ## The front n char is 0
        answer = ''
        for i in range(self.difficulty):
            answer += '0'
        return answer

    def startMatch(self):
        self._continue = 0

    def stopMatch(self):
        self._continue += 1


    '''
    Method description: Compute hash according to the difficulty
    Parameters: block_information: the block's information
    Return: the hash value, and the proof value
    '''
    #
    def mine(self, block_information):
        proof = 1
        while self._continue == 0:
            hash = computeHash((json.dumps(block_information) + str(proof)))
            if hash[:self.difficulty] == self.getAnswer():
                return hash, proof
            else:
                proof += 1
        if self._continue > 0:
            self._continue -= 1
        return None, None
