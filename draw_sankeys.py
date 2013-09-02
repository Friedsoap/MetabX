# -*- coding: utf-8 -*-
#!/usr/bin/python
# Filename: draw_sankeys_v01.py
#revision history
#v0.1
#v0.2: improving sankey layout: this version leaves the diagrams in scale, i.e. the first in top left and the last at the bottom right. The self-loops are ok.


import pdb#        pdb.set_trace() 
import numpy as np
import matplotlib.pyplot as plt
import os

from matplotlib.sankey import Sankey

__version__= '0.2'
#flows:
    #positive = inputs
    #negative = outputs
# IMPORTANT NBR_sectors has nbr+1 sectors so that python makes the range properly! ,i.e. range(NBR_sectors) for iterations!

def sankey_of_cyclic_flows(units,title_imported,NBR_sectors,total_inputs,feeding_flows,straight_inputs,total_losses,cycling_losses,straight_losses,useful_outputs,cyclic_array,acyclic_array,self_loops_array,images_directory,file_name):
    fig = plt.figure(figsize=(8, 12))
    #the losses are inferior than the cycles
    max_cycle_flow=np.max(cyclic_array)
    ax = fig.add_subplot(1, 1, 1, xticks=[], yticks=[], title=str(title_imported))
#the scaling is missing because I do not know yet the biggest flow - probably just run a search of maximal value amongst all arrays I use
    sankey = Sankey(ax=ax, format='%.3G', unit=str(units), gap=0.5, scale=1.0/max_cycle_flow)
#create the list of flows for each node in the following order:
    #inputs(positive): feeding_flows, inter-sectoral cycles, self_loop is the last
    #outputs(negative):-self_loop, -cycling_losses,-inter-sectoral cycles
    sankey_flows=[]
    for each_sector in range(NBR_sectors):
        sankey_flows.append(feeding_flows[each_sector])
        for j in range(NBR_sectors):
            if j!=each_sector:           
                sankey_flows.append(cyclic_array[j][each_sector])
        sankey_flows.append(cyclic_array[each_sector][each_sector])        
        sankey_flows.append(-cycling_losses[each_sector])
        for j in range(NBR_sectors):
            if j!=each_sector:
                sankey_flows.append(-cyclic_array[each_sector][j])
        sankey_flows.append(-cyclic_array[each_sector][each_sector])
        
    sankey_labels=[]
    for each_sector in range(NBR_sectors):
         sankey_labels.append('Feeding_flow')
         for j in range(NBR_sectors):
            if j!=each_sector:           
                sankey_labels.append('input from '+str(j))
         sankey_labels.append('Self-loop')       
         sankey_labels.append('Cycling losses')
         for j in range(NBR_sectors):
             if j!=each_sector:           
                sankey_labels.append('output to '+str(j))
         sankey_labels.append('Self-loop')
#create the list of orientations for each flow:
#orientation:
#1 (from/to the top), 0 (from/to the left or right), or -1 (from/to the bottom). 
# If *orientations* == 0, inputs will break in from the left and outputs will break away to the right.
#inputs(positive): feeding_flows:0:horizontal, inter-sectoral cycles:relative, self_loop:1:down 
#outputs(negative):-self_loop:1:down, -cycling_losses:0:horizontal,-inter-sectoral cycles:relative,
    sankey_orientations=[]
    for each_sector in range(NBR_sectors):
         sankey_orientations.append(0)
         for j in range(NBR_sectors):
            if each_sector<j:# 
                sankey_orientations.append(-1)
            if each_sector>j:# 
                sankey_orientations.append(1)
         sankey_orientations.append(-1)
         sankey_orientations.append(0)
         for j in range(NBR_sectors):
             if each_sector<j:# 
                sankey_orientations.append(-1)
             if each_sector>j:# 
                sankey_orientations.append(1)
         sankey_orientations.append(-1)

    sankey_pathlengths=[]
    for each_sector in range(NBR_sectors):
         sankey_pathlengths.append(0.5)#for input
         for j in range(NBR_sectors):
            if each_sector!=j:# 
                sankey_pathlengths.append(2*np.abs(each_sector-j))            
         sankey_pathlengths.append(0.25)#for self-loop
         sankey_pathlengths.append(0.5)#for output
         for j in range(NBR_sectors):
            if each_sector!=j:# 
                sankey_pathlengths.append(2*np.abs(each_sector-j))
         sankey_pathlengths.append(0.25)#for self-loop



#self_loops flows for separate sankey                
    sankey_flows_self_loops=[]
    for each_sector in range(NBR_sectors):
        sankey_flows_self_loops.append(-cyclic_array[each_sector][each_sector])
        sankey_flows_self_loops.append(cyclic_array[each_sector][each_sector])

    sankey_labels_self_loops=[]
    for each_sector in range(NBR_sectors):
        sankey_labels_self_loops.append('Self-loop')
        sankey_labels_self_loops.append('Self-loop')

    sankey_orientations_self_loops=[]
    for each_sector in range(NBR_sectors):
        sankey_orientations_self_loops.append(-1)
        sankey_orientations_self_loops.append(-1)
    sankey_pathlengths_self_loops=[]
    for each_sector in range(NBR_sectors):
        sankey_pathlengths_self_loops.append(0.25)
        sankey_pathlengths_self_loops.append(0.25)
    
#creating the sankey parts representing each node.
#to create the order, the first one does not containt "prior", then the others do.
    for each_sector in range(NBR_sectors):        
        if each_sector==0:
            sankey.add(patchlabel='Sector'+str(each_sector), facecolor='#37c959',
                       flows = sankey_flows[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)],labels = sankey_labels[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], pathlengths = sankey_pathlengths[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], orientations = sankey_orientations[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)])#,prior=2,connect=(5,2) OR ,prior=2,connect=(1,6) OR ,prior=1,connect=(1,5)
        if each_sector==1:      
            sankey.add(patchlabel='Sector'+str(each_sector), facecolor='#37c959', flows = sankey_flows[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], labels =           sankey_labels[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], pathlengths = sankey_pathlengths[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], orientations = sankey_orientations[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)],prior=0,connect=(5,1))
        if each_sector==2:      
            sankey.add(patchlabel='Sector'+str(each_sector), facecolor='#37c959', flows = sankey_flows[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], labels =           sankey_labels[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], pathlengths = sankey_pathlengths[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], orientations = sankey_orientations[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], prior=1,connect=(6,2))
#make a 2 case with if to add the "prior" STOPPED
#        if each_sector>0:      
#             sankey.add(patchlabel='Sector'+str(each_sector), facecolor='#37c959', flows=sankey_flows[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)],            orientations=sankey_orientations[each_sector*(2+2*NBR_sectors):(each_sector+1)*(2+2*NBR_sectors)], prior=each_sector-1, connect=(each_sector,NBR_sectors-each_sector))

#add the self-loop parts
    for each_sector in range(NBR_sectors):      
        sankey.add(patchlabel='Self_loop '+str(each_sector), facecolor='#58b1fa', flows = sankey_flows_self_loops[each_sector*2:(each_sector+1)*2], labels = sankey_labels_self_loops[each_sector*2:(each_sector+1)*2], pathlengths = sankey_pathlengths_self_loops[each_sector*2:(each_sector+1)*2], orientations = sankey_orientations_self_loops[each_sector*2:(each_sector+1)*2], prior = each_sector,connect=(NBR_sectors,0))#,prior=each_sector,connect=(NBR_sectors+1,0)

#add the extra branches to cross connect the sectors



#put the sankey together
    diagrams = sankey.finish()

    #format it
    for diagram in diagrams:
        diagram.text.set_fontweight('bold')
        diagram.text.set_fontsize('10')
        for text in diagram.texts:
            text.set_fontsize('10')
    #pdb.set_trace() #was useful to stop the debug before showin the diagram.
    #plt.show() #use to show the diagram and stop the program.
    
# I HAVE DISABLED SAVING THE SANKEYs BECAUSE I DO NOT NEED IT NOW.
    
    #plt.savefig(images_directory+'/'+file_name+'.png',dpi=300)#If *format* is *None* and *fname* is a string, the output format is deduced from the extension of the filename.
    
    #THEN I CAN CALL THE image from the main program and insert it in the xls

#def sankey_of_straight_flows():
#    return()