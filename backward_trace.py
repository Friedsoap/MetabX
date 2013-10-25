#!/usr/bin/python
# -*- coding: utf-8 -*-

# Filename: backward_trace.py


'''
This module contains all sub-modules necessary to decompose Zind,ac between Zind,ac,a and Zind,ac,c and finding rind,ac,a and rind,ac,c by backtracing the purely acyclic flows associated to find and by considering the interactiong between Zind,c and Zind,ac
'''

import pdb#        pdb.set_trace() 
import numpy as np
import sys
import time
from itertools import islice
import pprint as pprint
import networkx as nx

def main(Zind_ac, find, rind_ac, Zind_c):
    '''This function decomposes Zind,ac between Zind,ac,a and Zind,ac,c and 
    finding rind,ac,a and rind,ac,c by backtracing the purely acyclic flows 
    associated to find and by considering the interactiong between Zind,c and Zind,ac.
    
       
    Parameters
    ---------- 
        1. Zind_ac matrix [nxn]
        2. find vector [nx1] (most probably redundant  since the topological ordering leaves the p sector as the last one)
        3. rind_ac vector [1xn]
        4. Zind_c matrix [nxn]

    Returns
    -------
        1. Zind_ac_a  [nxn]
        2. Zind_ac_c [nxn]
        3. rind_ac_a [1xn]
        4. rind_ac_c [1xn]

    Notes
    -----
    See documentation for calculations
    
    References
    ----------
    
    '''
    # Arrange the IOT structure in topological order
    # I do not need to rearrange the whole array, just to treat them in the
    # order    
    #[Zind_ac_ordered, find_ordered, rind_ac_ordered, topological_order] = \
    #    topological_ordering(Zind_ac.copy(), find.copy(), rind_ac.copy())
    # the topological order puts the secot p as the last sector
    #Zind_ac_Digraph = nx.DiGraph(Zind_ac)
    #topological_order = nx.topological_sort(Zind_ac_Digraph)
    
    topological_order = nx.topological_sort(nx.DiGraph(Zind_ac))
    # we need to start with the last sector because we backtrack so we invert the order:
    topological_order.reverse()
    
    # intialise arrays
    NBR_sectors=np.shape(Zind_ac)[0]
    Zind_ac_a = np.zeros((NBR_sectors,NBR_sectors))
    Zind_ac_c = np.zeros((NBR_sectors,NBR_sectors))
    rind_ac_a = np.zeros(NBR_sectors)
    rind_ac_c = np.zeros(NBR_sectors)
    
    # however, the first sector (the p sector) is a especial case, so it is 
    # treated separately. The first sector from topological_order it taken out
    # and stores as p_sector
    p_sector=topological_order[0]
    
    # check is the p_sector is the last one
    if p_sector != list(find.flatten()).index(1):
    sys.exit('Abnornal error: the Zind_c of a based structure is not correctly ordered in topological order : the p-sector found in the topological order does not correspond to the product-based one.')
    
    for sector_index in range(NBR_sectors):
        Zind_ac_a[sector_index][p_sector] = Zind_ac[sector_index][p_sector]
        # Zind_ac_c[sector_index][p_sector] = 0, a redundant operation given Zind_ac_c definition
        
    # backtrace the flows according to inverse topo order starting from 2nd sector
    for order_index in topological_order[1:]:
        prop_a = np.sum(Zind_ac_a[order_index]) / (np.sum(Zind_ac_c[order_index]+Zind_ac_a[order_index]+ Zind_c[order_index]))
        prop_c = np.sum(Zind_ac_c[order_index] + Zind_c[order_index]) / (np.sum(Zind_ac_c[order_index]+Zind_ac_a[order_index]+ Zind_c[order_index]))
        print('output proportion for sector {2} \n prop_a ={0} \n prop_c ={1}'.format(prop_a,prop_c,order_index))
        # find resources rind_ac_a and rind_ac_c
        rind_ac_a[order_index] = prop_a * rind_ac[order_index]
        rind_ac_c[order_index] = prop_c * rind_ac[order_index]
        
        # find column Zind_ac_a and Zind_ac_c
        for sector_index in range(NBR_sectors):
            Zind_ac_a[sector_index][order_index] = prop_a * Zind_ac[sector_index][order_index]
            Zind_ac_c[sector_index][order_index] = prop_c * Zind_ac[sector_index][order_index]
    
    
    
    return(Zind_ac_a, Zind_ac_c, rind_ac_a, rind_ac_c)
    