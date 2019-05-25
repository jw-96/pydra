from copy import copy, deepcopy
from .helpers import ensure_list


class Graph:
    def __init__(self, nodes=None, edges=None):
        self.nodes = nodes
        self.edges = edges
        self._create_connections()
        self._sorted_nodes = None

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        if nodes:
            if len(set(nodes)) != len(nodes):
                raise Exception("nodes have repeated elements")
            self._nodes = nodes
        else:
            self._nodes = []

    @property
    def nodes_names(self):
        return [nd.name for nd in self.nodes]

    @property
    def edges(self):
        return self._edges

    @edges.setter
    def edges(self, edges):
        if edges:
            for (nd_out, nd_in) in edges:
                if nd_out not in self.nodes or nd_in not in self.nodes:
                    raise Exception(
                        f"edge {(nd_out, nd_in)} can't be added to the graph"
                    )
            self._edges = edges
        else:
            self._edges = []

    @property
    def edges_names(self):
        return [(edg[0].name, edg[1].name) for edg in self._edges]

    @property
    def sorted_nodes(self):
        if self._sorted_nodes is None:
            self.sorting()
        return self._sorted_nodes

    @property
    def sorted_nodes_names(self):
        return [nd.name for nd in self._sorted_nodes]

    def _create_connections(self):
        self._connections_pred = {}
        self._connections_succ = {}
        for nd in self.nodes:
            self._connections_pred[nd.name] = []
            self._connections_succ[nd.name] = []

        for (nd_out, nd_in) in self.edges:
            self._connections_pred[nd_in.name].append(nd_out)
            self._connections_succ[nd_out.name].append(nd_in)

    def add_nodes(self, new_nodes):
        # todo?
        self.nodes = self._nodes + ensure_list(new_nodes)
        for nd in ensure_list(new_nodes):
            self._connections_pred[nd.name] = []
            self._connections_succ[nd.name] = []
        if self._sorted_nodes is not None:
            # starting from the previous sorted list, so is faster
            self.sorting(presorted=self.sorted_nodes + ensure_list(new_nodes))

    def add_edges(self, new_edges):
        # todo?
        self.edges = self._edges + ensure_list(new_edges)
        for (nd_out, nd_in) in ensure_list(new_edges):
            self._connections_pred[nd_in.name].append(nd_out)
            self._connections_succ[nd_out.name].append(nd_in)
        if self._sorted_nodes is not None:
            # starting from the previous sorted list, so is faster
            self.sorting(presorted=self.sorted_nodes + [])

    def _sorting(self, notsorted_list, connections_pred):
        left_nodes = []
        sorted_part = []
        for nd in notsorted_list:
            if not connections_pred[nd.name]:
                sorted_part.append(nd)
            else:
                left_nodes.append(nd)
        return sorted_part, left_nodes

    def sorting(self, presorted=None):
        """sorting the graph"""
        self._sorted_nodes = []
        if presorted:
            notsorted_nodes = copy(presorted)
        else:
            notsorted_nodes = copy(self.nodes)
        connections_pred = {
            key: copy(val) for (key, val) in self._connections_pred.items()
        }

        while notsorted_nodes:
            sorted_part, notsorted_nodes = self._sorting(
                notsorted_nodes, connections_pred
            )
            self._sorted_nodes += sorted_part
            for nd_out in sorted_part:
                for nd_in in self._connections_succ[nd_out.name]:
                    connections_pred[nd_in.name].remove(nd_out)

    def remove_node(self, node):
        """removing a node, re-sorting if needed"""
        if node not in self.nodes:
            raise Exception(f"{node} is not present in the graph")
        if self._connections_pred[node.name]:
            raise Exception("this node shoudn't be run, has to wait")

        self.nodes.remove(node)
        for nd_in in self._connections_succ[node.name]:
            self._connections_pred[nd_in.name].remove(node)
            self.edges.remove((node, nd_in))
        self._connections_succ.pop(node.name)
        self._connections_pred.pop(node.name)

        # if graph is sorted, the sorted list has to be updated
        if hasattr(self, "sorted_nodes"):
            if node == self.sorted_nodes[0]:
                # if the first node is removed, no need to sort again
                self._sorted_nodes = self.sorted_nodes[1:]
            else:
                self._sorted_nodes.remove(node)
                # starting from the previous sorted list, so is faster
                self.sorting(presorted=self.sorted_nodes)
