from key.signature import sign
from key.ecdsaKey import generate_ECDSA_keys
from message.message import createTransaction
import json

'''
User class is used to indicate the User character for the each miner and validator
'''


class User:
    """
    Method Description: Initialize a instance of User
    Parameters: pubkey: public key as user's username
                privkey: the private key
    """
    def __init__(self, pubkey, privkey, deposit=0):
        self.username = pubkey
        self.privkey = privkey
        self.deposit = deposit

    def transfer(self, receiver, amount):
        transaction = createTransaction(self.username, receiver, amount)
        transaction["signature"] = sign(self.privkey, json.dumps(transaction["transaction_information"]))



