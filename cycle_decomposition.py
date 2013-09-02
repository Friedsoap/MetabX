# -*- coding: utf-8 -*-
#!/usr/bin/python
# Filename: cycle_decomposition.py
#revision history
# v0.1
# v0.2
# v0.3 included a modified simple_cycles function into a generator function. 
    # The architechture of the program has been optimised (calculate twice the 
    # cycles instead of storing them to avoid RAM and ROM memory issues).
    # Waiting for networkx to include the generator function in cycles.py


'''
This module contains all sub-modules necessary to extract the cycles from the
inter-sectoral matrix.
'''

__version__='0.3'


import pdb#        pdb.set_trace() 
import numpy as np
import sys
import time
from itertools import islice
import pprint as pprint
import networkx as nx
import new_cycles as new_cycles # this is where the modified simple_cycles is
# it is called simple_cycles_generator
# keep new_cycles as long as networkx does not ship cycles.py with it.

T = np.transpose    #    np.transpose(A) --> T(A)
P=pprint.pprint


def cycle_decomposition(working_array, output_columns):
    '''This function decomposes the intersectoral matrix of an IOT into an array 
    of the same size containing all the cycles and an array of the same size 
    containing all acycling flows.
    
    The search of the cycles uses the Johnson (1986) algorithm.
    The decomposition of the arc weight amongst the different cycles stems from
    Ulanowicz (1987) idea, whose algorithm has been modified for performance.
    
    Parameters
    ---------- 
        1. the intersectoral matrix [nxn]
        2. the output columns (fd and any other, usually several wastes). Thus,
        its dimension is [nx(1+m)] where m is the number of wastes.

    Returns
    -------
        1. cycle_array: array containing all cycling flows [nxn]
        2. straight_array: array containing the acyclic flows [nxn]
        3. subtracted_self_loops: array containing all self-loops [nxn]

    Notes
    -----
    The original inter-sectoral matrix = cycle_array + straight_array
    
    References
    ----------
    
    '''
        
    #### initialise variables
    straight_array = working_array.__copy__()
    original_array = working_array.__copy__()
    cycle_array = np.zeros(np.shape(working_array))
    total_outputs = np.sum(working_array,axis=1) + np.sum(output_columns,
                                                            axis=1)

    print('\n+++ Starting cycle analysis +++\n The initial working_array is \n'+str(working_array))

    #### extract all self-loops from working_array ####
    # The algorithm below could also extract them but we need a separate array 
    # containing the self-loop for further analysis
    [working_array, straight_array,cycle_array, subtracted_self_loops] = \
        extract_self_loops(working_array.__copy__(), cycle_array.__copy__(),
                           straight_array.__copy__())
    print('\nThe new cycle_array is now \n' + str(cycle_array) +
    '\n and the new straight_array is\n' + str(straight_array) +
    '\n and the new working_array is\n'+str(working_array))

    # Find the weakest arc through which cycles pass 
    working_array_digraph=nx.DiGraph(working_array)   
    [smallest_arc_with_cycle, smallest_arc_with_cycle_value] = find_smallest_arc_with_cycle(working_array, working_array_digraph)
    print('The smallest_arc_with_cycle is {0} and its value is {1}'.format(smallest_arc_with_cycle,smallest_arc_with_cycle_value))
    
    # Start iterations to subtract the cycles passing through the weakest arc 
    # according to their weighted circuit probabilities (Ulanowicz, 1987) and 
    # finding again the weakest arc through which cycles pass
    iteration_counter=0
    
    while smallest_arc_with_cycle:
        print('\n +++ Starting iteration {0} +++'.format(iteration_counter) )
        cycle_flows_to_be_subtracted = np.zeros(np.shape((working_array)))
    
        # FIRST run of the generator to calculate each cycle probability
        # note: the cycle generator ONLY provides all cycles going through 
        # the specified weakest arc
        
        generator = simple_cycles_through_specific_arc(working_array_digraph, smallest_arc_with_cycle)
        nexus_total_probs = 0
        print('\n + FIRST run to find the total nexus probability (it can take a long while) +')
        for cycle in generator:
            cycle_prob = find_cycle_probability(cycle, original_array, total_outputs)
            nexus_total_probs += cycle_prob
            #print('For cycle {1}: the cycle_prob is {0} and the nexus_total_probs is {2}'.format(cycle_prob,cycle,nexus_total_probs)) # FOR DEBUG ONLY.   
        print('The nexus_total_probs is {0}'.format(nexus_total_probs) )
    
        # SECOND run of the generator
        # using the nexus_prob_sum calculated before, I can allocate the weight of the 
        # weakest arc to each cycle going through it
        generator = simple_cycles_through_specific_arc(working_array_digraph,smallest_arc_with_cycle)
        print('\n + SECOND run to extract the cycles of the nexus (it can take another long while)+')
        for cycle in generator:
            cycle_prob = find_cycle_probability(cycle, original_array, total_outputs)        
            allocated_cycle_weight = cycle_prob / nexus_total_probs * smallest_arc_with_cycle_value
            #print('The cycle_prob is {0} for cycle {1} and allocated_cycle_weight is {2}'.format(cycle_prob,cycle,allocated_cycle_weight)) # FOR DEBUG ONLY.   

            # create the array to be substracted
            for i in range(len(cycle)-1):
                cycle_flows_to_be_subtracted[cycle[i]][cycle[i+1]] += allocated_cycle_weight 
        
        print('The cycle_flows_to_be_subtracted is\n {0}'.format(cycle_flows_to_be_subtracted) )
        # extract the cycles
        working_array = working_array - cycle_flows_to_be_subtracted

        # clean negligible values
        clean_negligible_values(working_array)
        print('The working_array is\n {0}'.format(working_array) )

        # add cycles to cycle_array
        cycle_array = cycle_array + cycle_flows_to_be_subtracted
        print('The cycle_array is\n {0}'.format(cycle_array) )
        
        straight_array = straight_array - cycle_flows_to_be_subtracted
        clean_negligible_values(straight_array)
        print('The straight_array is\n {0}'.format(straight_array) )

        # find the next weakest arc with cycles
        working_array_digraph=nx.DiGraph(working_array)
        [smallest_arc_with_cycle, smallest_arc_with_cycle_value] = find_smallest_arc_with_cycle(working_array, working_array_digraph)
        print('The smallest_arc_with_cycle is {0} and its value is {1}'.format(smallest_arc_with_cycle,smallest_arc_with_cycle_value) )
    
        iteration_counter     +=1
        
    return(cycle_array, straight_array, subtracted_self_loops)


################## extract_self_loops START ##################################

def extract_self_loops(working_array, cycle_array, straight_array):
    '''This function extract all self-loops from working_array and returns a new working array without the self-loops. It also returns the corresponding cycling array and straight-flows array.
        
    Parameters
    ----------     
        1. working_array from which the self loops are to be extracted [nxn]
        2. cycle_array which to which the self-loops are copied to [nxn]
        3. straight_array [nxn] (i.e. the remainder which can contain other 
        cycles than self ones.
    
    Returns
    -------
        1. working_array: [nxn] array whose self-loops have been extracted
        2. straight_array: [nxn] array from which the self loops have been subtracted
        but might still contain other non self-cycles
        3. cycle_array: [nxn] array containing the extracted self loops (and
        other loops if present before)
        4. subtracted_self_loops: [nx1] array with self-loop only.
        
    Notes
    -----
    Only the diagonal elements are considered self-loops.        
    '''

    self_loops_present=False
    subtracted_self_loops=np.zeros((np.shape(working_array)[0],1))#make a column to put all self_loops   

    for i in range(np.shape(working_array)[0]):       
        if working_array[i][i]<0:
                 sys.exit('''This is WEIRD: the cell z{0}{0} of the intersectoral matrix is negative, exiting '''.format(i))
        elif working_array[i][i]>0:
            cycle_array[i][i]=working_array[i][i]
            straight_array[i][i]=straight_array[i][i]-cycle_array[i][i]
            subtracted_self_loops[i][0]=working_array[i][i]
            working_array[i][i]=0            
            self_loops_present=True

    if self_loops_present==True:
        print('\n+ Self-loops extracted, proceeding... ')
    else:
        print('\n No self-loops found, proceeding...')    

    return(working_array, straight_array, cycle_array, subtracted_self_loops)

################## extract_self_loops END ##################################
   
    
#code from http://stackoverflow.com/questions/11131185/is-there-a-python-builtin-for-determining-if-an-iterable-contained-a-certain-seq

## here the window is 2 because the arc is defined by 2 nodes
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



def simple_cycles_through_specific_arc(working_array_digraph, arc):
    '''Generator function generating all simple cycles of the given digraph
    containing a specific arc.
    
    Parameters
    ---------- 
        1. working_array_digraph: Digraph defined with networkx.Digraph 
        2. arc defined as a list [a,b] where a is the starting node and b the 
        ending node of the arc
        
    Returns (generates)
    -------------------
        each iteration of the function generates a cycle conforming to the 
        new_cycles.simple_cycles_generator generator function output.
        
    See also
    --------
        See the main generator function defined in new_cycles or maybe incorporated
        in the main networkx distribution
    
    '''
    generator=new_cycles.simple_cycles_generator(working_array_digraph)
    for cycle in generator:
        if contains_sequence(cycle, arc):             
            yield cycle
    return
    




def find_smallest_arc_with_cycle(working_array, working_array_digraph):
    '''Find the smallest arc through which at least one cycle flows.
    
    Parameters
    ---------- 
        1. working_array: [nxn] array where to look for the weakest arc where a
        cycle passes
        2. working_array_digraph: the working_array converted in digraph by 
        networkx.Digraph
        
    Returns
    -------
        - if such arc exists:
            smallest_arc_with_cycle = [a,b] where a is the start and b the end node
            smallest_arc_with_cycle_value = weight of the arc
        - if such arc does not exist:
            smallest_arc_with_cycle = []
            smallest_arc_with_cycle_value = 0 
    '''

    smallest_arc_with_cycle = []
    smallest_arc_with_cycle_value = 0
    sparse_array = []
    # Create a sparse array avoiding empty arcs
    for i in range(np.shape(working_array)[0]):
        for j in range(np.shape(working_array)[1]):
            if working_array[i][j] !=0:
                sparse_array.append([i,j,working_array[i][j]])
    # Sort the sparse array by the arc weight, smallest first
    sorted_array=sorted(sparse_array, key=lambda x: x[2])
    # Check whether there is a cycle flowing through the arc
    for i in range(len(sorted_array)):
        smallest_arc = [sorted_array[i][0], sorted_array[i][1]]
        generator = simple_cycles_through_specific_arc(working_array_digraph, smallest_arc)
        if any(generator):
            smallest_arc_with_cycle=smallest_arc
            smallest_arc_with_cycle_value=sorted_array[i][2]
            break
        
    return smallest_arc_with_cycle,smallest_arc_with_cycle_value
    

def find_cycle_probability(cycle, original_array, total_outputs):
    '''Finds the circuit probability of a given cycle within a given IOT.

    Parameters
    ---------- 
         1. cycle: list containing all nodes of a cycle, repeating the starting
         node at the end
         2. original_array: [nxn] array containing *all* original flows so that 
         the probabilities can be calculated
         3. total_outputs: [nx1] array containing total outputs of the IOT to 
         calculate the probability to go to a specific node over the total output.
         
    Returns
    -------
        circuit_probabilities_of_the_cycle: product of all output probabilities
        of getting to the next node of the cycle. PROD(weight_ij/total_output_i)
    
    Notes
    -----
    The circuit probability is defined by the product of the probabilities of
    a particle getting from one node to the next node of the cycle (Ulanowicz,
    1987)

    References
    ----------
    
    '''
    output_prob_of_each_arc=[]
    for i in range(len(cycle)-1):
        weight_of_the_arc = original_array[cycle[i]][cycle[i+1]]
        output_probability_of_the_arc = weight_of_the_arc / total_outputs[cycle[i]]
        output_prob_of_each_arc.append(output_probability_of_the_arc)
    circuit_probabilities_of_the_cycle = np.prod(output_prob_of_each_arc)
    
    return circuit_probabilities_of_the_cycle 
        
def clean_negligible_values(working_array):
    ''' Cleans the array by rounding negligible values to 0 according to a 
    pre-defined threeshold.
    
    Parameters
    ----------    
        1. working_array: [nxn] array to clean
        
    Returns
    -------
        Nothing directly but since it is the array that is passed, the modifications
        persist through the assignment.
    
    Notes
    -----
        The function contains the zero_threeshold internally
    
    '''
    # Specified threeshold
    zero_threeshold=0.000001
    
    for i in range(np.shape(working_array)[0]):
        for j in range(np.shape(working_array)[1]):
            if working_array[i][j] == 0: # important otherwise it will reduntdantly substitute zero values
                continue
            elif 0 < working_array[i][j] < zero_threeshold:
                print(' ... working_array (or straight_array) position [{0}][{1}] of value {2} is substituted by 0 because it is lower than specified threeshold {3} (to avoid endless iteration to subtract negligible flows)'.format(i,j,working_array[i][j],zero_threeshold))
                working_array[i][j] = 0
            elif -zero_threeshold <= working_array[i][j] < 0:
                working_array[i][j] = 0
                print(' ... working_array (or straight_array) position [{0}][{1}] of value {2} is substituted by 0 because although it is a negative value, it is so small (between -{3} and 0) that it is most probably a rounding issue.'.format(i,j,working_array[i][j],zero_threeshold))
            elif working_array[i][j] < -zero_threeshold:
                sys.exit('Error: the working_array (or straight_array) contains a negative value in position [{0}{1}], exiting. (It might be a simple rounding issue, in which case you need to change the zero_threeshold value accordingly)'.format(i,j))    

    return working_array