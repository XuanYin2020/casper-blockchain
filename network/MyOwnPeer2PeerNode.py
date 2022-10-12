from network.node import Node


class MyOwnPeer2PeerNode(Node):

    # Python class constructor
    def __init__(self, miner, host, port):
        super(MyOwnPeer2PeerNode, self).__init__(miner, host, port, None)
        print("MyPeer2PeerNode: Started")

    def outbound_node_connected(self, node):
        print("outbound_node_connected: " + node.id)

    def inbound_node_connected(self, node):
        print("inbound_node_connected: " + node.id)

    def inbound_node_disconnected(self, node):
        print("inbound_node_disconnected: " + node.id)

    def outbound_node_disconnected(self, node):
        print("outbound_node_disconnected: " + node.id)

    def node_message(self, node, data):
        # print("node_message from " + node.id + ": " + str(data))
        self.receive_block.append(data)
        # print(self.receive_data)
        # TODO:将new block加到现有的chain上

    def node_disconnect_with_outbound_node(self, node):
        print("node wants to disconnect with oher outbound node: " + node.id)

    def node_request_to_stop(self):
        print("node is requested to stop!")

