import hashlib

"""
Method Description: compute the hash value based on the information
Parameters: information: corresponding information
Return: the hash value 
"""
def computeHash(information):
    return str(hashlib.sha256((information.encode('utf-8'))).hexdigest())