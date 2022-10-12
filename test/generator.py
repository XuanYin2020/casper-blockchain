'''
TODO: 未完成 （优先度低）
Generate user set, miners set and validators set
1. network server
2. 用于规模测试，创建用户集合，矿工集合和验证者集合
'''
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from key.ecdsaKey import generate_ECDSA_keys
from character.user import User
from character.miner import Miner
from flask import Flask, jsonify
from configuration.generalParameters import MINERS_SIZE, INIT_DYNASTY
from message.message import createVote
from key.signature import sign
import json

# func for connect with other miner node. Fully connects here
def complete_connect(miners):
    for i in range(0, len(miners)):
        for j in range(0, len(miners)):
            connect_host = miners[j].node.host
            connect_port = miners[j].node.port
            miners[i].node.connect_node(connect_host, connect_port)

# int miner, each miner is also a validator
miner_size = MINERS_SIZE
miners = []  # miner
ip_address = "127.0.0.1"
port_start = 8000
for i in range(miner_size):
    publickey, private_key = generate_ECDSA_keys()
    user = User(publickey, private_key)
    INIT_DYNASTY.append(user.username)
    miner = Miner(user, ip_address, port_start + i)
    miner.start()
    miners.append(miner)

# connect with other miner node
complete_connect(miners)

# each miners start mine
for each in miners:
    each.startMine()

# Create APIs
app = Flask(__name__, static_url_path="")

'''
    Path: /receive
    Desc: return the number of blocks and votes have received 
'''
@app.route('/receive', methods=['GET'])
def get_receives():
    sets = {}
    for _miner in miners:
        sets[_miner.user.username] = {
            "receive_blocks": len(_miner.node.receive_blocks),
            "receive_votes": len(_miner.node.receive_votes)
        }
    response = {
        'miners': sets
    }
    return jsonify(response), 200

'''
    Path: /all_ndoes
    Desc: return the connection of nodes 
'''
@app.route('/all_ndoes', methods=['GET'])
def get_all_ndoes():
    sets = {}
    for each in miners:
        sets[each.user.username] = (each.node.message_count_recv, str(each.node.all_nodes()))
    response = {
        'miners': sets
    }
    return jsonify(response), 200

'''
    Path: /head
    Desc: return the head of nodes 
'''
@app.route('/heads', methods=['GET'])
def get_heads():
    sets = {}
    for each in miners:
        sets[each.user.username] = (each.block_set[each.head]["height"], str(each.head),
                                    each.isAncestor(each.highest_justified_checkpoint["hash"], each.head))
    response = {
        'miners': sets
    }
    return jsonify(response), 200


'''
    Path: /checkpoint
    Desc: return all checkpoints of nodes 
'''
@app.route('/checkpoints', methods=['GET'])
def get_checkpoints():
    sets = {}
    for each in miners:
        sets[each.user.username] = each.checkpoint_set
    response = {
        'miners': sets
    }
    return jsonify(response), 200

'''
    Path: /blocktree
    Desc: return all blocks of nodes 
'''
@app.route('/blocktree', methods=['GET'])
def get_blocktree():
    sets = {}
    for each in miners:
        sets[each.user.username] = {}
        head = each.highest_justified_checkpoint['hash']

        for blockhash in each.block_set:
            previous_hash = each.block_set[blockhash]['block_information']['previous_hash']
            hash = each.block_set[blockhash]['hash']

            height = each.block_set[blockhash]['height']
            sets[each.user.username][blockhash]={}
            sets[each.user.username][blockhash]['dynasty'] = each.counter.dynasty.dynasties[
                each.counter.dynasty.current_epoch]
            sets[each.user.username][blockhash]['receive'] = {"receive_blocks": len(each.node.receive_blocks),
                                                              "receive_votes": len(each.node.receive_votes)}
            sets[each.user.username][blockhash]['penalty'] = each.counter.penalty
            sets[each.user.username][blockhash]['connection'] = (each.node.message_count_recv, str(each.node.all_nodes()))

            sets[each.user.username][blockhash]['previous_hash'] = previous_hash
            sets[each.user.username][blockhash]['hash'] = hash
            sets[each.user.username][blockhash]['height'] = height
            attribute = ''
            if height%5 != 0:
                attribute = 'block'
                sets[each.user.username][blockhash]['attribute'] = attribute
            elif blockhash in each.checkpoint_set:
                if blockhash == head:
                    attribute = 'head'
                else:
                    attribute = each.checkpoint_set[blockhash]['attribute']
                # attribute = each.checkpoint_set[blockhash]['attribute']
                sets[each.user.username][blockhash]['attribute'] = attribute
            sets[each.user.username][blockhash]['value'] = [height,attribute]
    response = {
        'blocks': sets
    }
    return jsonify(response), 200


'''
    Path: /counts
    Desc: return all vote counts of nodes 
'''
@app.route('/counts', methods=['GET'])
def get_counts():
    sets = {}
    for each in miners:
        counts = {}
        for source_hash in each.counter.count_forward.keys():
            source = each.checkpoint_set[source_hash]
            source_epoch = source["epoch"]
            if source_epoch not in counts:
                counts[source_epoch] = {}
            counts[source_epoch][source_hash] = each.counter.count_forward[source_hash]
        sets[each.user.username] = counts
    response = {
        'miners': sets
    }
    return jsonify(response), 200


'''
    Path: /history
    Desc: return recorded vote history counts of nodes 
'''
@app.route('/history', methods=['GET'])
def get_history():
    sets = {}
    for a in miners:
        sets[a.user.username] = len(a.counter.vote_history)
    response = {
        'miners': sets
    }
    return jsonify(response), 200

'''
    Path: /penalty
    Desc: return penalty recorded in each nodes 
'''
@app.route('/penalty', methods=['GET'])
def get_penalty():
    sets = {}
    for each in miners:
        sets[each.user.username] = each.counter.penalty
    response = {
        'miners': sets
    }
    return jsonify(response), 200


'''
    Path: /dynasty
    Desc: return current dynasty of each nodes
'''
@app.route('/dynasty', methods=['GET'])
def get_dynasty():
    sets = {}
    for each in miners:
        sets[each.user.username] = {
            "current_epoch": each.counter.dynasty.current_epoch,
            "dynasty": each.counter.dynasty.dynasties[each.counter.dynasty.current_epoch]}
    response = {
        'miners': sets
    }
    return jsonify(response), 200


'''
    Path: /highestJustifiedCheckpoint
    Desc: return highest justified checkpoint of  each nodes 
'''
@app.route('/highestJustifiedCheckpoint', methods=['GET'])
def get_highest_justified_checkpoint():
    sets = {}
    for each in miners:
        sets[each.user.username] = each.highest_justified_checkpoint
    response = {
        'miners': sets
    }
    return jsonify(response), 200


@app.route('/checkDependencies1', methods=['GET'])
def checkDependencies1():
    sets = {}
    for each in miners:
        sets[each.user.username] = {
            "vote_J": each.validator.vote_dependencies,
        }
    response = {
        'miners': sets
    }
    return jsonify(response), 200


@app.route('/checkDependencies', methods=['GET'])
def checkDependencies():
    sets = {}
    for each in miners:
        vote_ds = []
        for vote_d in each.validator.vote_dependencies.keys():
            if vote_d in each.checkpoint_set.keys():
                vote_ds.append(1)
            elif vote_d in each.block_set.keys():
                vote_ds.append(2)
            else:
                vote_ds.append(3)
        sets[each.user.username] = {
            "vote_J": vote_ds,
        }
    response = {
        'miners': sets
    }
    return jsonify(response), 200


'''
    Path: /blockTreeLen
    Desc: return some information for debug
'''
@app.route('/blockTreeLen', methods=['GET'])
def get_blockTreeLen():
    sets = {}
    for each in miners:
        vote_ds = []
        vote_dd = []
        for vote_d in each.validator.vote_dependencies:
            vote_ds.append((len(each.validator.vote_dependencies[vote_d])))
            vote_dd.append({vote_d: each.validator.vote_dependencies[vote_d]})
        sets[each.user.username] = {
            "vote": len(each.validator.vote_dependencies.keys()),
            "vote_ds": vote_ds,
            "vote_dd": vote_dd,
            "other": (each.counter.call_counter, each.counter.validate_call_counter, len(each.block_set.keys()),
                      len(each.block_dependencies))
        }
    response = {
        'miners': sets
    }
    return jsonify(response), 200

'''
    Path: /add
    Desc: add a new validator
'''
@app.route('/add', methods=['GET'])
def add():
    publickey, private_key = generate_ECDSA_keys()
    user = User(publickey, private_key)
    INIT_DYNASTY.append(user.username)
    miner = Miner(user, ip_address, port_start + len(miners))
    miners.append(miner)
    miner.start()
    complete_connect(miners)
    miner.joinDynasty()
    miner.startMine()

    response = {
        'result': publickey
    }
    return jsonify(response), 200

@app.route('/bad_vote', methods=['GET'])
def bad_vote():
    miner = miners[0]
    source = miner.root_checkpoint
    target = miner.highest_justified_checkpoint

    vote = createVote(source["vote_information"]["source_hash"], target["vote_information"]["target_hash"], source["vote_information"]["source_epoch"], target["vote_information"]["target_epoch"], miner.user.username)
    vote["signature"] = sign(miner.user.privkey, json.dumps(vote["vote_information"]))

app.run(host='0.0.0.0', port=5000)
