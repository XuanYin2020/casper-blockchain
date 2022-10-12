"""
Method Description: create a 'new_block' message's data
Parameters: transactions: the relational transactions for the current block
            previous_hash: the previous hash value for the current block
Return: block instance data
"""
def createBlock(transactions, previous_hash):
    block = {
        "block_information": {
            "previous_hash": previous_hash,
            "transactions": transactions,
            "proof": None
        },
        "hash": None,
        "height": None,
        "timestamp": None
    }
    return block

"""
Method Description: create a new transaction message data
Parameters: sender: the transaction 's sender for transaction information
            receiver: the transaction 's receiver for transaction information
Return: transaction instance data
"""
def createTransaction(sender, receiver, amount):
    transaction = {
        "transaction_information": {
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        },
        "signature": None
    }
    return transaction

"""
Method Description: create a new checkpoint message data
Parameters: block_hash: the current block's hash, which is also the current checkpoint's hash
            pre_checkpoint_hash: the previous checkpoint's hash
            epoch: the current checkpoint's epoch
Return: checkpoint instance data
"""
def createCheckpoint(block_hash, pre_checkpoint_hash, epoch):
    checkpoint = {
        "hash" : block_hash,
        "previous_checkpoint_hash": pre_checkpoint_hash,
        "epoch" : epoch,
        "attribute": "NORMAL"
    }
    return checkpoint



"""
Method Description: create a new vote message data
Parameters: source_hash: the hash of any justified checkpoint (the “source”)
            target_hash: any checkpoint hash that is a descendent of s (the “target”)
            source_epoch: h(s) the height of checkpoint s in the checkpoint tree
            target_epoch: h(t) the height of checkpoint t in the checkpoint tree
Return: vote instance data
"""
def createVote(source_hash, target_hash, source_epoch, target_epoch, validator):
    vote = {
        "vote_information":{
            "source_hash": source_hash,
            "target_hash": target_hash,
            "source_epoch": source_epoch,
            "target_epoch": target_epoch
        },
        "validator": validator,
        "signature": None

    }
    return vote