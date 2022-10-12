import socket
import time
import threading
import json
from message.message import createCheckpoint,createVote
from key.signature import sign, validateSignature

"""
Class Description: This class is used to establish the real TCP/IP socket connection by the class Node with other node
"""
class NodeConnection(threading.Thread):
    """
    Method Description: Initialize a instance of NodeConnection
    Parameters: character: the Miner class, that is the role corresponding to the node
                main_node: the node class, to received a connection
                sock     : the socket, to associated with the client connection.
                id       : the unique id for the connected node, which is the target side of connection
                host and port: the host/ip and port of the main node
    """
    def __init__(self, character, main_node, sock, id, host, port):

        super(NodeConnection, self).__init__()
        # Store the receive transactions message
        self.receive_transactions = []

        # The corresponding role for the node
        self.character = character

        #the main node's host and port information
        self.host = host
        self.port = port
        self.main_node = main_node
        self.sock = sock
        self.terminate_flag = threading.Event()

        # The id of the connected node
        self.id = id

        # End of transmission character for the network streaming messages.
        self.EOT_CHAR = 0x04.to_bytes(1, 'big')

        # Datastore to store additional information concerning the node.
        self.info = {}

        self.main_node.debug_print(
            "NodeConnection.send: Started with client (" + self.id + ") '" + self.host + ":" + str(self.port) + "'")

    '''
    Method description : 
    Input: data : the send data, which can be str,dict or bytes objects.
           encoding_type : using utf-8/ascii to decode the packets ate the other node.
    '''
    def send(self, data, encoding_type='utf-8'):

        if isinstance(data, str):  # the send data is str type
            self.sock.sendall(data.encode(encoding_type) + self.EOT_CHAR)  # using end of transmission character
        elif isinstance(data, dict):  # the send data is dict type
            try:
                # data is converted to JSON that is send over to the other node
                json_data = json.dumps(data)
                json_data = json_data.encode(encoding_type) + self.EOT_CHAR
                self.sock.sendall(json_data)
            except TypeError as type_error:
                print('This dict is invalid')
            except Exception as e:
                print('Unexpected Error in send message')
        elif isinstance(data, bytes):  # the send data is bytes type
            bin_data = data + self.EOT_CHAR
            self.sock.sendall(bin_data)
        else:
            print('datatype used is not valid plese use str, dict (will be send as json) or bytes')


    def check_message(self, data):
        return True

    '''
    Method description : Stop the node client. 
    '''
    def stop(self):
        self.terminate_flag.set()

    '''
    Method description: decode the packet
    Return: the decoded data
    '''
    def decode_packet(self, packet):
        try:
            packet_decoded = packet.decode('utf-8')
            try:
                return json.loads(packet_decoded)
            except json.decoder.JSONDecodeError:
                return packet_decoded
        except UnicodeDecodeError:
            return packet

    '''
    Method description: The main loop of the node client, the thread waits to receive data from another node.
    '''
    def run(self):

        self.sock.settimeout(10.0)
        buffer = b''  # Hold the stream that comes in!

        while not self.terminate_flag.is_set():
            chunk = b''

            # to receive the data
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                self.main_node.debug_print("NodeConnection: timeout")

            except Exception as e:
                self.terminate_flag.set()
                self.main_node.debug_print('Unexpected error')
                self.main_node.debug_print(e)

            # the data is received
            if chunk != b'':
                buffer += chunk
                eot_pos = buffer.find(self.EOT_CHAR) # find the end character in buffer
                while eot_pos > 0:
                    packet = buffer[:eot_pos]  # cut end character
                    buffer = buffer[eot_pos + 1:]
                    data = self.decode_packet(packet)

                    # duplicate removal: Remove the repeated received message
                    if data != "" and data != None:

                        # Determine the type of data received
                        # receive a new block message with string 'new_block'
                        if data not in self.main_node.receive_blocks and 'new_block' in data.keys():
                            self.main_node.message_count_recv += 1
                            self.main_node.receive_blocks.append(data)

                            block = json.loads(data["new_block"])
                            # invoke the method to accept block for miner character
                            ask_block_hash = self.character.acceptBlock(block)

                            if ask_block_hash != None:
                                # ask the pre block hash
                                self.main_node.send_to_node(self, {
                                    "ask_block": ask_block_hash})

                        # receive a vote message with string 'vote'
                        elif data not in self.main_node.receive_votes and 'vote' in data.keys():
                            self.main_node.message_count_recv += 1
                            self.main_node.receive_votes.append(data)

                            vote = json.loads(data["vote"])

                            # invoke the method to check weather accept vote message
                            ask_block_hash = self.character.validator.acceptVote(vote)

                            # if the vote epoch can be found in history vote, response with your history vote
                            if vote["vote_information"]["target_epoch"] in self.character.validator.vote_history:
                                self.main_node.send_to_node(self, {"vote": json.dumps(self.character.validator.vote_history[vote["vote_information"]["target_epoch"]])})

                            # ask for block if the target or source Related vote is not existed in the recorded history
                            if ask_block_hash != None:
                                self.main_node.send_to_node(self, {
                                    "ask_block": ask_block_hash})
                        # receive asking a block message with string 'ask_block' to ask the new block
                        elif 'ask_block' in data.keys():
                            print("Receive thr ask_block messgae")
                            block_hash = data["ask_block"]
                            if block_hash in self.character.block_set:
                                self.main_node.send_to_node(self, {"new_block": json.dumps(self.character.block_set[block_hash])})

                        eot_pos = buffer.find(self.EOT_CHAR)

            time.sleep(0.01)

        self.sock.settimeout(None)
        self.sock.close()
        self.main_node.debug_print("NodeConnection: Stopped")

    def set_info(self, key, value):
        self.info[key] = value

    def get_info(self, key):
        return self.info[key]

    def __str__(self):
        return 'NodeConnection: {}:{} <-> {}:{} ({})'.format(self.main_node.host, self.main_node.port, self.host,
                                                             self.port, self.id)

    def __repr__(self):
        return '<NodeConnection: Node {}:{} <-> Connection {}:{}>'.format(self.main_node.host, self.main_node.port,
                                                                          self.host, self.port)
