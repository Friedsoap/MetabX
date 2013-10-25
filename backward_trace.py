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

def main(Zind_ac, find, rind_ac):
    '''This function decomposes Zind,ac between Zind,ac,a and Zind,ac,c and 
    finding rind,ac,a and rind,ac,c by backtracing the purely acyclic flows 
    associated to find and by considering the interactiong between Zind,c and Zind,ac.
    
       
    Parameters
    ---------- 
        1. Zind_ac matrix [nxn]
        2. find vector [nx1]
        3. rind_ac vector [1xn]

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
    topological_order = nx.topological_sort(nx.Digraph(Zind_ac))
    # we need to start with the last sector so we invert the order:
    topological_order.reverse()
    
    # intialise arrays
    Zind_ac_a_tmp=np.zeros((NBR_sectors,NBR_sectors))
    Zind_ac_c_tmp=np.zeros((NBR_sectors,NBR_sectors))
    
    # however, the first sector (the p sector) is a especial case, so it is 
    # treated separately. tThe first sector from topological_order it taken out
    # and stores as p_sector
    p_sector=topological_order.pop(0)
    for sector_index in range(NBR_sectors):
        Zind_ac_a_tmp[sector_index][p_sector] = Zind_ac[sector_index][p_sector]
        # Zind_ac_c_tmp[sector_index][p_sector] = 0, a redundant operation given Zind_ac_c_tmp definition
        
    
    # backtrace the flows and allocate each to either Zind_ac_a or Zind_ac_c
    for order_index in topological_order:
        prop_c=
        prop_a=
        for sector_index in range(NBR_sectors):
            Zind_ac_a_tmp[sector_index][order_index] = prop_a * Zind_ac[sector_index][order_index]
            Zind_ac_c_tmp[sector_index][order_index] = prop_c * Zind_ac[sector_index][order_index]
    
    
    
    return(Zind_ac_a, Zind_ac_c, rind_ac_a, rind_ac_c)
    

def topological_ordering(Zind_ac, find, rind_ac):
     '''This function find the topological order of Zind,ac, and tranforms 
     Zind_ac, find, rind_ac accordingly, also providing an array undo the
     ordering.
    
       
    Parameters
    ---------- 
        1. Zind_ac matrix [nxn]
        2. find vector [nx1]
        3. rind_ac vector [1xn]

    Returns
    -------
        1. Zind_ac matrix in topological order [nxn]
        2. find vector in topological order  [nx1]
        3. rind_ac vector in topological order [1xn]
        4. topological_order: vector enabling to undo the ordering (n list)

    Notes
    -----
    See documentation for calculations
    
    References
    ----------
    
    '''   
    # find topological order
    topological_order = nx.topological_sort(nx.Digraph(Zind_ac))
    
    
    
    return(Zind_ac_ordered, find_ordered, rind_ac_ordered, topological_order)