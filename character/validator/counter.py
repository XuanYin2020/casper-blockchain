'''
TODO: 未完成（中）
Count votes and store votes history related to specified validator
1. 数vote的数量，判断有没有2/3
2. 记录每一个validator的投票历史
'''
from rule.dynasty import Dynasty
from rule.rule import invalidatorDetect
import json
from key.signature import validateSignature

class Counter:
    """ Count votes and store votes history related to specified validator
    Attributes:
        count: record votes and used for requirement of prepare and commit
        voteHistory:record vote history of each validator and used for slashing detection
    """
    def __init__(self):
        """init counter
        Args:
        Return:
            None
        """
        # 初始化dynasty
        self.validate_call_counter = 0  # just count how many times this func has been validated called
        self.call_counter = 0  # just count how many times this func has been called

        self.dynasty = Dynasty()

        self.count_forward = {}  # {source : {target : count} } 对forward validator set进行计数
        self.count_rear = {}  # {source : {target : count} } 对rear validator set进行计数

        self.vote_history = {}  # {validator_id(the pubkey of specific validator) : [vote](list)}

        self.penalty = {}  # record penalty for who against slashing conditions

    def countVote(self, vote):
        """Do count here

        Args:
            vote: vote information

        Return:
            True or False
        """
        # only process a same vote once
        if vote["validator"] in self.vote_history:
            for each in self.vote_history[vote["validator"]]:
                if (json.dumps(vote["vote_information"])) == json.dumps(each):
                    return False

        self.call_counter += 1
        if vote["validator"] in self.vote_history:
            # when slashing conditions occur
            if not invalidatorDetect(self.vote_history[vote["validator"]], vote["vote_information"]):
                if vote["validator"] not in self.penalty:
                    self.penalty[vote["validator"]] = []
                self.penalty[vote["validator"]].append((vote))
                print("Penlity!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                return
        self.validate_call_counter += 1
        voter = vote["validator"]
        source = vote["vote_information"]["source_hash"]
        target = vote["vote_information"]["target_hash"]
        current_dynasty = self.dynasty.dynasties[self.dynasty.current_epoch]

        # count
        if voter in current_dynasty[0]:
            if source not in self.count_forward:
                self.count_forward[source] = {}
            self.count_forward[source][target] = self.count_forward[source].get(target, 0) + 1

        elif voter in current_dynasty[1]:
            if source not in self.count_forward:
                self.count_forward[source] = {}
            self.count_forward[source][target] = self.count_forward[source].get(target, 0) + 1

            if source not in self.count_rear:
                self.count_rear[source] = {}
            self.count_rear[source][target] = self.count_rear[source].get(target, 0) + 1

        elif voter in current_dynasty[2]:
            if source not in self.count_rear:
                self.count_rear[source] = {}
            self.count_rear[source][target] = self.count_rear[source].get(target, 0) + 1
        else:
            print("invalidate voter")
            return
        self.recordVotes(vote)

        # forward and rear counts
        if self.count_forward[source][target] >= ((len(current_dynasty[0]) + len(current_dynasty[1])) * 2) // 3 \
                and self.count_rear[source][target] >= ((len(current_dynasty[2]) + len(current_dynasty[1])) * 2) // 3:
            return True  # True means reach 2/3
        else:
            return False  # False means un reach 2/3


    def recordVotes(self, vote):
        """ record votes
        Args:
            vote: vote

        Return:
            None
        """

        # int self.voteHistory[validate_vote.voter_identifier]为list
        if vote["validator"] not in self.vote_history:
            self.vote_history[vote["validator"]] = []
        # record vote_information
        self.vote_history[vote["validator"]].append(vote["vote_information"])