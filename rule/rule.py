'''
description: invalidator detection. (slashing condition)
parameters: validator: obj, new_votes: set
return: Boolean
'''
def invalidatorDetect(vote_history, new_votes):

    for prev_vote in vote_history:
        if prev_vote["target_epoch"] == new_votes["target_epoch"]:
            return False
        if ((prev_vote["source_epoch"] < new_votes["source_epoch"] and prev_vote["target_epoch"] > new_votes["target_epoch"]) or
            (prev_vote["source_epoch"] > new_votes["source_epoch"] and prev_vote["target_epoch"] < new_votes["target_epoch"])):
            return False
    return True