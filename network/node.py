import socket
import time
import threading
from network.nodeconnection import NodeConnection

'''
Node class is used to establish the connection between different nodes, where each node can connect to other nodes and 
can also accept the connection of other nodes. The connection is created a  TCP/IP server with the given port
'''


class Node(threading.Thread):

    """
    Method Description: Initialize a instance of Node
    Parameters: character: the Miner class, that is the role corresponding to the node
                host: the host or ip address, used to bind the TCP/IP server
                port: the port number, used to bind the TCP/IP server
    Return: max:int
    """
    def __init__(self, character, host, port, callback=None):

        super(Node, self).__init__()

        # Store the vote/blocks/sync/checkpoint message received by node
        self.receive_votes = []
        self.receive_blocks = []
        self.receive_sync = []
        self.receive_checkpoint = []

        # The corresponding role for the node
        self.character = character
        # if the flag is set, the node will stop and close
        self.terminate_flag = threading.Event()

        # host and port,used to bind to and the port
        self.host = host
        self.port = port

        # Events are send back to the given callback
        self.callback = callback

        # For the established connection in the Node (Node -> self)
        self.nodes_inbound = []  # nodes that connect with the server
        # For the established connection from itself (self -> Node)
        self.nodes_outbound = [] # nodes that are connected to

        # Using the user's username (public key) as the fixed unique ID
        self.id = self.character.user.username

        # Start the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()

        # Message counters, used to track the total messages
        self.message_count_send = 0
        self.message_count_recv = 0
        self.message_count_rerr = 0

        # Debugging set
        self.debug = False

    """
    Method Description: get all the node in the inbound and ourbound
    Return: list of all node which is connect with itself
    """
    def all_nodes(self):
        return self.nodes_inbound + self.nodes_outbound

    """
    Method Description: print the debug message in the console
    """
    def debug_print(self, message):
        if self.debug:
            print("DEBUG: " + message)

    """
    Method Description: Initialize the TCP/IP server
    """
    def init_server(self):
        print("Initialisation of the Node on port: " + str(self.port) + " on node (" + self.id + ")")
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(None)
        self.sock.listen(5)


    """
    Method Description: Check the connection is still exited, and delete the disconnected node
    """
    def delete_closed_connections(self):
        for n in self.nodes_inbound:
            if n.terminate_flag.is_set():
                print("inbound_node_disconnected: " + n.id)
                n.join()
                del self.nodes_inbound[self.nodes_inbound.index(n)]

        for n in self.nodes_outbound:
            if n.terminate_flag.is_set():
                print("outbound_node_disconnected: " + n.id)
                n.join()
                del self.nodes_outbound[self.nodes_inbound.index(n)]


    """
    Method Description: send the data to all the connected node in the inbound and outbound
    Parameters: data: the send data, which can be str,dict or bytes objects.
    """
    def send_to_nodes(self, data):
        for n in (self.nodes_inbound + self.nodes_outbound):
            self.send_to_node(n, data)

    """
    Method Description: send the data to the connected node
    Parameters: data: the send data, which can be str,dict or bytes objects.
    """
    def send_to_node(self, n, data):
        self.message_count_send = self.message_count_send + 1
        self.delete_closed_connections()
        print("send_to_node Method: the n is :" +str(n))
        try:
            n.send(data)
            print("send_to_node Method: finished to send data : "+str(data))
        except Exception as e:
            print("send_to_node Method Error: sending data to the node (" + str(e) + ")")

    """
    Method Description: Connect the TCP/IP connection  to target node
    Parameters: target_host: The host of the target node
                target_port: The port of the target node
    """
    def connect_node(self, target_host, target_port):
        # Node cannot connect to itself
        if target_host == self.host and target_port == self.port:
            print("cannot connect to itself")
            return False
        # The connection to target node is already existed
        for node in self.nodes_outbound:
            if node.host == target_host and node.port == target_port:
                print("the connection is existed")
                return True

        # Connect to the target node
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((target_host, target_port))

        # To exchange basic information, first the node sends itself ID and then wait to receive the target node’s ID
        sock.send(self.id.encode('utf-8'))  # Send itself ID (source ID)to the target connected node
        target_node_id = sock.recv(4096).decode('utf-8')  # When the target is receive the source ID, it sends it id to source

        # To create the actual new connection
        node_connection = NodeConnection(self.character, self, sock, target_node_id, target_host, target_port)
        node_connection.start()

        # The connection is established
        self.nodes_outbound.append(node_connection)
        print("outbound_node_connected: " + self.id)

    """
    Method Description: Disconnect the connection with the specified node
    Parameters: node: the target node
    """
    def disconnect_with_node(self, node):
        # check the connection is in the outbound
        if node in self.nodes_outbound:
            print("Node disconnect_with_node: node wants to disconnect with other outbound node: " + node.id)
            node.stop()
            # join the thread, and the application is waiting
            node.join()
            del self.nodes_outbound[self.nodes_outbound.index(node)]
        else:
            print("Node disconnect_with_node: cannot disconnect with a node with which we are not connected.")

    """
    Method Description: top this node and terminate all the connected nodes.
    """
    def stop(self):
        print("node is requested to stop!")
        self.terminate_flag.set()
    """
    Method Description: The main loop of the thread that deals with connections from other nodes on the network.
    """
    def run(self):

        # Check whether the thread needs to be closed every 0.01s
        while not self.terminate_flag.is_set():
            try:
                connection, Initiator_address = self.sock.accept()

                # Receive the source connected node's ID, and then seng itself(target) ID
                Initiator_node_id = connection.recv(4096).decode('utf-8')
                connection.send(self.id.encode('utf-8'))

                # To create the actual new connection
                node_connection = NodeConnection(self.character, self, connection, Initiator_node_id, Initiator_address[0],
                                                 Initiator_address[1])
                node_connection.start()

                # The connction is established from other node
                self.nodes_inbound.append(node_connection)
                print("inbound_node_connected: " + node_connection.id)

            except socket.timeout:
                None
                #print('Node: Connection timeout!')

            # Listening socket to receive message every 0.01
            time.sleep(0.01)

        # Stop all conncetion
        print("Node stopping...")
        for t in self.nodes_inbound:
            t.stop()
        for t in self.nodes_outbound:
            t.stop()
        time.sleep(1)
        for t in self.nodes_inbound:
            t.join()
        for t in self.nodes_outbound:
            t.join()
        #close sock
        self.sock.settimeout(None)
        self.sock.close()
        print("Node stopped")



    def __str__(self):
        return 'Node: {}:{}'.format(self.host, self.port)

    def __repr__(self):
        return '<Node {}:{} id: {}>'.format(self.host, self.port, self.id)
