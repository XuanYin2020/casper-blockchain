'''
dynamic validator set change
new validators to join and existing validators to leave
'''
import copy
import logging

logger = logging.getLogger(__name__)
from configuration.generalParameters import INIT_DYNASTY


class Dynasty:
    def __init__(self):
        # [(new,expert,retired)] d+2
        self.dynasties = [[[], INIT_DYNASTY, []], [[], [], []], [[], [], []]]
        self.current_epoch = 0  # d
        self.join_community = [] + INIT_DYNASTY
        # {validator_addr:[deposit,epoch]}
        self.deposit_bank = {}
        self.withdraw_delay = 1

    def joinDynasty(self, validator_address, deposit=1):
        '''
        func: apply to join the validator set
        args:
            validatorAddress: the identity of new validator
            deposit: the deposit of the new validator
        '''

        if not deposit or deposit <= 0:
            logger.warning('warning: validator %s please pay the deposit' % validator_address)
            return

        # A validator cannot join anymore if he/she has joined before even he/she has already quit
        if validator_address not in self.join_community:
            self.deposit_bank[validator_address] = [deposit, self.current_epoch]
            self.dynasties[self.current_epoch + 2][0].append(validator_address)
            # join
            self.join_community.append(validator_address)

    def quitDynasty(self, validator_address):
        '''
        func: apply to quit the validator set
        args:
            validatorAddress: the identity of new validator
        '''
        if validator_address in self.dynasties[self.current_epoch][1]:
            # join_dynasty changed to quit dynasty(d+2+5)
            self.deposit_bank[validator_address][1] = self.current_epoch + 2 + self.withdraw_delay
            self.dynasties[self.current_epoch + 2][2].append(validator_address)

        elif validator_address in self.dynasties[self.current_epoch + 1][0]:
            # join_dynasty changed to quit dynasty(d+2+5)
            self.deposit_bank[validator_address][1] = self.current_epoch + 2 + self.withdraw_delay
            self.dynasties[self.current_epoch + 2][0].remove(validator_address)
            self.dynasties[self.current_epoch + 2][2].append(validator_address)
        else:
            logger.warning('warning: %s not in the new and expert validator', str(validator_address))

    def dynastyChange(self):
        '''
        func: dynasty change
        '''
        # change epoch which is the number of finalized checkpoints
        self.current_epoch += 1
        self.dynasties.append([[], [], []])
        # get current dynasty
        current_dynasty = self.dynasties[self.current_epoch]

        # read the message in previous dynasty
        previous_dynasty = self.dynasties[self.current_epoch - 1]
        previous_new = set(copy.deepcopy(previous_dynasty[0]))
        previous_og = set(copy.deepcopy(previous_dynasty[1]))

        # update the message in current dynasty
        current_retire = set(copy.deepcopy(current_dynasty[2]))
        current_og = list(previous_og.union(previous_new) - current_retire)
        current_dynasty[1] = current_og
