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
    [Zind_ac_ordered, find_ordered, rind_ac_ordered, topological_correspondence] = \
        topological_ordering(Zind_ac.copy(), find.copy(), rind_ac.copy())
    
    
    
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
        4. topological_correspondence: vector enabling to undo the ordering [1xn]

    Notes
    -----
    See documentation for calculations
    
    References
    ----------
    
    '''   
    
    
    
    return(Zind_ac_ordered, find_ordered, rind_ac_ordered, topological_correspondence)