"""
========================
Cycle finding algorithms
========================

"""

#    Copyright (C) 2010 by 
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    All rights reserved.
#    BSD license.


#   This file has been customised by Aleix Altimiras Martin from Networkx v1.6
#   In particular the simple_cycles routine has been transformed in a 
#   generator function. Apparently a similar implementation will be included 
#   in next releases of NetworkX
#   This file corresponds to cycles.py in networkx v1.6.
#   The pull request corresponding to similar changes is 
#   https://github.com/networkx/networkx/pull/890


import networkx as nx
from collections import defaultdict
from itertools import islice
import pdb#        pdb.set_trace() 

__all__ = ['cycle_basis','simple_cycles']

__author__ = "\n".join(['Jon Olav Vik <jonovik@gmail.com>', 
                        'Aric Hagberg <hagberg@lanl.gov>'])

def cycle_basis(G,root=None):
    """ Returns a list of cycles which form a basis for cycles of G.

    A basis for cycles of a network is a minimal collection of 
    cycles such that any cycle in the network can be written 
    as a sum of cycles in the basis.  Here summation of cycles 
    is defined as "exclusive or" of the edges. Cycle bases are 
    useful, e.g. when deriving equations for electric circuits 
    using Kirchhoff's Laws.

    Parameters
    ----------
    G : NetworkX Graph
    root : node, optional 
       Specify starting node for basis.

    Returns
    -------
    A list of cycle lists.  Each cycle list is a list of nodes
    which forms a cycle (loop) in G.

    Examples
    --------
    >>> G=nx.Graph()
    >>> G.add_cycle([0,1,2,3])
    >>> G.add_cycle([0,3,4,5])
    >>> print(nx.cycle_basis(G,0))
    [[3, 4, 5, 0], [1, 2, 3, 0]]

    Notes
    -----
    This is adapted from algorithm CACM 491 [1]_. 

    References
    ----------
    .. [1] Paton, K. An algorithm for finding a fundamental set of 
       cycles of a graph. Comm. ACM 12, 9 (Sept 1969), 514-518.

    See Also
    --------
    simple_cycles
    """
    if G.is_directed():
        e='cycle_basis() not implemented for directed graphs'
        raise Exception(e)
    if G.is_multigraph():
        e='cycle_basis() not implemented for multigraphs'
        raise Exception(e)

    gnodes=set(G.nodes())
    cycles=[]
    while gnodes:  # loop over connected components
        if root is None:
            root=gnodes.pop()
        stack=[root]
        pred={root:root} 
        used={root:set()}
        while stack:  # walk the spanning tree finding cycles
            z=stack.pop()  # use last-in so cycles easier to find
            zused=used[z]
            for nbr in G[z]:
                if nbr not in used:   # new node 
                    pred[nbr]=z
                    stack.append(nbr)
                    used[nbr]=set([z])
                elif nbr is z:        # self loops
                    cycles.append([z]) 
                elif nbr not in zused:# found a cycle
                    pn=used[nbr]
                    cycle=[nbr,z]
                    p=pred[z]
                    while p not in pn:
                        cycle.append(p)
                        p=pred[p]
                    cycle.append(p)
                    cycles.append(cycle)
                    used[nbr].add(z)
        gnodes-=set(pred)
        root=None
    return cycles


def simple_cycles(G,list_of_nodes=[],list_of_edges=[],SplitResult=True):
    """Find simple cycles (elementary circuits) of a directed graph.
    
    An simple cycle, or elementary circuit, is a closed path where no 
    node appears twice, except that the first and last node are the same. 
    Two elementary circuits are distinct if they are not cyclic permutations 
    of each other.

    Parameters
    ----------
    G : NetworkX DiGraph
       A directed graph
    list_of_nodes : (optional) a list of nodes
    list_of_edges : (optional) a list of edges
    

    Returns
    -------
    A list of circuits, where each circuit is a list of nodes, with the first
    and last node being the same. The list of circuits can be negatively 
    filtered by nodes (only circuits NOT containing the nodes defined in 
    list_of_nodes are included in the results) or positively filtered by edges 
    (only circuits containing the edges defined in list_of_edges are included
    in the result). The filtering options can be used independently or together.
    
    Example:
    >>> G = nx.DiGraph([(0, 0), (0, 1), (0, 2), (1, 2), (2, 0), (2, 1), (2, 2)])
    >>> nx.simple_cycles(G)
    [[0, 0], [0, 1, 2, 0], [0, 2, 0], [1, 2, 1], [2, 2]]
    >>> nx.simple_cycles(G,[0])
    [[1, 2, 1], [2, 2]]
    >>> nx.simple_cycles(G,[0],[[1,2]])
    [[1, 2, 1]]
    >>> nx.simple_cycles(G,[],[[1,2]])
    [[0, 1, 2, 0], [1, 2, 1]]
    
    See Also
    --------
    cycle_basis (for undirected graphs)
    
    Notes
    -----
    The implementation follows pp. 79-80 in [1]_.

    The time complexity is O((n+e)(c+1)) for n nodes, e edges and c
    elementary circuits.

    References
    ----------
    .. [1] Finding all the elementary circuits of a directed graph.
       D. B. Johnson, SIAM Journal on Computing 4, no. 1, 77-84, 1975. 
       http://dx.doi.org/10.1137/0204007

    See Also
    --------
    cycle_basis
    """
    # Jon Olav Vik, 2010-08-09
    def _unblock(thisnode):
        """Recursively unblock and remove nodes from B[thisnode]."""
        if blocked[thisnode]:
            blocked[thisnode] = False
            while B[thisnode]:
                _unblock(B[thisnode].pop())
    
    def circuit(thisnode, startnode, component):
        closed = False # set to True if elementary path is closed
        path.append(thisnode)
        blocked[thisnode] = True
        if SplitResult == False:
            for nextnode in component[thisnode]: # direct successors of thisnode        
                if nextnode == startnode:
                    result.append(path + [startnode])
                    closed = True                
                elif not blocked[nextnode]:
                    if circuit(nextnode, startnode, component):
                        closed = True
                # Pop out the cycles NOT containing an edge from list_of_edges         
                if result != [] and list_of_edges != []:
                    for edge in list_of_edges:
                        #pdb.set_trace() 
                        if not contains_sequence(result[len(result)-1],edge):
                            result.pop(len(result)-1)
                            break
                        # if it is not a directed graph, pop out cycles containing
                        # the edge inverse.
                        if not G.is_directed() and not contains_sequence(result[len(result)-1],edge.reverse()):
                            result.pop(len(result)-1)
                            break
        else:
            for nextnode in component[thisnode]: # direct successors of thisnode        
                if nextnode == startnode:
                    result[nbr_result_arrays].append(path + [startnode])
                    closed = True                
                elif not blocked[nextnode]:
                    if circuit(nextnode, startnode, component):
                        closed = True
                # Pop out the cycles NOT containing an edge from list_of_edges         
                if result[nbr_result_arrays] != [] and list_of_edges != []:
                    for edge in list_of_edges:
                        #pdb.set_trace() 
                        if not contains_sequence(result[nbr_result_arrays][len(result[nbr_result_arrays])-1],edge):
                            result[nbr_result_arrays].pop(len(result)-1)
                            break
                        # if it is not a directed graph, pop out cycles containing
                        # the edge inverse.
                        if not G.is_directed() and not contains_sequence(result[nbr_result_arrays][len(result[nbr_result_arrays])-1],edge.reverse()):
                            result[nbr_result_arrays].pop(len(result)-1)
                            break
                if len(result[nbr_result_arrays])==1000000:
                     result.append([])
                     nbr_result_arrays+=1
        if closed:
            _unblock(thisnode)
        else:
            for nextnode in component[thisnode]:
                if thisnode not in B[nextnode]: # TODO: use set for speedup?
                    B[nextnode].append(thisnode)
        path.pop() # remove thisnode from path
        return closed
    
    if not G.is_directed():
        raise nx.NetworkXError(\
            "simple_cycles() not implemented for undirected graphs.")
            
    # check whether edges well defined in list_of_edges
    for edge in list_of_edges:
        #pdb.set_trace()
        if len(edge) !=2:
            raise nx.NetworkXError(\
            'Input Error in the list_of_edges: the defined edge {0} does not exactly contain 2 nodes.'.format(edge))
            
      
    path = [] # stack of nodes in current path
    blocked = defaultdict(bool) # vertex: blocked from search?
    B = defaultdict(list) # graph portions that yield no elementary circuit
    pdb.set_trace() 
    if SplitResult == False:
        result = [] # list to accumulate the circuits found
    elif SplitResult == True:
        result = [[]] # list of lists to accumulate the circuits found
        nbr_result_arrays=0
    else:
        raise nx.NetworkXError(\
            "The fourth argument must be a boolean.")
    # Johnson's algorithm requires some ordering of the nodes.
    # They might not be sortable so we assign an arbitrary ordering.

    # New definition of the ordering. It is not "random" any more
    # The first positions are given to the nodes to skip.
    if list_of_nodes == []:
        ordering=dict(zip(G,range(len(G))))
        # for debugging purposes
        #print('''the ordering is {0}'''.format(ordering))
    elif type(list_of_nodes) is list:
        ordering=dict(zip(list_of_nodes,range(len(list_of_nodes))))
        node_counter=len(list_of_nodes)
        for node in range(len(G)):
            if node not in list_of_nodes:
                ordering[node]=node_counter
                node_counter+=1
        # for debugging purposes
        #print('''the ordering is {0}'''.format(ordering))
    else:
        raise nx.NetworkXError(\
            "The first optional argument list_of_nodes is not a list")
    for s in ordering:
        # Build the subgraph induced by s and following nodes in the ordering
        # NEW CODE: now that ordering has nodes to bypass in the first positions
        #           skip the processing if the node to process is in the list.
        if s in list_of_nodes:
            continue
        subgraph = G.subgraph(node for node in G 
                              if ordering[node] >= ordering[s])
         
        # Find the strongly connected component in the subgraph 
        # that contains the least node according to the ordering
        strongcomp = nx.strongly_connected_components(subgraph)
        mincomp=min(strongcomp, 
                    key=lambda nodes: min(ordering[n] for n in nodes))
        component = G.subgraph(mincomp)
        if component:
            # smallest node in the component according to the ordering
            startnode = min(component,key=ordering.__getitem__) 
            for node in component:
                blocked[node] = False
                B[node][:] = []
            dummy=circuit(startnode, startnode, component)

    return 

# Functions defined to check whether an edge is contained in a cycle
#code from http://stackoverflow.com/questions/11131185/is-there-a-python-builtin-for-determining-if-an-iterable-contained-a-certain-seq

## Here, the window is 2 because the arc is defined by 2 nodes
def window(seq, n=2):
    """
    Returns a sliding window (of width n) over data from the iterable
    s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   
    """
    it = iter(seq)
    result = list(islice(it, n))
    if len(result) == n:
        yield result    
    for elem in it:
        result = result[1:] + [elem]
        yield result

def contains_sequence(all_values, seq):
    return any(seq == current_seq for current_seq in window(all_values, len(seq)))


def simple_cycles_generator(G):
    """Find simple cycles (elementary circuits) of a directed graph.
    
    An simple cycle, or elementary circuit, is a closed path where no 
    node appears twice, except that the first and last node are the same. 
    Two elementary circuits are distinct if they are not cyclic permutations 
    of each other.

    Parameters
    ----------
    G : NetworkX DiGraph
       A directed graph

    Returns
    -------
    A list of circuits, where each circuit is a list of nodes, with the first 
    and last node being the same.
    
    Example:
    >>> G = nx.DiGraph([(0, 0), (0, 1), (0, 2), (1, 2), (2, 0), (2, 1), (2, 2)])
    >>> nx.simple_cycles(G)
    [[0, 0], [0, 1, 2, 0], [0, 2, 0], [1, 2, 1], [2, 2]]
    
    See Also
    --------
    cycle_basis (for undirected graphs)
    
    Notes
    -----
    The implementation follows pp. 79-80 in [1]_.

    The time complexity is O((n+e)(c+1)) for n nodes, e edges and c
    elementary circuits.

    References
    ----------
    .. [1] Finding all the elementary circuits of a directed graph.
       D. B. Johnson, SIAM Journal on Computing 4, no. 1, 77-84, 1975. 
       http://dx.doi.org/10.1137/0204007

    See Also
    --------
    cycle_basis
    """
    # Jon Olav Vik, 2010-08-09
    def _unblock(thisnode):
        """Recursively unblock and remove nodes from B[thisnode]."""
        if blocked[thisnode]:
            blocked[thisnode] = False
            while B[thisnode]:
                _unblock(B[thisnode].pop())
    
    def circuit(thisnode, startnode, component):
        #pdb.set_trace()
        closed = False # set to True if elementary path is closed
        path.append(thisnode)
        blocked[thisnode] = True
        for nextnode in component[thisnode]: # direct successors of thisnode
            if nextnode == startnode:
                yield path + [startnode]
                closed = True
            elif not blocked[nextnode]:
                for cycle in circuit(nextnode, startnode, component):
                    yield cycle
                    closed = True
        if closed:
            _unblock(thisnode)
        else:
            for nextnode in component[thisnode]:
                if thisnode not in B[nextnode]: # TODO: use set for speedup?
                    B[nextnode].append(thisnode)
        path.pop() # remove thisnode from path
        return #closed
    
    if not G.is_directed():
        raise nx.NetworkXError(\
            "simple_cycles() not implemented for undirected graphs.")
    path = [] # stack of nodes in current path
    blocked = defaultdict(bool) # vertex: blocked from search?
    B = defaultdict(list) # graph portions that yield no elementary circuit
    # in the generator function, no need to define a result array 
    #result = [] # list to accumulate the circuits found
    # Johnson's algorithm requires some ordering of the nodes.
    # They might not be sortable so we assign an arbitrary ordering.
    
    ordering=dict(zip(G,range(len(G))))
    for s in ordering:
        # Build the subgraph induced by s and following nodes in the ordering
        subgraph = G.subgraph(node for node in G 
                              if ordering[node] >= ordering[s])
        # Find the strongly connected component in the subgraph 
        # that contains the least node according to the ordering
        strongcomp = nx.strongly_connected_components(subgraph)
        mincomp=min(strongcomp, 
                    key=lambda nodes: min(ordering[n] for n in nodes))
        component = G.subgraph(mincomp)
        if component:
            # smallest node in the component according to the ordering
            startnode = min(component,key=ordering.__getitem__) 
            for node in component:
                blocked[node] = False
                B[node][:] = []
            #dummy=circuit(startnode, startnode, component)
            circuit_gen=circuit(startnode, startnode, component)
            for cycle in circuit_gen:
                yield cycle

    return