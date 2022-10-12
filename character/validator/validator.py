'''
TODO：未完成
依赖：
'''
from message.message import createCheckpoint,createVote
from key.signature import sign, validateSignature
import json

class Validator():
    """For construct validator func and attributes, All the vote related attributes and func here

    """
    def __init__(self, miner):
        """
        """
        # the gate of accessing miner
        self.miner = miner

        # if a vote received before its related source and target received, it will be store here and waiting for process
        self.vote_dependencies = {}

        # All your voting history
        self.vote_history = {}

        # When ask for sync as a new node, the history vote recieved while its source is not justified, it will be store here and waiting for process
        self.vote_sync_dependencies ={}


    def acceptVote(self, vote):
        ''' Process vote when receive vote
        Args:
            vote: a dict object which contains information of vote
        '''
        # if source or target not received
        if vote["vote_information"]["source_hash"] not in self.miner.checkpoint_set:
            # store this vote into vote_dependencies {key(source) : vote }
            if vote["vote_information"]["source_hash"] not in self.vote_dependencies:
                self.vote_dependencies[vote["vote_information"]["source_hash"]] = []
            self.vote_dependencies[vote["vote_information"]["source_hash"]].append(vote)
            # self.miner.node.send_to_nodes({"ask_block": vote["vote_information"]["source_hash"]})
            return vote["vote_information"]["source_hash"]

        if vote["vote_information"]["target_hash"] not in self.miner.checkpoint_set:
            # store this vote into vote_dependencies {key(target) : vote }
            if vote["vote_information"]["target_hash"] not in self.vote_dependencies:
                self.vote_dependencies[vote["vote_information"]["target_hash"]] = []
            self.vote_dependencies[vote["vote_information"]["target_hash"]].append(vote)
            # self.miner.node.send_to_nodes({"ask_block": vote["vote_information"]["target_hash"]})
            return vote["vote_information"]["target_hash"]

        # If a history vote received while its source is not justified when do sync
        if self.miner.checkpoint_set[vote["vote_information"]["source_hash"]]["attribute"] != "JUSTIFIED":
            # store this vote into vote_sync_dependencies {key(source) : vote }
            if vote["vote_information"]["source_hash"] not in self.vote_sync_dependencies:
                self.vote_sync_dependencies[vote["vote_information"]["source_hash"]] = []
            # if vote not in self.vote_sync_dependencies[vote["vote_information"]["source_hash"]]:
            self.vote_sync_dependencies[vote["vote_information"]["source_hash"]].append(vote)
            return None

        # return true, means this vote condition meet (take 2/3 of all votes), then do prepare and commit.
        if self.miner.counter.countVote(vote):
            source = self.miner.checkpoint_set[vote["vote_information"]["source_hash"]]
            target = self.miner.checkpoint_set[vote["vote_information"]["target_hash"]]
            # prepare process
            # if source["attribute"] is JUSTIFIED:
            if source["attribute"] is "JUSTIFIED":
                # prepare as justified
                target["attribute"] = "JUSTIFIED"
                self.miner.justified_checkpoints.append(target["hash"])

                # update main_chain, record blocks from the last justified checkpoint to the nearest justified checkpoint before it.
                chain = []
                chain.append(target["hash"])
                pre_block = self.miner.block_set[target["hash"]]
                while pre_block["hash"] != self.miner.highest_justified_checkpoint["hash"]:
                    chain.append(pre_block["hash"])
                    pre_block = self.miner.block_set[pre_block["block_information"]["previous_hash"]]
                chain.reverse()
                self.miner.main_chain += chain

                # update highest justified checkpoint
                self.miner.highest_justified_checkpoint = target

                # process vote in vote_sync_dependencies?
                if target["hash"] in self.vote_sync_dependencies:
                    votes = self.vote_sync_dependencies[target["hash"]]
                    for vote in votes:
                        self.acceptVote(vote)

            # commit process
            # if (target["attribute"] == JUSTIFIED and source["attribute"] == JUSTIFIED and target["epoch"] - source["epoch"] == 1) or source["hash"] == self.miner.root_checkpoint["hash"]:
            if source["attribute"] == "JUSTIFIED" and ((target["attribute"] == "JUSTIFIED" and target["epoch"] - source["epoch"] == 1) or source["hash"] == self.miner.root_checkpoint["hash"]):
                source["attribute"] = "FINALIZED"
                self.miner.justified_checkpoints.remove(target["hash"])
                self.miner.finalized_checkpoints.append(source["hash"])
                # New finalized checkpoint occur，do dynasty change from d to d+1
                self.miner.counter.dynasty.dynastyChange()
        return None

    def generateVote(self, target):
        '''
        func: generate new vote
        Args:
            target: the target checkpoint
        '''

        # create vote by target and highest checkpoint
        vote = createVote(self.miner.highest_justified_checkpoint["hash"], target["hash"], self.miner.highest_justified_checkpoint["epoch"], target["epoch"], self.miner.user.username)
        vote["signature"] = sign(self.miner.user.privkey, json.dumps(vote["vote_information"]))

        # self accept this vote
        self.acceptVote(vote)
        # store personal vote history
        self.vote_history[self.miner.vote_epoch] = vote
        # broadcast vote to other nodes
        self.miner.node.send_to_nodes({"vote": json.dumps(vote)})
