from proposalMechanism.pow import proofOfWork
from key.signature import validateSignature
from configuration.generalParameters import POW_DIFFICULTY
from character.validator.counter import Counter
import threading
import time
import json
from message.message import createTransaction, createBlock, createCheckpoint
from network.MyOwnPeer2PeerNode import MyOwnPeer2PeerNode
from hash.hash import computeHash
from character.validator.validator import Validator
from configuration.generalParameters import EPOCH_TIME

'''
Miner class is used to indicate the Miner character for the application
'''

class Miner(threading.Thread):

    """
    Method Description: Initialize a instance of Miner
    Parameters: user: the related user class instance, each miner is a user
                host: the host or ip address, used to bind the TCP/IP server
                port: the port number, used to bind the TCP/IP server

    """
    def __init__(self, user, host, port):
        super(Miner, self).__init__()

        self.con = threading.Condition()
        self.isStart = -1  # This attribute is used to determine whether to mine or not
        self.user = user  # the miner also acts as a user

        # Create the node class instance with the current Miner, used to communicate
        self.node = MyOwnPeer2PeerNode(self, host, port)  # 用于消息传递
        self.node.start()

        # Each miner is a validator by default
        self.validator = Validator(self)
        # Message buffer, waiting to accept parent node
        self.block_dependencies = {}

        self.vote_epoch = 0

        # Compute the root hash
        root = createBlock("root", None)  # root block
        root["hash"] = computeHash(json.dumps(root["block_information"]))
        root["height"] = 0

        # Initial the tree of blocks
        self.block_set = {}
        self.block_set[root["hash"]] = root

        # store the information about Pre-block and their successors.
        self.block_link = {}
        # head to indicates the current block where the miner should be mining
        self.head = root["hash"]

        # initial the pow instance to mine a block
        self.pow = proofOfWork(POW_DIFFICULTY)

        # the transaction pool, which related to the block information
        self.transactionPool = []

        # reward to miner a new block
        self.allocatedTransactions = []
        self.minerReward = 50

        # the preblock for each block ( each block only have a pre-block, but a block may have multi children)
        self.preblock_child = {'': [root]}  # {pre block's hash: []}

        # Validator related properties
        self.root_checkpoint = createCheckpoint(root["hash"], None, 0)
        self.root_checkpoint["attribute"] = "JUSTIFIED"

        #Initialize checkpoint set and record all checkpoints
        self.checkpoint_set = {self.root_checkpoint["hash"]: self.root_checkpoint}
        self.justified_checkpoints = [self.root_checkpoint["hash"]]
        self.finalized_checkpoints = []
        self.main_chain = [self.root_checkpoint["hash"]]

        # to record the highest justified checkpoint
        self.highest_justified_checkpoint = self.root_checkpoint

        # Initialize counter, vote count and recorder
        self.counter = Counter()

    """
    Method Description: used to determine whether miner should continue to mine a new block.
                        If not, miner will stop mining until the attribute isStart is reset
    """
    def run(self):
        while True:
            if self.isStart == 0:
                self.mineBlock()
            elif self.isStart > 0:
                self.isStart -= 1
    """
    Method Description: Synchronize all nodes from the highest justified node
    """
    def sync(self):
        self.node.send_to_nodes({"sync": self.highest_justified_checkpoint})

    """
    Method Description: Verify the validity of the new block and duplicate check to accept a new block for the miner.
    Parameter: a instance of block class
    """
    def acceptBlock(self, block):
        # The block is not accepted yet
        if block["hash"] not in self.block_set:
            # If the parent block of the block is not None and has not received it
            if block["block_information"]["previous_hash"] not in self.block_set and block["block_information"]["previous_hash"] is not None:
                # waiting to receive the pre block
                if block["block_information"]["previous_hash"] not in self.block_dependencies:
                    self.block_dependencies[block["block_information"]["previous_hash"]] = []
                if block not in self.block_dependencies[block["block_information"]["previous_hash"]]:
                    self.block_dependencies[block["block_information"]["previous_hash"]].append(block)
                return block["block_information"]["previous_hash"]

            # accept the new block, and receive the block in the block set
            self.block_set[block["hash"]] = block

            # update the pre block and current block information
            if block["block_information"]["previous_hash"] not in self.block_link:
                self.block_link[block["block_information"]["previous_hash"]] = []
            self.block_link[block["block_information"]["previous_hash"]].append(block)

            # It is the time to broadcast a vote message for miner as validator
            if block["height"] % EPOCH_TIME == 0:  # and self.vote_epoch < block["height"] / EPOCH_TIME
                previous_checkpoint_hash = self.findNearestCheckpoint(block)
                checkpoint = createCheckpoint(block["hash"], previous_checkpoint_hash, (block["height"] / EPOCH_TIME))
                # record the current checkpoint
                self.checkpoint_set[checkpoint["hash"]] = checkpoint

                # If it is a validator, judge whether to vote or not
                if self.validator is not None and self.vote_epoch < checkpoint["epoch"]:
                    self.vote_epoch += 1  # block["height"] / EPOCH_TIME
                    # Initiate the voting process
                    self.validator.generateVote(checkpoint)
                    # 发起投票

            # invoke the method to reset the miner's head
            self.forkChooseRule(block)

            # handle voter_dependencies
            if block["hash"] in self.validator.vote_dependencies:
                d_votes = self.validator.vote_dependencies.pop(block["hash"])
                for d_vote in d_votes:
                    self.validator.acceptVote(d_vote)

            # handle block_dependencies
            if block["hash"] in self.block_dependencies:
                d_blocks = self.block_dependencies.pop(block["hash"])
                for d_block in d_blocks:
                    self.acceptBlock(d_block)
        return None

    """
    Method Description: find the nearest checkpoint for the block
    Parameter: a instance of block class
    Return: a block which is the nearest checkpoint
    """
    def findNearestCheckpoint(self, block):
        previous_block_hash = block["block_information"]["previous_hash"]
        previous_block = self.block_set[previous_block_hash]

        while previous_block["height"] % EPOCH_TIME != 0:
            previous_block = self.block_set[previous_block["block_information"]["previous_hash"]]

        return previous_block["hash"]
    """
    Method Description: for miner start to mine a new block
    """
    def startMine(self):
        self.pow.startMatch()
        self.isStart = 0
    """
    Method Description: for miner stop to mine a new block
    """
    def stopMine(self):
        self.isStart += 1
        self.pow.stopMatch()

    """
    Method Description: get 10 transactions for each block 
    """
    def allocateTransactions(self):
        while len(self.transactionPool) > 0 and len(self.allocatedTransactions) < 10:
            transaction = self.transactionPool.pop(0)
            self.allocatedTransactions.append(transaction)
    """
    Method Description: mine a new block 
    """
    def mineBlock(self):
        # Check whether the head of miner is on the highest justified checkpoint
        if not self.isAncestor(self.highest_justified_checkpoint["hash"], self.head):
            print("wrong head")
            self.resetHead()

        # Set miner reward transaction
        reward_transaction = createTransaction("y3w", self.user.username, self.minerReward)

        # Verify the validity of all transactions in transaction pool
        for transaction in self.transactionPool:
            if not validateSignature(transaction["transaction_information"]["sender"], transaction["signature"],
                                     json.dumps(transaction["transaction_information"])):
                raise Exception("invalid transaction found")

        # Allocate Transaction to Block
        self.allocateTransactions()
        self.allocatedTransactions.insert(0, reward_transaction)

        # create a new block
        new_block = createBlock(self.allocatedTransactions, self.head)
        # Set the block's height
        new_block["height"] = (self.block_set[self.head]["height"] + 1)
        # invoke the method to mine the new block
        new_block["hash"], new_block["block_information"]["proof"] = self.pow.mine(new_block["block_information"])

        # not get the new block
        if new_block["hash"] == None or new_block["block_information"]["proof"] == None:
            print(self.user.username + " Stop mine!!!!!!!!!!!!!!!!!!!")
            # clean the allocated transaction
            self.allocatedTransactions = []
            return
        else:
            # Set timestamp
            new_block["timestamp"] = time.time()

            print(
                str(new_block["height"]) + " " + "Miner: " + self.user.username + "Mine end: " + json.dumps(new_block))
            # get the new block
            if new_block["hash"] not in self.block_set:
                self.allocatedTransactions = []
                # 自身接收新的block
                self.acceptBlock(new_block)
                # broadcast to all miner and validator,there is a new block
                self.node.send_to_nodes({"new_block": json.dumps(new_block)})
    """
    Method Description: add the block to it pre-block's children list
    Parameter: a instance of block
    """
    def addChildToPrehash(self, block):

        child_list = []
        # For miner, check that the current block's pre-block already has children in miner
        if self.preblock_child.get(block["block_information"]["previous_hash"], 0) != 0:
            child_list = self.preblock_child.get(block["block_information"]["previous_hash"], 0)
        # update the children list
        child_list.append(block)
        self.preblock_child.update({block["block_information"]["previous_hash"]: child_list})

    """
    Method Description: reset head when detect its not on the chain of highest justified checkpoint
    """
    def resetHead(self):
        print("reset head")
        all_peaks = self.findPeaks(self.highest_justified_checkpoint)
        if len(all_peaks) == 0:
            self.head = self.highest_justified_checkpoint["hash"]
        else:
            _head = all_peaks[0]
            for i in range(len(all_peaks)):
                if all_peaks[i]["height"] > _head["height"]:
                    _head = all_peaks[i]
            self.head = _head["hash"]

    """
    Method Description: Reset the head when receive the new block
    Parameters: new_block: the received the new block
    """
    def forkChooseRule(self, new_block):
        if self.isAncestor(self.highest_justified_checkpoint["hash"], new_block["hash"]):
            if str(self.head) == str(new_block["block_information"]["previous_hash"]):
                self.stopMine()
                self.head = new_block["hash"]
        else:
            self.stopMine()
            self.resetHead()

    def findPeaks(self, block):
        all_peak = []
        if block["hash"] in self.block_link:
            children = self.block_link[block["hash"]]
            for child in children:
                all_peak += self.findPeaks(child)
        return all_peak


    """
    Method Description: check weather the anc_hash is ancestor of the  desc_hash 
    Parameters: new_block: the received the new block
    """
    def isAncestor(self, anc_hash, desc_hash):
        if anc_hash == desc_hash:
            return True
        anc = self.block_set[anc_hash]
        desc = self.block_set[desc_hash]

        # Get desc's father's hash
        desc_anc_hash = desc["block_information"]["previous_hash"]
        while desc_anc_hash in self.block_set and desc_anc_hash is not None and desc_anc_hash != "":
            desc_anc = self.block_set[desc_anc_hash]
            if desc_anc["hash"] == anc["hash"]:
                return True
            elif desc_anc["height"] <= anc["height"]:
                return False
            # keep forward tracking
            desc_anc_hash = self.block_set[desc_anc["block_information"]["previous_hash"]]["hash"]
        return False

    def joinDynasty(self):
        # request for join
        self.node.send_to_nodes({"join_request": self.user.username})


