# -*- coding: utf-8 -*-
#!/usr/bin/python
# Filename: circos_interface.py
#revision history
# v0.1: implemented diagram_type: merged or symmetrical, scale_type: normalised or non_normalised, flow_type: sector_outputs, sector_inputs, cyclic_acyclic; ribbon_order: size_asc, size_desc or native (as in circos but does not work very well);
# v0.1_TODO: improve native ribbon_order

# v0.2: improved merged layout (with double sector space)
# v0.2_TODO: improve native ribbon_order


"""
Created on Sun May 26 09:21:22 2013

@author: aleix
"""

__version__='0.2'

import numpy as np
import sys
#from numpy import linalg as LA
import pprint as pprint
import os as os
import time
import operator #to sort stuff
#import collections

#==============================================================================
import pdb
# pdb.set_trace()
#==============================================================================

#XXX: important check before drawing merged circos diagrams: the intersectoral outputs + intersectoral inputs need to be inferior than the total output or total input. If superior (as the case of the manuf and services sector in the agricultural prod struct), i should issue a warning. That is why the symmertrical graph is actually better: it can ALWAYS accommodate for any representation, the merged cannot ALWAYS.


# The idea of this first interface are:
# 1 -parse the IO table information to be able to represent the draw the links 
# 2 write the config files
# 3 execute circos automatically

def draw_circos_diagram(circos_execute, circos_open_images, unit, diagram_type, scale_type, flow_type, ribbon_order, directory, data_filename, nbr_sectors, nbr_emissions, sector_names, *arrays):
    '''This is the main function which takes the options for drawing the diagram, it will call sub-functions accordingly.
    
    Parameters
    ----------
    1. circos_execute (boolean) from config file: executes circos if true
    2. circos_open_images (boolean) from config file: opens the graphs that have been produced if true
    - diagram_type: merged or symmetrical
    - scale_type: normalised or non_normalised
    - flow_type: sector_outputs, sector_inputs, cyclic_acyclic
    - ribbon_order: size_asc, size_desc or native (same as in circos)

    - directory: path where the config, data and image files are put, creates etc, data and img subfolders
    the data passed to draw the diagram is
    - nbr_sectors [integer]
    - nbr_emissions [integer]
    - sector_names [array containing sector names in the same order as in the other arrays]
    - *arrays: is a list called arrays containing different array which should always be passed in blocks of 4 with strict order: intersectoral_matrix [nbr_sectors x nbr_sectors],  primary_inputs[1 x nbr_sectors], final_goods [nbr_sectors x 1], emission_matrix [nbr_sectors x nbr_emissions]. By doing that this subroutine is flexible to calculate any kind of flow-type decomposition.
    '''  

    ### function checks
    # check whether the amount of sectors/ emissions exceeds the default colour capacities
    if nbr_sectors > 12:
         sys.exit('''Error: there are {0} sectors but there are only 12 predefined colors for sectors. You will need to comment out this error and modify the attribute_colors.conf file'''.format(nbr_sectors))
    if nbr_emissions > 6:
         sys.exit('''Error: there are {0} emission types but there are only 5 predefined colors for emissions. You will need to comment out this error and modify the attribute_colors.conf file'''.format(nbr_emissions))

    # check whether the options passed are not mispelled
    if diagram_type != 'merged' and diagram_type !='symmetrical':
         sys.exit('''Error: the diagram_type argument is not merged nor symmetrical''')
    if scale_type != 'normalised' and  scale_type !='non_normalised':
         sys.exit('''Error: the scale_type argument is not normalised nor non_normalised''')
    if flow_type != 'sector_outputs' and flow_type !='sector_inputs' and flow_type !='cyclic_acyclic':
         sys.exit('''Error: the flow_type argument is not sector_outputs nor sector_inputs nor cyclic_acyclic ''')
    if ribbon_order != 'size_asc' and ribbon_order != 'size_desc' and ribbon_order != 'native':
         sys.exit('''Error: the ribbon_order argument is not size_asc nor size_desc nor native.''')

    # check consistency in the number of arrays passed
    nbr_arrays=len(arrays)# number of arrays passed to the function
    if nbr_arrays != 4 and (flow_type == 'sector_outputs' or flow_type =='sector_inputs'):
         sys.exit('''Error: You want a sector_outputs or sector_inputs diagram but the number of arrays passed to the draw_circos_diagram function is {0}, please check it out, it should be four.'''.format(nbr_arrays))
    if nbr_arrays != 8 and flow_type == 'cyclic_acyclic':
         sys.exit('''Error: You want a sector_outputs or cyclic_acyclic diagram but the number of arrays passed to the draw_circos_diagram function is {0}, please check it out, it should be eight. '''.format(nbr_arrays))    
    # the next is a redundant check of the structure at this point, but the idea is to enable drawing k components at the same time in future versions
    nbr_flow_structures = nbr_arrays/4
    if not isinstance( nbr_flow_structures, int ):
         sys.exit('''Error: A structure is defined by 4 arrays, but you passed {0} arrays, which is not a multiple of 4... something is wrong. (The typical decompositions are either a full structure diagram (the 4 IOT components) or the disaggregated cyclic_acyclic which contains 4 structures and thus 16 arrays'''.format(nbr_arrays))

    # check array dimensions
    for i in range(nbr_flow_structures):
        if np.shape(arrays[4*i]) != (nbr_sectors, nbr_sectors):
            sys.exit('''Error: The {0}th intersectoral matrix you passed to the circos interface (i.e. the {1}th array) does not seem to be of the required dimension   [{2}x{2}]'''.format(i+1,4*i+1,nbr_sectors))
        if np.shape(arrays[4*i+1]) != (1, nbr_sectors):
            sys.exit('''Error: The {0}th primary inputs array you passed to the circos interface (i.e. the {1}th array) does not seem to be of the required dimension is  [1x{2}]'''.format(i+1, 4*i+1+1, nbr_sectors))
        if np.shape(arrays[4*i+2]) != (nbr_sectors, 1):
            sys.exit('''Error: The {0}th final demand array you passed to the circos interface (i.e. the {1}th array) does not seem to be of the required dimension   [{2}x1]'''.format(i+1,4*i+2+1,nbr_sectors))
        if np.shape(arrays[4*i+3]) != (nbr_sectors, nbr_emissions):
            sys.exit('''Error: The {0}th emissions array you passed to the circos interface (i.e. the {1}th array)  does not seem to be of the required dimension  [{2}x{3}]'''.format(i+1, 4*i+3+1, nbr_sectors, nbr_emissions))


    # create folder structure required by circos
    # create a circos directory for the specific graph inside the "directory" directory containing the required subfolders (etc, data and img)
    specific_circos_dir=diagram_type+'_'+scale_type+'_'+flow_type+'_'+ribbon_order
    os.chdir(directory)
    working_dir=os.path.join(directory,specific_circos_dir)
    if specific_circos_dir not in os.listdir('./'):         
        os.mkdir(working_dir)
        os.chdir(working_dir)
        os.mkdir('etc')
        os.mkdir('data')
        os.mkdir('img')
        
    # apply the unit change   
    arrays = list(arrays)       
    if unit !=1:
        for i in range(len(arrays)):
            arrays[i] = arrays[i] * unit
            
    ### Write the config and data files in the corresponding subfolders
    print('\n+++ Writing Circos config and data files in {0}+++'.format(os.path.join(directory,specific_circos_dir)))
    create_attribute_colors_conf(nbr_emissions, sector_names, working_dir)
    create_kariotype_txt(diagram_type, flow_type, working_dir, nbr_sectors, nbr_emissions, sector_names, arrays)
    create_ticks_conf(working_dir)
    (histogram_end) = create_histograms_conf(diagram_type, flow_type, working_dir, nbr_sectors, nbr_emissions, sector_names, arrays)
    # correction of the histogram end to draw the sectoral labels    
    if diagram_type == 'merged':
        histogram_end=histogram_end+'+50p'
    create_ideogram_conf(working_dir, histogram_end)
    create_links_conf(working_dir)
    parent_name=os.path.split(directory)[1]
    create_image_conf(parent_name, specific_circos_dir, working_dir)
    create_normalisation_conf(diagram_type, scale_type, working_dir, nbr_sectors, sector_names, arrays)
    create_circos_conf(unit, working_dir)
    create_links_data_txt(diagram_type, flow_type, ribbon_order, working_dir, data_filename, nbr_sectors, nbr_emissions, sector_names, arrays)
        
    if circos_execute:
        print('\n+++ Executing Circos in folder {0}+++'.format(os.path.join(directory,specific_circos_dir)))
        execute_circos(parent_name, specific_circos_dir, working_dir, circos_open_images)
    else: # write error to log but do not stop program
        print('''\n+++++++++++++++++++++++++++++++++++
+++++++++++ ERROR: The Circos graph with 'merged' option cannot be drawn because the sum of intersectoral inputs plus interesectoral outputs exceeds the total outputs. In other words, the intersectoral links exceed the space available for drawing. Thus, this IOT can only be drawn in 'symmetrical mode'. The program did not quit because there is nothing you can do about it.
The graph was to be drawn in {0} but the program continues...
+++++++++++++++++++++++++++++++++++'''.format(working_dir))
    return()

###################### /etc/attribute_colors.conf START ######################## 

#XXX: TODO: automatise the color generation so that 
# the col_sectorNAme is correct
# the col_emission_NBR_EMISSIONS is correct
    
def create_attribute_colors_conf(nbr_emissions,sector_names,working_dir):
    '''Creates the attribute_colors.conf file in etc directory.
    
    I use the predefined brewer color palettes as recommended by Circos (see circos docs and http://colorbrewer2.org/)
    The problem is that there is a maximum of 12 colors for a qualitative palette and 9 for a sequential palettes.
    This poses restrictions on the colors that can be atributed automatically following the color palettes.
    See the conf file comments for more details.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    attribute_colors_conf_file = open('attribute_colors.conf', 'w')  
    # the content of the file should start at the beginning of the line, i.e. not respecting the indentation, otherwise that indentation is used in the file.

    attribute_colors_conf_file_content='''\
# this is the file defining my custom colors so they are attributed to links, sectors, etc.	
# This file does not need the typical section start/end  <colors> and </colors> because it is called by circos.conf which has them.	
# careful, the color definition cannot contain the transparency layer e.g. _a1 appended at the end, you need to append it when you call the color	
# careful Circos colors should be lowercase.	
	
####### COLORS DEFINED FOR FLOW-BY-SECTOR SCHEMES ################	
# limitations of the color schemes:	
# for intersectoral flows: only 12 allowed in set3-12-qual (maximum of the colorbrewer palette anyway)	
# for external emissions: I started the green, blue and red sequential coloring at 8 (the 9 was too dark). So it admits 7 more emissions, fd or resource types. 	
#The set3-12-qual is in pastel tone, which is different from the tone of the rdylgn-11-div	
# it is a pain in the sense that some sectors will have colors close to the external flows but I cannot do anything about that if I want to automate the color assigment to each sector
'''
    attribute_colors_conf_file.write(attribute_colors_conf_file_content)
    
    for i in range(len(sector_names)):
        attribute_colors_conf_file_content='''\ncol_{0} = set3-12-qual-{1}'''.format(sector_names[i].lower(),12-i)
        attribute_colors_conf_file.write(attribute_colors_conf_file_content)
    
    if len(sector_names)>12:
        sys.exit('''Error: the circos interface could not generate the attribute_colors.conf because there are {0} sector and it is currently using the set3-12-qual color brewer palette which only supports 12 different colors, exiting. You need to comment out the generation of the attribute_colors.conf file (i.e. the line with "create_attribute_colors_conf" and create it manually in the etc folder'''.format(len(sector_names)))

    attribute_colors_conf_file_content='''\n
# the resources, fd and emissions colors use the sequential color schemes	
# the resources are greens-9-seq starting at 8 (9 is too dark), anyway only one will be implemented	
# the final goods are blues-9-seq  starting at 8 (9 is too dark), anyway only one will be implemented	
	
col_resources = greens-9-seq-8	
col_final_goods = blues-9-seq-8

# The emissions are reds-9-seq-8  starting at 8 (9 is too dark), probably more will be used.
'''
    attribute_colors_conf_file.write(attribute_colors_conf_file_content)
    
    for i in range(nbr_emissions):
        attribute_colors_conf_file_content='''\ncol_emission_{0} = reds-9-seq-{1}'''.format(i,8-i)
        attribute_colors_conf_file.write(attribute_colors_conf_file_content)
    
    if nbr_emissions > 8:
        sys.exit('''Error: the circos interface could not generate the attribute_colors.conf because there are {0} emission types and it is currently using the reds-9-seq color brewer palette from 8 to 1 which only supports 8 different colors, exiting. You need to comment out the generation of the attribute_colors.conf file (i.e. the line with "create_attribute_colors_conf" and create it manually in the etc folder'''.format(len(sector_names)))

    attribute_colors_conf_file_content='''\n	
###### COLORS DEFINED FOR FLOW-BY-TYPE SCHEMES ##############		
# flow types: self-cycling, inter-cycling, indirect acyclic and direct acyclic:	
# To mark the separation between cyclic and acyclic flows (each having 2 components), I chose a 4-div color scheme	
# However the div schemes either start with red or end in green, so I mix the brown side of brbg-4 and the purple side of puor-4	
#the cyclic flows being the	
#col_sc=	brbg-4-div-1
#col_ic=	brbg-4-div-2
#col_ia=	puor-4-div-3
#col_da=	puor-4-div-4

col_flowtype_0=	brbg-4-div-1
col_flowtype_1=	brbg-4-div-2
col_flowtype_2=	brbg-4-div-3
col_flowtype_3=	brbg-4-div-4'''

    attribute_colors_conf_file.write(attribute_colors_conf_file_content)
    attribute_colors_conf_file.close()
    return()
    
###################### /etc/attribute_colors.conf END ######################## 



###################### /data/kariotype.txt START ######################## 

def create_kariotype_txt(diagram_type, flow_type, working_dir, nbr_sectors, nbr_emissions, sector_names, arrays):
    '''Creates the kariotype.txt file in data directory.
    
    if flow_type=sector_outputs or sector_inputs, only chromosomes are defined 
    if diagram_type=cylic-acyclic, chromosomes and cytogenetic bands are defined
    '''
    os.chdir(working_dir)
    os.chdir('data')
    kariotype_txt_file = open('kariotype.txt', 'w')
    #creating the intial config comments
    # the content of the file should start at the beginning of the line, i.e. not respecting the indentation, otherwise that indentation is used in the file.
    kariotype_txt_file_content='''\
####### SECTOR DEFINITION ####################
# this file defines the sizes and colors if the sectors. It is called karyotype because circos originally draws genes. 	
#careful, no decimals allowed in start end positioning	
# the format of the sectors is as follows	
#chr - CHRNAME CHRLABEL START END COLOR 	
# “chr -”	 is mandatory
# CHRNAME	  for internal use when called in other conf files (I could crop the sector to 4 characters – CAREFUL, IT MUST BE UNIQUE)
# CHRLABEL	 is the label printed in output picture
# START	 0
# END	      The amount of total output
# COLOR	I have predefined the colors in the attribute_colors.conf file
    '''
    kariotype_txt_file.write(kariotype_txt_file_content)

#calculating total outputs
    sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
    sum_resource_vectors=np.zeros((1,nbr_sectors))
    sum_fd_vectors=np.zeros((nbr_sectors,1))
    sum_emission_array=np.zeros((nbr_sectors,nbr_emissions))
    
    for i in range(len(arrays)/4):
        sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
        sum_resource_vectors=arrays[4*i+1] + sum_resource_vectors
        sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
        sum_emission_array=arrays[4*i+3] + sum_emission_array
    total_inputs= np.sum(sum_intersectoral_matrices,axis=0) + sum_resource_vectors

#create the chr- lines for merged and symmetrical cases
        
    # in merged case, the sectors are listed as they appear
    if diagram_type == 'merged':
        for i in range(len(sector_names)):
            
            #trick to round: "%.Xf" % round(total_inputs[i],X). The first part tells python just show the number up to the X decimal and the second part does the actual rounding. It is weird but it is the best I could find. Also note that the first filter returns a string so no need to transform it into string.
            kariotype_txt_file.write('\nchr - '+sector_names[i]+' '+sector_names[i]+' 0 '+ "%.0f" % round(2*total_inputs[0][i],0) + ' col_' + sector_names[i].lower())
        
        # only write teh cytongenetic bands for the cycle_acyclic
        if flow_type == 'cyclic_acyclic':
            kariotype_txt_file_content='''\n \n       
####### FLOW TYPE BANDS ####################
# this section defines the proportions and colors of the flow types contained in each sectorsectors. In circos they are originally called cytogenetic bands.
#careful, no decimals allowed in start end positioning	
# the format of the sectors is as follows	
#band	sector	bandX	bandX	start 	end	color	#type
# “band”	 is mandatory
# sector    must be associated to CHRNAME, i.e the name of the sector
# bandX     id of the band, must be there but not used anymore
# START	 start of the band section
# END	      end of the band section
# COLOR	I have predefined the colors in the attribute_colors.conf file. I have only managed to apply color names as col_flowtype_X where X is a number. The flowtype to which it refers depends on the ordering of the arrays passed to the main circos function. So, col_flowtype_0 will be the color to the first flow type.
    '''
            kariotype_txt_file.write(kariotype_txt_file_content)
            band_counter=0
            band_start=np.zeros((1,nbr_sectors))
            band_end=np.zeros((1,nbr_sectors))
            for i in range(len(arrays)/4):
                intersectoral_matrix=arrays[4*i]
                resource_vector=arrays[4*i+1]
                fd_column=arrays[4*i+2]
                emissions_columns=arrays[4*i+3]
                total_inputs= np.sum(intersectoral_matrix,axis=0) + resource_vector.flatten()
                total_outputs = np.sum(intersectoral_matrix,axis=1) + fd_column.flatten() + np.sum(emissions_columns,axis=1)
                band_end = total_inputs + total_outputs + band_end
                #pdb.set_trace()
                for j in range(len(sector_names)):
                    #pdb.set_trace()
                    if eval("%.0f" % round(band_start[0][j])) < eval("%.0f" % round(band_end[0][j])):
                        kariotype_txt_file.write('\nband '+ sector_names[j] + ' band' + str(band_counter) + ' band' + str(band_counter) + ' ' + "%.0f" % round(band_start[0][j]) + ' ' + "%.0f" % round(band_end[0][j]) +' col_flowtype_' + str(i))
                        band_counter=band_counter+1
                    elif eval("%.0f" % round(band_start[0][j])) == eval("%.0f" % round(band_end[0][j])):
                        print('\n+++ WARNING: SOME BANDS FROM THE KARYOTYPE WERE OMITTED BECAUSE THE START WAS EQUAL TO THE END AND CIRCOS DO NOT SUPPORT THAT. IT SHOULD NOT BE AN ISSUE. +++')        
                    else:
                        sys.exit('\n+++ ERROR: SOME BANDS FROM THE KARYOTYPE WERE OMITTED BECAUSE THE START WAS inferior TO THE END and this is wrong. Check the karyoptype bands to determine which arrays has the error. The error war found in the flowtype structure {0} for sector number {1} +++'.format(i,j)) 
                    #pdb.set_trace()
                band_start=band_end
            #if flowtypes = cyclic_acyclic , add cytogenetic bands according to the sector names and different structures
    # in symmetrical case, the sectors are appended with _out as they appear, then reversed and appended with _in (e.g. sector1_out, sector2_out,sector2_in and sector1_in)
    elif diagram_type == 'symmetrical':
      
         for i in range(len(sector_names)):
            kariotype_txt_file.write('\nchr - '+sector_names[i]+'_out '+sector_names[i]+'_out 0 '+ "%.0f" % round(total_inputs[0][i],0) + ' col_' + sector_names[i].lower())
         for i in range(len(sector_names)-1,-1,-1):
            kariotype_txt_file.write('\nchr - '+sector_names[i]+'_in '+sector_names[i]+'_in 0 '+ "%.0f" % round(total_inputs[0][i],0) + ' col_' + sector_names[i].lower())

         if flow_type == 'cyclic_acyclic':
            kariotype_txt_file_content='''\n \n       
####### FLOW TYPE BANDS ####################
# this section defines the proportions and colors of the flow types contained in each sectorsectors. In circos they are originally called cytogenetic bands.
#careful, no decimals allowed in start end positioning	
# the format of the sectors is as follows	
#band	sector	bandX	bandX	start 	end	color	#type
# “band”	 is mandatory
# sector    must be associated to CHRNAME, i.e the name of the sector
# bandX     id of the band, must be there but not used anymore
# START	 start of the band section
# END	      end of the band section
# COLOR	I have predefined the colors in the attribute_colors.conf file. I have only managed to apply color names as col_flowtype_X where X is a number. The flowtype to which it refers depends on the ordering of the arrays passed to the main circos function. So, col_flowtype_0 will be the color to the first flow type.
    '''
            kariotype_txt_file.write(kariotype_txt_file_content)
            band_counter=0
            band_start=np.zeros((1,nbr_sectors))
            band_end=np.zeros((1,nbr_sectors))
            for i in range(len(arrays)/4):
                intersectoral_matrix=arrays[4*i]
                resource_vector=arrays[4*i+1]
                total_inputs= np.sum(intersectoral_matrix,axis=0) + resource_vector
                band_end=total_inputs+band_end
                for j in range(len(sector_names)):
                    # band_start needs to be inferior than band_end. Sometimes they can be equal, which need to be removed, otherwise circos complains
                    if eval("%.0f" % round(band_start[0][j])) < eval("%.0f" % round(band_end[0][j])):
                        kariotype_txt_file.write('\nband '+ sector_names[j] + '_out band' + str(band_counter) + ' band' + str(band_counter) + ' ' + "%.0f" % round(band_start[0][j]) + ' ' + "%.0f" % round(band_end[0][j]) +' col_flowtype_' + str(i))
                        band_counter=band_counter+1
                        kariotype_txt_file.write('\nband '+ sector_names[j] + '_in band' + str(band_counter) + ' band' + str(band_counter) + ' ' + "%.0f" % round(band_start[0][j]) + ' ' + "%.0f" % round(band_end[0][j]) +' col_flowtype_' + str(i))
                        band_counter=band_counter+1
                    elif eval("%.0f" % round(band_start[0][j])) == eval("%.0f" % round(band_end[0][j])):
                        print('\n+++ WARNING: SOME BANDS FROM THE KARYOTYPE WERE OMITTED BECAUSE THE START WAS EQUAL TO THE END AND CIRCOS DO NOT SUPPORT THAT. IT SHOULD NOT BE AN ISSUE. +++')        
                    else:
                        sys.exit('\n+++ ERROR: SOME BANDS FROM THE KARYOTYPE WERE OMITTED BECAUSE THE START WAS inferior TO THE END and this is wrong. Check the karyoptype bands to determine which arrays has the error. The error war found in the flowtype structure {0} for sector number {1} +++'.format(i,j))     
                    #pdb.set_trace()
                band_start=band_end
    kariotype_txt_file.close()
    return()

###################### /data/kariotype.txt END ######################## 

###################### /etc/ideogram.conf START ######################## 
    
   
def create_ideogram_conf(working_dir,histogram_end):
    '''Creates the ideogram.conf file in etc directory.
    
    See the conf file comments for more details.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    ideogram_conf_file = open('ideogram.conf', 'w')
    ideogram_conf_file_content='''\
# This file defines how and where the sectors (chromosomes) are shown
# Also defines their labels format  and position
# note: I merged separate ideogram.conf files

<ideogram>

####### Ideogram section ########
<spacing>
default = 0.01r
</spacing>

# thickness and color of ideograms
thickness        = 25p
stroke_thickness = 2p
stroke_color     = vdgrey

# the default sector (chromosome) color is set here BUT any value
# defined in the karyotype file overrides it 
fill             = yes
fill_color       = black

# fractional radius position of chromosome ideogram within image
radius         = 0.65r

####### Ideogram labels section ########
show_label     = yes
label_font     = default
label_radius   = {0}+ 0.02r # I took out the relative position dims(ideogram,radius_outer) and put the same radius where the histogram ends + 0.02r
label_size     = 36
label_parallel = yes
label_case     = upper

####### cytogenetic bands section ########
show_bands            = yes
band_stroke_thickness = 1
fill_bands            = yes
band_transparency     = 1


</ideogram>
'''.format(histogram_end)
    ideogram_conf_file.write(ideogram_conf_file_content)
    ideogram_conf_file.close()
    return()
    
###################### /etc/ideogram.conf END ######################## 
    
###################### /etc/ticks.conf START ######################## 
    
#XXX:TODO: pass the most external radius of the data track so it draws the labels from there.     
    
def create_ticks_conf(working_dir):
    '''Creates the ticks.conf file in etc directory.
    
    See the conf file comments for more details.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    ticks_conf_file = open('ticks.conf', 'w')
    ticks_conf_file_content='''\
# This files defines the ticks, i.e. the marks and labels of any scale present in diagram 
# however, more axis can be defined within other datatracks if wanted.
# original file from circos lesson 2/12/etc/ticks.conf
# Here I left some unused code about grids in case it might be useful.
# The labels are size 18p, which is about OK for an A4 print 
# The labels are partly positioned with absolute values (i.e. 1r+Xp)
#  so if you reposition the ideogram, it will mess up how ticks and labels fit together.

show_ticks        = yes
show_tick_labels  = yes
show_grid         = yes 

<ticks>
# The following are general setting applied to all ticks
# but can be overriden by writing the same options within a tick block
label_font      = default
radius          = dims(ideogram,radius_outer) + 72p
label_offset    = 5p
label_size      = 18p
multiplier      = 1
color           = black
format          = %d
grid_thickness  = 1p

<tick>
# absolute tick, every 100 Mb, with label
spacing        = 100u
size           = 12p
thickness      = 2p
show_label     = yes

# here the grid looks pretty bad because it mixes the relative and absolute values.
#grid_start     = 1r
#grid_end       = 1r+45p
#grid_color     = vdgrey
#grid           = yes
</tick>

<tick>
#absolute tick, every 50 Mb, with grid
spacing        = 50u
size           = 7p
thickness      = 2p
show_label     = no

# here the grid looks pretty bad because it mixes the relative and absolute values.
#grid_start     = 1r
#grid_end       = 1r+45p
#grid_color     = grey
#grid           = yes
</tick>

<tick>
# absolute tick, every 10 Mb
spacing        = 10u
size           = 3p
thickness      = 2p
show_label     = no
</tick>

<tick>
# relative tick in inner radius, every 10% with label
radius         = 1r
spacing_type   = relative
rspacing       = 0.10
size           = 7p
thickness      = 2p
show_label     = yes
label_relative = yes
rmultiplier    = 100
suffix         = %

# here looks bad as it would mix with absolute values
#grid_start     = 0.5r
#grid_end       = 0.75r
#grid_color     = grey
#grid           = yes
</tick>

<tick>
#relative tick in inner radius, every 2%
radius         = 1r
spacing_type   = relative
rspacing       = 0.02
size           = 4p
thickness      = 2p
show_label     = no
</tick>

</ticks>

'''
    ticks_conf_file.write(ticks_conf_file_content)
    ticks_conf_file.close()
    return()
    
###################### /etc/ticks.conf END ######################## 

###################### /etc/histograms.conf START ######################## 

def create_histograms_conf(diagram_type, flow_type, working_dir, nbr_sectors, nbr_emissions, sector_names, arrays):
    '''Creates the histograms.conf file in etc directory AND the corresponding data files in data directory, one for each external flow type (resources, final goods plus one per emission type).
    
    The histograms drawn are different depending on the diagram type, as follows    
    if diagram_type= merged, normal or stacked histograms are drawn with axis
        if flow_type=sector_outputs or sector_inputs (i.e. flow-by-sector), one color per type of input/output is used as normal histogram
        if diagram_type=cylic-acyclic (i.e. flow-by-type), input and outputs are subdivided according to the type of flow as stacked histogram
    if diagram_type= symmetrical, circular barplot histograms are drawn with axis
        if flow_type=sector_outputs or sector_inputs (i.e. flow-by-sector) or cylic-acyclic (i.e. flow-by-type), circular barplot histograms are used. The former only with one color and the latter each barplot subdivided according to the contained flowtypes.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    nbr_arrays = len(arrays)

##### CREATING THE CONFIG FILES #######
    histograms_conf_file = open('histograms.conf', 'w')
    #creating the intial config comments
    # the content of the file should start at the beginning of the line, i.e. not respecting the indentation, otherwise that indentation is used in the file.
    histograms_conf_file_content='''\
# this file defines the histograms about system inputs and outputs
# In case it is a 'merged', 'flow-by-sector' diagram, it will be a normal histogram, with labels for resources, fd and emissions
# So I need to create the histogram_labels.txt, histogram_data_resources.txt,  histogram_data_final_goods.txt and histogram_data_emission_X.txt (As many as nbr_emissions)
# In case it is a 'merged', 'flow-by-type' diagram, it will be a stacked histogram, with labels for resources, fd and emissions
# So I need to create the histogram_labels.txt, histogram_data_resources.txt,  histogram_data_final_goods.txt and histogram_data_emission_X.txt (As many as nbr_emissions)
# In case it is a 'symmetrical' representation, it will be a circular stacked bar plot, without labels for resources fd and emissions, 
# So I need to create the histogram_stacked_bar_plot_color_rules.conf, histogram_data_resources.txt,  histogram_data_final_goods.txt and histogram_data_emission_X.txt (As many as nbr_emissions)\n'''
    histograms_conf_file.write(histograms_conf_file_content)

    barplot_content=['resources','final_goods']        
    for i in range(nbr_emissions):
        barplot_content.append('emission_'+str(i))    

    if diagram_type == 'symmetrical' or diagram_type == 'merged':
        #there will be a minimum of 3 cicular bar plots and maximum depends on the number of emissions. So Nbr_barplots = 2 + nbr_emissions
        # The histogram starts at 1r+150p due to the ticks
        # each barplot has a thickness of 50p
        barplot_start_list=range(150,150+50*(2+nbr_emissions),50)
        barplot_end_list=range(200,200+50*(2+nbr_emissions),50)
        #the histogram_end is passed to ideogram to draw the sectoral labels further out than the histogram
        histogram_end='1r+'+str(200+50*(2+nbr_emissions))+'p'
    
        histograms_conf_file_content='''
<plots>
# the highlight type is to make a  circular Stacked Bar Plots 
# highlight type requires rules to color the barplot section
type        = highlight
stroke_thickness = 0p
stroke_color = black\n'''
        histograms_conf_file.write(histograms_conf_file_content)
       
        for i in range(2+nbr_emissions):
            histograms_conf_file_content = '''
<plot>
#Circular Stacked Bar Plots for {0}
r0          = 1r+{1}p
r1          = 1r+{2}p
file        = ../data/histogram_data_{0}.txt
<<include histogram_stacked_bar_plot_color_rules.conf>>
<axes>
<axis>
color     = black_a1
spacing   = 1r
thickness = 1p
</axis>
</axes>
</plot>\n'''.format(barplot_content[i],str(barplot_start_list[i]),str(barplot_end_list[i]))
            histograms_conf_file.write(histograms_conf_file_content)              

        histograms_conf_file_content='''
</plots>
'''
        histograms_conf_file.write(histograms_conf_file_content)

        histograms_conf_file.close()
    
    # creating the additional rules in a separate file
    # The colors depend whether it is a flow-by-type or flow-by-sector diagram
        histogram_stacked_bar_plot_color_rules_conf_file = open('histogram_stacked_bar_plot_color_rules.conf', 'w')

        histogram_stacked_bar_plot_color_rules_conf_content='''\
# This file defines the color rules for the circular barplot histogram
# recall that flowtype colors are defined as col_flowtype_X
# recall that sector colors are defined as col_resources, etc

<rules>\n'''
        histogram_stacked_bar_plot_color_rules_conf_file.write(histogram_stacked_bar_plot_color_rules_conf_content)
        if flow_type == 'cyclic_acyclic':
            for i in range(nbr_arrays/4):
                histogram_stacked_bar_plot_color_rules_conf_content='''
<rule>
importance = 100
condition  = var(id) eq "col_flowtype_{0}"
fill_color = col_flowtype_{0}
</rule>\n'''.format(str(i),)
                histogram_stacked_bar_plot_color_rules_conf_file.write(histogram_stacked_bar_plot_color_rules_conf_content)
            histogram_stacked_bar_plot_color_rules_conf_content='''
</rules>'''
            histogram_stacked_bar_plot_color_rules_conf_file.write(histogram_stacked_bar_plot_color_rules_conf_content)

        if flow_type == 'sector_outputs' or flow_type == 'sector_inputs':
            for i in range(2+nbr_emissions):
                histogram_stacked_bar_plot_color_rules_conf_content='''
<rule>
importance = 100
condition  = var(id) eq "col_{0}"
fill_color = col_{0}
</rule>\n'''.format(barplot_content[i])
                histogram_stacked_bar_plot_color_rules_conf_file.write(histogram_stacked_bar_plot_color_rules_conf_content)
            histogram_stacked_bar_plot_color_rules_conf_content='''
</rules>'''
            histogram_stacked_bar_plot_color_rules_conf_file.write(histogram_stacked_bar_plot_color_rules_conf_content)
    
        histogram_stacked_bar_plot_color_rules_conf_file.close()

# OLD MERGED CONFIG with external histograms.
#    elif diagram_type == 'merged':
#        # I need to calculate the maximum absolute value to be represented as the outer radius of the histogram. It is the max_value(max_value(total primary inputs), max_value(total finalgoods),max_value(total emission_X))
#        #calculating total outputs
#        sum_intersectoral_matrices = np.zeros((nbr_sectors,nbr_sectors))
#        sum_resource_vectors = np.zeros((1,nbr_sectors))
#        sum_fd_vectors = np.zeros((nbr_sectors,1))
#        sum_emission_array = np.zeros((nbr_sectors,nbr_emissions))
#        
#        for i in range(len(arrays)/4):
#            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
#            sum_resource_vectors=arrays[4*i+1] + sum_resource_vectors
#            sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
#            sum_emission_array=arrays[4*i+3] + sum_emission_array
#        # careful, sum_emission_array is ((nbr_sectors,nbr_emissions)), but I can flatten it to find the maximum
#        
#        max_value=max(max(sum_resource_vectors.flatten()),max(sum_fd_vectors.flatten()),max(sum_emission_array.flatten()))
#        #the histogram_end is passed to ideogram to draw the sectoral labels further out than the histogram
#        histogram_end='1.3r'
#        
#        histograms_conf_file_content='''
#<plots>
#
##Draw axes below all histograms
#<plot>
#z=-5
#<axes>
#<axis>
## grey axis every 100 units 
#color     = grey_a3
#spacing   = 100
#thickness = 2p
#</axis>
#<axis>
## black axis every 100 units 
#color     = black_a2
#spacing   = 500
#thickness = 2p
#</axis>
#</axes>
#</plot>
#
## Default parameters for the external input/output histograms (primary res, fd and emissions)
#type        = histogram
#thickness   = 0p
#color       = black
#
## radial position of the histogram
#r0          = 1r+150p
#r1          = {0}
#
## value start and end of the drawn histogram
#min         = 0
## the maximum should be the maximum of all primary inputs or final outputs
## i.e. max_value(max_value(total primary inputs), max_value(total finalgoods),max_value(total emission_X))
#max         = {1}\n'''.format(histogram_end,max_value)
#        histograms_conf_file.write(histograms_conf_file_content)
#
#        if flow_type == 'sector_outputs' or flow_type == 'sector_inputs':
#            for i in range(2+nbr_emissions):
#                histograms_conf_file_content='''
#<plot>
## Normal histogram for {0}
#file        = ../data/histogram_data_{0}.txt
#fill_color  = col_{0}_a1
#
#</plot>\n'''.format(barplot_content[i])
#                histograms_conf_file.write(histograms_conf_file_content)
#              
#        
#        if flow_type == 'cyclic_acyclic':
#            histograms_conf_file_content='''    
## colors for the different stacks, in order
##fill_under = yes
#fill_color = '''
#            histograms_conf_file.write(histograms_conf_file_content)
#            for i in range(nbr_arrays/4-1):
#                histograms_conf_file_content='''\
#col_flowtype_{0}_a1,'''.format(str(i))
#                histograms_conf_file.write(histograms_conf_file_content)
#            #last flowtype color has no comma at the end
#            histograms_conf_file_content='''\
#col_flowtype_{0}_a1\n'''.format(str(i+1))
#            histograms_conf_file.write(histograms_conf_file_content)
#
#            for i in range(2+nbr_emissions):
#                histograms_conf_file_content='''
#<plot>
## Stacked histogram for{0}
#file        = ../data/histogram_data_{0}.txt
#</plot>\n'''.format(barplot_content[i])
#                histograms_conf_file.write(histograms_conf_file_content)
#                
#        #write the labels for external flows types
#        histograms_conf_file_content='''
#<plot>
## text labels plot for normal or stacked histograms for resources, fd and emissions
#type  = text
#color = black
#file  = ../data/histogram_labels.txt
##note: if label do not fit in the space r1-r0, they will  not be drawn
#r0 = 1.32r
#r1 = 1.5r
#label_parallel = yes
##show_links     = no
##link_dims      = 0p,2p,6p,2p,5p
##link_thickness = 2p
##link_color     = black
##label_snuggle        = yes
##max_snuggle_distance = 1r
##snuggle_tolerance    = 0.25r
##snuggle_sampling     = 2
##snuggle_refine       = yes
#label_size = 20p
#label_font = default
#padding    = 0p
#rpadding   = 0p
#</plot>
#
#</plots>'''
#        histograms_conf_file.write(histograms_conf_file_content)
    
        histograms_conf_file.close()

#################################################################        
##### CREATING THE DATA FILES FOR HISTOGRAM #######
    

# OLD WAY TO PARSE DATA FOR MERGED
#    if diagram_type == 'merged':    
#        os.chdir(working_dir)
#        os.chdir('data')
#### creating ../data/histogram_labels.txt ###
## only required for diagram_type == 'merged'
#
#        histogram_labels_txt_file = open('histogram_labels.txt', 'w')
#        histogram_labels_txt_file_content= '''\
## This file defines the histogram labels
## File format:
## Sector Start End label
## Careful, no decimals in start nor end position
#\n'''
#        histogram_labels_txt_file.write(histogram_labels_txt_file_content)
#
#        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
#        sum_resource_vectors=np.zeros((1,nbr_sectors))
#        sum_fd_vectors=np.zeros((nbr_sectors,1))
#        sum_emission_array=np.zeros((nbr_sectors,nbr_emissions))
#        list_total_inputs_by_flow_type=[]
#        for i in range(len(arrays)/4):
#            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
#            sum_resource_vectors=arrays[4*i+1] + sum_resource_vectors
#            sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
#            sum_emission_array=arrays[4*i+3] + sum_emission_array
#            list_total_inputs_by_flow_type.append(np.sum(arrays[4*i],axis=0).flatten()+arrays[4*i+1].flatten())
#        total_inputs= np.sum(sum_intersectoral_matrices,axis=0) + sum_resource_vectors
#        list_totals=[sum_resource_vectors.flatten(),sum_fd_vectors.flatten()]
#        for j in range(nbr_emissions):
#            # careful with slicing arrays: a[row_start:row_end][:,column_start:column_end]
#            list_totals.append(sum_emission_array[:][:,j:j+1].flatten())
#        # the position in the normal and stacked histograms is calculated as a fraction of the total outputs (or inputs).
#        fraction_of_total_inputs=total_inputs/(2+nbr_emissions)
#        start_position=np.zeros(nbr_sectors)
#        position_list=[start_position]
#        for j in range(2+nbr_emissions):
#            # careful with slicing arrays: a[row_start:row_end][:,column_start:column_end]
#            position_list.append(position_list[-1]+fraction_of_total_inputs.flatten())
#            
#        for i in range(len(sector_names)):
#            for j in range(len(barplot_content)):
#                #remember, no decimals allowed in start/ end position
#                histogram_labels_txt_file_content= '''\
#{0} {1} {2} {3}\n'''.format(sector_names[i], "%.0f" % round(position_list[j][i],0), "%.0f" % round(position_list[j+1][i],0), barplot_content[j])
#                histogram_labels_txt_file.write(histogram_labels_txt_file_content)
#        histogram_labels_txt_file.close()
#
#### creating ../data/histogram_data_XXX.txt for merged flow-by-sector ###
#        
#        if flow_type == 'sector_outputs' or flow_type == 'sector_inputs':
#            # for res, fd, em
#
#            for i in range(len(barplot_content)):
#                #open the data file for res, fd or em_X
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[i]) + '.txt\',\'w\')'
#                # create preamble for res, fd or em_X
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'# data for normal histogram for {0}\n# resources will always be in the first segment\n# careful, no decimals allowed in start end positioning\n# chr start end value\n\n\'\'\'.format(barplot_content[i])'
#                # write preamble for res, fd or em_X
#                exec 'histogram_' +barplot_content[i]+ '_txt_file.write(histogram_' +barplot_content[i]+ '_txt_file_content)'
#                # the arrays are also given in order, so 1st intersectoral matrix, res, fd and emissions
#
#                for j in range(len(sector_names)):
#                    #remember: no decimal in start/end positions
#                     #pdb.set_trace()
#                     exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(position_list[i][j],0), "%.0f" % round(position_list[i+1][j],0), list_totals[i][j])'
#                     exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file.close'
#
#### creating ../data/histogram_data_XXX.txt for merged flow-by-type ###
#
#        if flow_type == 'cyclic_acyclic':
#            # for res, fd, em
#            for i in range(len(barplot_content)):
#                #open the data file for res, fd or em_X
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[i]) + '.txt\',\'w\')'
#                # create preamble for res, fd or em_X
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'# data for stacked histogram for {0}\n# careful, no decimals allowed in start end positioning\n# chr start end Flow_value0,flow_valu1,...\n\n\'\'\'.format(barplot_content[i])'
#                # write preamble for res, fd or em_X
#                exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +barplot_content[i]+ '_txt_file_content)'
#                # the arrays are also given in order, so 1st intersectoral matrix, res, fd and emissions
#
#                for j in range(len(sector_names)):
#                    #remember: no decimal in start/end positions
#                     #pdb.set_trace()
#                     #if only one emission
#                     if len(barplot_content) == 3:
#                         exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0} {1} {2} \'\'\'.format(sector_names[j], "%.0f" % round(position_list[i][j],0), "%.0f" % round(position_list[i+1][j],0), list_totals[i][j])'
#                         exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                         
#                         for k in range(len(arrays)/4-1):
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0},\'\'\'.format(arrays[4*k+i+1].flatten()[j])'
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                         k=k+1    
#                         exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+i+1].flatten()[j])'
#                         exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'    
#                     #if more than 1 emission 
#                     elif len(barplot_content) > 3:
#
#                         if i <= 2:
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0} {1} {2} \'\'\'.format(sector_names[j], "%.0f" % round(position_list[i][j],0), "%.0f" % round(position_list[i+1][j],0), list_totals[i][j])'
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                         
#                             for k in range(len(arrays)/4-1):
#                                 exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0},\'\'\'.format(arrays[4*k+i+1].flatten()[j])'
#                                 exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                             k=k+1    
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+i+1].flatten()[j])'
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#
#                             
##==============================================================================
##                              for em_nbr in range(nbr_emissions-1):
##                               #pdb.set_trace()
##                                   exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\'\'\'.format(arrays[4*k+3][:][:,em_nbr-1,em_nbr].flatten()[j])'
##                                   exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
##                                   em_nbr=em_nbr+1
##                                   exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+3][:][:,em_nbr,em_nbr+1].flatten()[j])'
##                                   exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
##==============================================================================
#                         if i> 2:
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0} {1} {2} \'\'\'.format(sector_names[j], "%.0f" % round(position_list[i][j],0), "%.0f" % round(position_list[i+1][j],0), list_totals[i][j])'
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                             #pdb.set_trace()
#                             for k in range(len(arrays)/4-1):
#                                 
#                                 exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0},\'\'\'.format(arrays[4*k+i][:][:,i-3:i-2].flatten()[j])'
#                                 exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
#                             k=k+1    
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+i][:][:,i-3:i-2].flatten()[j])'
#                             exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'                      
#                                  
#                                  
#                                  
#                                  
##==============================================================================
##                      if nbr_emissions > 1:
##                          for em_nbr in range(nbr_emissions-1):
##                              #pdb.set_trace()
##                              exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\'\'\'.format(arrays[4*k+3][:][:,em_nbr,em_nbr+1].flatten()[j])'
##                              exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
##                          em_nbr=em_nbr+1
##                          exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+3][:][:,em_nbr,em_nbr+1].flatten()[j])'
##                          exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
##                      elif  nbr_emissions == 1:
##                          exec 'histogram_' +str(barplot_content[i])+ '_txt_file_content =\'\'\'{0}\n\'\'\'.format(arrays[4*k+3].flatten()[j])'
##                          exec 'histogram_' +str(barplot_content[i])+ '_txt_file.write(histogram_' +str(barplot_content[i])+ '_txt_file_content)'
##==============================================================================
#                #pdb.set_trace()
#                exec 'histogram_' + str(barplot_content[i])+ '_txt_file.close'                
                

    if diagram_type == 'merged':    
        os.chdir(working_dir)
        os.chdir('data')
    # symmetrical histogram is a circular stacked barplot
    # careful: if a line contains the same start and end, it will draw a line, so you need to filter them out to avoid misleading lines: it would seems there is an small amount of input/output while in reality there is none. That is why I added an if statement checking if start < end position with real values (If I did it with the rounded values, you could  overlook some real input/ output that should be drawn)

### creating ../data/histogram_data_XXX.txt for symmetrical flow-by-sector ###
        
        if flow_type == 'sector_outputs' or flow_type == 'sector_inputs':
            
        #### write resources data file ###
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[0]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[0])'
                # write preamble 
            exec 'histogram_' +barplot_content[0]+ '_txt_file.write(histogram_' +barplot_content[0]+ '_txt_file_content)'
            for j in range(len(sector_names)):
                #remember: no decimal in start/end positions
                resource_start=0
                resource_end = arrays[1].flatten()[j]
                if resource_end > resource_start: #check if the same start/end value
                    exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], resource_start, "%.0f" % round(resource_end,0), \'id=col_\'+barplot_content[0])'
                    exec 'histogram_' +str(barplot_content[0])+ '_txt_file.write(histogram_' +str(barplot_content[0])+ '_txt_file_content)'
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file.close'    

        #### write fd data file    ###   
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[1]) + '.txt\',\'w\')'
                # create preamble 
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} position is after the total intersectoral outputs \n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[1])'
                # write preamble 
            exec 'histogram_' +barplot_content[1]+ '_txt_file.write(histogram_' +barplot_content[1]+ '_txt_file_content)'

            for j in range(len(sector_names)):
                #remember: no decimal in start/end positions
                     #pdb.set_trace()
                # the start point is the end of resources+ intersectoral inputs+intersectoral outputs, the end is the former plus the fd value
                fd_start = arrays[1].flatten()[j] + np.sum(arrays[0],axis=0).flatten()[j]+ np.sum(arrays[0],axis=1).flatten()[j]
                fd_end = fd_start + arrays[2].flatten()[j]
                if fd_start < fd_end:#check if the same start/end value
                    exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(fd_start,0), "%.0f" % round(fd_end,0), \'id=col_\'+barplot_content[1])'
                    exec 'histogram_' +str(barplot_content[1])+ '_txt_file.write(histogram_' +str(barplot_content[1])+ '_txt_file_content)'
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file.close'        

            #### write emissions data file(s) ###
            for i in range(len(barplot_content)-2):
                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[i+2]) + '.txt\',\'w\')'
                    # create preamble 
                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[i+2])'
                    # write preamble 
                exec 'histogram_' +barplot_content[i+2]+ '_txt_file.write(histogram_' +barplot_content[i+2]+ '_txt_file_content)'
                for j in range(len(sector_names)):
                    #remember: no decimal in start/end positions
                    # in the first emissions, the start point is the end of resources+ intersectoral inputs+intersectoral outputs + fd
                    if i == 0:#for the first emission
                        start_pos = arrays[1].flatten()[j] + np.sum(arrays[0],axis=0).flatten()[j]+ np.sum(arrays[0],axis=1).flatten()[j] +arrays[2].flatten()[j]
                        #
                        # emissions are position 3 in the 4-step structures (0,1,2,3)
                        # remember all emissions are in a matrix, so need to call the appropriate column                            
                        end_pos = start_pos + arrays[3][:][:,0:1].flatten()[j]
                        #remember: no decimal in start/end positions
                        if start_pos < end_pos:#check if the same start/end value
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_\'+barplot_content[i+2])'
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file.write(histogram_' +str(barplot_content[2+i])+ '_txt_file_content)'
                        
                    if i>0:
                        # in the subsequent emissions, the start position is the previous and the next is the start + the current emission                        
                        sum_previous_emissions = np.sum(arrays[3][:][:,i-1:i],axis=1).reshape((nbr_sectors,1))
                        #start_pos=(np.sum(arrays[0],axis=1).reshape((nbr_sectors,1))+arrays[2]+sum_previous_emissions).flatten()[j]
                        start_pos = arrays[1].flatten()[j] + np.sum(arrays[0],axis=0).flatten()[j] + np.sum(arrays[0],axis=1).flatten()[j] + sum_previous_emissions.flatten()[j]
                        # final products are position two in the 4-step structures (0,1,2,3)
                        end_pos = start_pos + arrays[3][:][:,i:i+1].flatten()[j]
                        #remember: no decimal in start/end positions
                        if start_pos < end_pos:#check if the same start/end value
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_\'+barplot_content[i+2])'
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file.write(histogram_' +str(barplot_content[2+i])+ '_txt_file_content)'
                            start_pos=end_pos
#==============================================================================
#                     if i == 0:#for the first emission
#                     # the start point is the end of intersectoral output+fd, the end is intersectoral output+fd+em_0
#                         #pdb.set_trace()
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten())[j],0), "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+arrays[3][:][:,0:1].flatten())[j],0), \'id=col_\'+barplot_content[i+2])'
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.write(histogram_' +str(barplot_content[i+2])+ '_txt_file_content)'
# 
#                     elif i > 0:#for the rest of emission
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+np.sum(arrays[3][:][:,0:i],axis=1).flatten())[j],0), "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+np.sum(arrays[3][:][:,0:i+1],axis=1).flatten())[j],0), \'id=col_\'+barplot_content[i+2])'
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.write(histogram_' +str(barplot_content[i+2])+ '_txt_file_content)'
#==============================================================================

                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.close'                 
         
### creating ../data/histogram_data_XXX.txt for symmetrical flow-by-type ###
        
        if flow_type == 'cyclic_acyclic':         
            #### write resources data file ###
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[0]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs, i.e. at the very beginning\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[0])'
                # write preamble 
            exec 'histogram_' +barplot_content[0]+ '_txt_file.write(histogram_' +barplot_content[0]+ '_txt_file_content)'                        
            for j in range(len(sector_names)):
                # in the input side, the start position is at the beginning, i.e. 0                
                start_pos=0
                for i in range(len(arrays)/4):
                    # resources are position one in the 4-step structures (0,1,2,3)
                    end_pos=start_pos + arrays[4*i+1].flatten()[j]
                    #remember: no decimal in start/end positions
                    if start_pos < end_pos:#check if the same start/end value
                        exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                        exec 'histogram_' +str(barplot_content[0])+ '_txt_file.write(histogram_' +str(barplot_content[0])+ '_txt_file_content)'
                        start_pos=end_pos
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file.close'

            #### write fd data file ###
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[1]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0}is after all intersectoral outputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[1])'
                # write preamble 
            exec 'histogram_' +barplot_content[1]+ '_txt_file.write(histogram_' +barplot_content[1]+ '_txt_file_content)'                        
            for j in range(len(sector_names)):
                # the start position is after the resources + TOTAL intersectoral inputs + TOTAL intersectoral outputs of the 4 structures
                sum_intersectoral_matrices = np.zeros((nbr_sectors,nbr_sectors))
                sum_resource_vectors = np.zeros((1,nbr_sectors))
                sum_fd_vectors=np.zeros((nbr_sectors,1)) # required later
                for i in range(len(arrays)/4):
                    sum_intersectoral_matrices = arrays[4*i] + sum_intersectoral_matrices
                    sum_resource_vectors = arrays[4*i+1] + sum_resource_vectors
                    sum_fd_vectors = arrays[4*i+2] + sum_fd_vectors  # required later
                start_pos=sum_resource_vectors.flatten()[j] + np.sum(sum_intersectoral_matrices,axis=1).flatten()[j]+ np.sum(sum_intersectoral_matrices,axis=0).flatten()[j]

                for i in range(len(arrays)/4):
                    # final products are position two in the 4-step structures (0,1,2,3)
                    end_pos=start_pos + arrays[4*i+2].flatten()[j]
                    #remember: no decimal in start/end positions
                    if start_pos < end_pos:#check if the same start/end value
                        exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                        exec 'histogram_' +str(barplot_content[1])+ '_txt_file.write(histogram_' +str(barplot_content[1])+ '_txt_file_content)'
                        start_pos=end_pos
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file.close'        


            #### write emission(s) data file(s) ###
            for em_nbr in range(nbr_emissions):
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[2+em_nbr]) + '.txt\',\'w\')'
                    # create preamble
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is after all intersectoral outputs+all fd+ all other emissions (if any)\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[2+em_nbr])'
                    # write preamble 
                exec 'histogram_' +barplot_content[2+em_nbr]+ '_txt_file.write(histogram_' +barplot_content[2+em_nbr]+ '_txt_file_content)'                        
                if em_nbr == 0:
                    for j in range(len(sector_names)):
                        # in the first emissions, the start position is after the resources + TOTAL intersectoral inputs + TOTAL intersectoral outputs + fd of the 4 structures 
                        start_pos = sum_resource_vectors.flatten()[j] + np.sum(sum_intersectoral_matrices,axis=1).flatten()[j]+ np.sum(sum_intersectoral_matrices,axis=0).flatten()[j] + sum_fd_vectors.flatten()[j]
                        #pdb.set_trace()
                        for i in range(len(arrays)/4):
                            # emissions are position 3 in the 4-step structures (0,1,2,3)
                            # remember all emissions are in a matrix, so need to call the appropriate column                            
                            end_pos=start_pos + arrays[4*i+3][:][:,0:1].flatten()[j]
                            #remember: no decimal in start/end positions
                            if start_pos < end_pos:#check if the same start/end value
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.write(histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content)'
                                start_pos=end_pos
                elif em_nbr > 0:
                    for j in range(len(sector_names)):
                        # in the subsequent emissions, the start position is the previous and the next is the start + the current emission                        
                        sum_fd_vectors=np.zeros((nbr_sectors,1))
                        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
                        sum_emissions=np.zeros((nbr_sectors,1))
                        for i in range(len(arrays)/4):
                            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
                            sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
                            sum_emissions=arrays[4*i+3][:][:,em_nbr-1:em_nbr] + sum_emissions
                        start_pos = sum_resource_vectors.flatten()[j] + np.sum(sum_intersectoral_matrices,axis=1).flatten()[j]+ np.sum(sum_intersectoral_matrices,axis=0).flatten()[j] + sum_fd_vectors.flatten()[j] + sum_emissions.flatten()[j]

                        for i in range(len(arrays)/4):
                            # final products are position two in the 4-step structures (0,1,2,3)
                            end_pos=start_pos + arrays[4*i+3][:][:,em_nbr:em_nbr+1].flatten()[j]
                            #remember: no decimal in start/end positions
                            if start_pos < end_pos:#check if the same start/end value
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j], "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.write(histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content)'
                                start_pos=end_pos
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.close'       

                
    elif diagram_type == 'symmetrical':    
        os.chdir(working_dir)
        os.chdir('data')
    # symmetrical histogram is a circular stacked barplot
    # careful: if a line contains the same start and end, it will draw a line, so you need to filter them out to avoid misleading lines: it would seems there is an small amount of input/output while in reality there is none. That is why I added an if statement checking if start < end position with real values (If I did it with the rounded values, you could  overlook some real input/ output that should be drawn)

### creating ../data/histogram_data_XXX.txt for symmetrical flow-by-sector ###
        
        if flow_type == 'sector_outputs' or flow_type == 'sector_inputs':
            
        #### write resources data file ###
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[0]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[0])'
                # write preamble 
            exec 'histogram_' +barplot_content[0]+ '_txt_file.write(histogram_' +barplot_content[0]+ '_txt_file_content)'
            for j in range(len(sector_names)):
                #remember: no decimal in start/end positions
                if arrays[1].flatten()[j] > 0: #check if the same start/end value
                    exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_in\', 0, "%.0f" % round(arrays[1].flatten()[j],0), \'id=col_\'+barplot_content[0])'
                    exec 'histogram_' +str(barplot_content[0])+ '_txt_file.write(histogram_' +str(barplot_content[0])+ '_txt_file_content)'
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file.close'    

        #### write fd data file    ###   
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[1]) + '.txt\',\'w\')'
                # create preamble 
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} position is after the total intersectoral outputs \n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[1])'
                # write preamble 
            exec 'histogram_' +barplot_content[1]+ '_txt_file.write(histogram_' +barplot_content[1]+ '_txt_file_content)'

            for j in range(len(sector_names)):
                #remember: no decimal in start/end positions
                     #pdb.set_trace()
                # the start point is the end of intersectoral output(i.e. row sum of intersectoral matrix), the end is the former plus the fd value
                if np.sum(arrays[0],axis=1).flatten()[j] < (np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten())[j]:#check if the same start/end value
                    exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(np.sum(arrays[0],axis=1).flatten()[j],0), "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten())[j],0), \'id=col_\'+barplot_content[1])'
                    exec 'histogram_' +str(barplot_content[1])+ '_txt_file.write(histogram_' +str(barplot_content[1])+ '_txt_file_content)'
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file.close'        

            #### write emissions data file(s) ###
            for i in range(len(barplot_content)-2):
                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[i+2]) + '.txt\',\'w\')'
                    # create preamble 
                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[i+2])'
                    # write preamble 
                exec 'histogram_' +barplot_content[i+2]+ '_txt_file.write(histogram_' +barplot_content[i+2]+ '_txt_file_content)'
                for j in range(len(sector_names)):
                    #remember: no decimal in start/end positions
                    # in the first emissions, the start position is after the TOTAL intersectoral outputs of the 4 structures + the fd of the 4 structures
                    if i == 0:#for the first emission
                        start_pos = (np.sum(arrays[0],axis=1).reshape((nbr_sectors,1))+arrays[2]).flatten()[j]
                        #
                        # emissions are position 3 in the 4-step structures (0,1,2,3)
                        # remember all emissions are in a matrix, so need to call the appropriate column                            
                        end_pos = start_pos + arrays[3][:][:,0:1].flatten()[j]
                        #remember: no decimal in start/end positions
                        if start_pos < end_pos:#check if the same start/end value
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_\'+barplot_content[i+2])'
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file.write(histogram_' +str(barplot_content[2+i])+ '_txt_file_content)'
                        
                    if i>0:
                        # in the subsequent emissions, the start position is the previous and the next is the start + the current emission                        
                        sum_previous_emissions=np.sum(arrays[3][:][:,i-1:i],axis=1).reshape((nbr_sectors,1))
                        start_pos=(np.sum(arrays[0],axis=1).reshape((nbr_sectors,1))+arrays[2]+sum_previous_emissions).flatten()[j]
                        # final products are position two in the 4-step structures (0,1,2,3)
                        end_pos=start_pos + arrays[3][:][:,i:i+1].flatten()[j]
                        #remember: no decimal in start/end positions
                        if start_pos < end_pos:#check if the same start/end value
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_\'+barplot_content[i+2])'
                            exec 'histogram_' +str(barplot_content[2+i])+ '_txt_file.write(histogram_' +str(barplot_content[2+i])+ '_txt_file_content)'
                            start_pos=end_pos
#==============================================================================
#                     if i == 0:#for the first emission
#                     # the start point is the end of intersectoral output+fd, the end is intersectoral output+fd+em_0
#                         #pdb.set_trace()
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten())[j],0), "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+arrays[3][:][:,0:1].flatten())[j],0), \'id=col_\'+barplot_content[i+2])'
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.write(histogram_' +str(barplot_content[i+2])+ '_txt_file_content)'
# 
#                     elif i > 0:#for the rest of emission
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+np.sum(arrays[3][:][:,0:i],axis=1).flatten())[j],0), "%.0f" % round((np.sum(arrays[0],axis=1).flatten()+arrays[2].flatten()+np.sum(arrays[3][:][:,0:i+1],axis=1).flatten())[j],0), \'id=col_\'+barplot_content[i+2])'
#                         exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.write(histogram_' +str(barplot_content[i+2])+ '_txt_file_content)'
#==============================================================================

                exec 'histogram_' +str(barplot_content[i+2])+ '_txt_file.close'                 
         
### creating ../data/histogram_data_XXX.txt for symmetrical flow-by-type ###
        
        if flow_type == 'cyclic_acyclic':         
            #### write resources data file ###
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[0]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is before the intersectoral inputs, i.e. at the very beginning\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[0])'
                # write preamble 
            exec 'histogram_' +barplot_content[0]+ '_txt_file.write(histogram_' +barplot_content[0]+ '_txt_file_content)'                        
            for j in range(len(sector_names)):
                # in the input side, the start position is at the beginning, i.e. 0                
                start_pos=0
                for i in range(len(arrays)/4):
                    # resources are position one in the 4-step structures (0,1,2,3)
                    end_pos=start_pos + arrays[4*i+1].flatten()[j]
                    #remember: no decimal in start/end positions
                    if start_pos < end_pos:#check if the same start/end value
                        exec 'histogram_' +str(barplot_content[0])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_in\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                        exec 'histogram_' +str(barplot_content[0])+ '_txt_file.write(histogram_' +str(barplot_content[0])+ '_txt_file_content)'
                        start_pos=end_pos
            exec 'histogram_' +str(barplot_content[0])+ '_txt_file.close'

            #### write fd data file ###
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[1]) + '.txt\',\'w\')'
                # create preamble
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0}is after all intersectoral outputs\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[1])'
                # write preamble 
            exec 'histogram_' +barplot_content[1]+ '_txt_file.write(histogram_' +barplot_content[1]+ '_txt_file_content)'                        
            for j in range(len(sector_names)):
                # in the output side, the start position is after the TOTAL intersectoral outputs of the 4 structures
                sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
                for i in range(len(arrays)/4):
                    sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
                start_pos=np.sum(sum_intersectoral_matrices,axis=1).flatten()[j]
                for i in range(len(arrays)/4):
                    # final products are position two in the 4-step structures (0,1,2,3)
                    end_pos=start_pos + arrays[4*i+2].flatten()[j]
                    #remember: no decimal in start/end positions
                    if start_pos < end_pos:#check if the same start/end value
                        exec 'histogram_' +str(barplot_content[1])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                        exec 'histogram_' +str(barplot_content[1])+ '_txt_file.write(histogram_' +str(barplot_content[1])+ '_txt_file_content)'
                        start_pos=end_pos
            exec 'histogram_' +str(barplot_content[1])+ '_txt_file.close'        


            #### write emission(s) data file(s) ###
            for em_nbr in range(nbr_emissions):
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file = open(\'histogram_data_' + str(barplot_content[2+em_nbr]) + '.txt\',\'w\')'
                    # create preamble
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'# data for circular barplot histogram for {0}\n# {0} is after all intersectoral outputs+all fd+ all other emissions (if any)\n# careful, no decimals allowed in start end positioning\n# chr start end ID\n\n\'\'\'.format(barplot_content[2+em_nbr])'
                    # write preamble 
                exec 'histogram_' +barplot_content[2+em_nbr]+ '_txt_file.write(histogram_' +barplot_content[2+em_nbr]+ '_txt_file_content)'                        
                if em_nbr == 0:
                    for j in range(len(sector_names)):
                        # in the first emissions, the start position is after the TOTAL intersectoral outputs of the 4 structures + the fd of the 4 structures
                        sum_fd_vectors=np.zeros((nbr_sectors,1))
                        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
                        for i in range(len(arrays)/4):
                            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
                            sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
                        start_pos=(np.sum(sum_intersectoral_matrices,axis=1).reshape((nbr_sectors,1))+sum_fd_vectors).flatten()[j]
                        #pdb.set_trace()
                        for i in range(len(arrays)/4):
                            # emissions are position 3 in the 4-step structures (0,1,2,3)
                            # remember all emissions are in a matrix, so need to call the appropriate column                            
                            end_pos=start_pos + arrays[4*i+3][:][:,0:1].flatten()[j]
                            #remember: no decimal in start/end positions
                            if start_pos < end_pos:#check if the same start/end value
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.write(histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content)'
                                start_pos=end_pos
                elif em_nbr > 0:
                    for j in range(len(sector_names)):
                        # in the subsequent emissions, the start position is the previous and the next is the start + the current emission                        
                        sum_fd_vectors=np.zeros((nbr_sectors,1))
                        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
                        sum_emissions=np.zeros((nbr_sectors,1))
                        for i in range(len(arrays)/4):
                            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
                            sum_fd_vectors=arrays[4*i+2] + sum_fd_vectors
                            sum_emissions=arrays[4*i+3][:][:,em_nbr-1:em_nbr] + sum_emissions
                        start_pos=(np.sum(sum_intersectoral_matrices,axis=1).reshape((nbr_sectors,1))+sum_fd_vectors+sum_emissions).flatten()[j]

                        for i in range(len(arrays)/4):
                            # final products are position two in the 4-step structures (0,1,2,3)
                            end_pos=start_pos + arrays[4*i+3][:][:,em_nbr:em_nbr+1].flatten()[j]
                            #remember: no decimal in start/end positions
                            if start_pos < end_pos:#check if the same start/end value
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content =\'\'\'{0} {1} {2} {3}\n\'\'\'.format(sector_names[j]+\'_out\', "%.0f" % round(start_pos,0), "%.0f" % round(end_pos,0), \'id=col_flowtype_\'+str(i))'
                                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.write(histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file_content)'
                                start_pos=end_pos
                exec 'histogram_' +str(barplot_content[2+em_nbr])+ '_txt_file.close'        

         
    return(histogram_end)    
    
###################### /etc/histograms.conf and data files END ######################## 

###################### /etc/links.conf START ######################## 
    
def create_links_conf(working_dir):
    '''Creates the links.conf file in etc directory.
    
    This file defines how links are shown (position, shape, etc.). The link data is created by another routine
    See the conf file comments for more details.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    links_conf_file = open('links.conf', 'w') 
    links_conf_file_content='''\
# this file defines how links are shown (position, shape, etc.)	
  
<links>		
<link>		
ribbon              = yes		
stroke_thickness    = 1p		
file                = ../data/links_data.txt		
bezier_radius       = 0r		

# The radius is the default radius of the ribbon, i.e. where it reaches ON BOTH ENDS		
radius              = 1r - 25p		
# radius,radius1 and radius2 are three options to define the reach of the ribbons. 
#   radius affects both segments ends, radius1 affects start segment and radius2 affects end segment
# note that different options can be set up in the data file, overriding the setting defined here.
# Remember: several options must be place without blank spaces between commas.
	
radius2             = 0.98r		
color               = black_a3		
		
flat	=	yes 
#if flat = no: the ribbons twist to give a nice visual effect. A problem appears when there is a ribbon going to the same chromosome in the contiguous space, then the ribbon appears unconnected, as two individual ribbons, leading to misleading interpretations.
		
</link>		
</links>'''
    links_conf_file.write(links_conf_file_content)
    links_conf_file.close()
    return()
   
###################### /etc/links.conf END ########################

###################### /etc/image.conf START ######################## 
 

def create_image_conf(parent_name, specific_circos_dir, working_dir):
    '''Creates the image.conf file in etc directory.
    
    It defines size, orientation, type and folder destination of the images generated. Names the image file according to the directory names parent_name (contains date stamp + structure) and specific_circos_dir (contains diagram arguments).
    See the conf file comments for more details.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    image_conf_file = open('image.conf', 'w')
    image_name=parent_name+'_'+specific_circos_dir
    image_conf_file_content='''\
# this file defines size, orientation, type and folder destination of the images generated
  
<image>

dir     = ../img
file    = {0}.png
png     = yes
svg     = yes

# radius of inscribed circle in image. So if radius=n, the size of the image will be 2nx2n
radius  = 1500p

# by default angle=0 is at 3 o'clock position
angle_offset      = -88.5 
# In the symmetric, I need to change from -90 to -88.5 so that the symmetry follows a straight vertical line,
# otherwise the gap between input and output is not centered in the middle because the sector starts at -90, so the gap is before. 


#angle_orientation = counterclockwise

auto_alpha_colors = yes
auto_alpha_steps  = 5

background = white

</image>'''.format(image_name)
    image_conf_file.write(image_conf_file_content)
    image_conf_file.close()
    return()
   
###################### /etc/image.conf END ######################## 

###################### /etc/normalisation.conf START ######################## 

def create_normalisation_conf(diagram_type, scale_type, working_dir, nbr_sectors,sector_names, arrays):
    '''Creates the normalisation.conf file in etc directory.
    
    It is always included in the circos.conf file but it is empty ifthe file is generated with scale_type=non_normalised.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    normalisation_conf_file = open('normalisation.conf', 'w') 
    normalisation_conf_file_content='''\
# this file defines the scaling conf for normalisation
# if included in circos.conf, all sectors will have the same width
# careful: no spaces between the scale options if more than one
# this file is blank if generated with the non_normalised option
''' 
    normalisation_conf_file.write(normalisation_conf_file_content)
    if scale_type == 'non_normalised':
        normalisation_conf_file.close()    
    elif scale_type =='normalised':
        normalisation_conf_file_content='''\
chromosomes_scale = ''' 
        normalisation_conf_file.write(normalisation_conf_file_content)
        #calculating total outputs
        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
        sum_resource_vectors=np.zeros((1,nbr_sectors))
        for i in range(len(arrays)/4):
            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
            sum_resource_vectors=arrays[4*i+1] + sum_resource_vectors
        total_inputs= np.sum(sum_intersectoral_matrices,axis=0) + sum_resource_vectors
        normalisation_list=[]
        #the normalisation calculation is referenced to the one sector, here the first one
        for i in range(nbr_sectors-1):
            normalisation_list.append(total_inputs.flatten()[0]/total_inputs.flatten()[i+1])
        if diagram_type == 'merged':          
            for i in range(nbr_sectors-1-1):
                normalisation_conf_file_content='''{0}={1},''' .format(sector_names[i+1],normalisation_list[i])
                normalisation_conf_file.write(normalisation_conf_file_content)
            i=i+1
            normalisation_conf_file_content='''{0}={1}'''.format(sector_names[i+1],normalisation_list[i])
            normalisation_conf_file.write(normalisation_conf_file_content)
        elif diagram_type == 'symmetrical':    
            for i in range(nbr_sectors-1-1):
                normalisation_conf_file_content='''{0}_in={1},''' .format(sector_names[i+1],normalisation_list[i])
                normalisation_conf_file.write(normalisation_conf_file_content)
                normalisation_conf_file_content='''{0}_out={1},''' .format(sector_names[i+1],normalisation_list[i])
                normalisation_conf_file.write(normalisation_conf_file_content)                
            i=i+1
            normalisation_conf_file_content='''{0}_in={1},'''.format(sector_names[i+1],normalisation_list[i])
            normalisation_conf_file.write(normalisation_conf_file_content)
            normalisation_conf_file_content='''{0}_out={1}'''.format(sector_names[i+1],normalisation_list[i])
            normalisation_conf_file.write(normalisation_conf_file_content)
        normalisation_conf_file.close()
    return()
   
###################### /etc/links.conf END ######################## 

###################### /etc/circos.conf START ######################## 

def create_circos_conf(unit, working_dir):
    '''Creates the circos.conf file in etc directory.
    
    The unit is the multiplier by which you multiplied the structure; this is specially required if you work with percentages because circos cannot draw decimals. You need to multiply all your results by, e.g. 1000 and then pass 1000 as 'unit'. This is the main config file called all the others.
    '''
    os.chdir(working_dir)
    os.chdir('etc')
    circos_conf_file = open('circos.conf', 'w') 
    circos_conf_file_content='''\
# this is the circos.conf file

# links definition; also calls the data file
# from the same directory as circos.conf
<<include links.conf>>

# histograms and other plots definition; also calls the data file
# from the same directory as circos.conf
<<include  histograms.conf>>

# the karyotype parameter specifies the file which defines the
# size and name of each sector (chromosome) for the figure
karyotype = ../data/kariotype.txt

#unit of length of the sectors (chromosomes) - this is used
# in other parts of the file where the position is referenced
#I think I am working at 1 instead of the 1000000 (the chromosom position is of the order of e6, but in my case of the order of e3
chromosomes_units      = {0}

# comment this include to avoid normalising the size of all sectors (it might be empty if this file was generated with non_normalised option)
<<include normalisation.conf>>

# toggle to display all of the chromosomes in the
# karyotype file in the order of appearance
chromosomes_display_default = yes

# spacing, position, thickness, color/outline format of the ideograms
# from the same directory as circos.conf
<<include ideogram.conf>>

# position, labels, spacing and grids for tick marks
# from the same directory as circos.conf
<<include ticks.conf>>

# size format and location of the output image
# from the same directory as circos.conf
<<include image.conf>>

# Defining colors, fonts and fill patterns
# The files preceded with etc/ are located in the main circos program etc folder
# I added the <<include attribute_colors.conf>> in the LOCAL etc folder so I can define colors for specific attributes

<colors>
<<include attribute_colors.conf>>
<<include etc/colors.conf>>
</colors>

<fonts>
<<include etc/fonts.conf>>
</fonts>

<patterns>
<<include etc/patterns.conf>>
</patterns>

# the housekeeping file, contains system paremeters that
# define file delimiters, debugging options and other global settings
<<include etc/housekeeping.conf>>'''.format(unit)
    circos_conf_file.write(circos_conf_file_content)
    circos_conf_file.close()
    return()
   
###################### /etc/links.conf END ######################## 

###################### /data/links_data.txt START ######################## 

def create_links_data_txt(diagram_type, flow_type, ribbon_order, working_dir, data_filename, nbr_sectors, nbr_emissions, sector_names, arrays):
    '''Creates the links_data.txt f file in data directory according to options ribbon_sorting (sorting) and flow_type (coloring).
    
    The links can be sorted by
    - ribbon size: 
        - option size_desc places large row/column cells at the start of segment
        - option size_desc places small row/column cells at the start of segment
    - end segment order with option native (reduces cross-over and makes a cleaner visual image.
    The links are also colored according to the flow_type option.
    - sector_outputs: outputs have the same color as sector producing them
    - sector_inputs: inputs have the same color as sector receiving them
    - cyclic_acyclic: ribbons colored according to flowtype (Self-cycling, inter-cycling, indirect acyclic and direct acyclic)
    '''
    os.chdir(working_dir)
    os.chdir('data')
    links_data_txt_file = open('links_data.txt', 'w') 
    links_data_txt_content='''\
# this is the links_data.txt file defining the position and color of the ribbons
# links are defined on a sigle line, without unique identifier so need to use circos version 0.6 (I cannot recall the exact version) so use the latest!
# you can add more options but do not leave white spaces between the commas.
# remember, no decimals in the position
'''
    links_data_txt_file.write(links_data_txt_content)
    
    # constructing a table with the intersectoral flows
    # column 0: positions of the giving sectors in the ideogram
    # column 1: output from from sector
    # column 2: positions of the receiving sectors in the ideogram
    # column 3: input from from sector
    # column 4: color of the ribbon
    
    # however, the number of sectors represented depends whether it is a symmetrical of merged diagram
    if flow_type == 'sector_outputs':

        if diagram_type == 'merged':
            # number of sectors represented = number of sectors
            table_intersectoral_flows=[]
            for i in range(nbr_sectors):
                for j in range(nbr_sectors):
                    #do not append if the flow is 0
                    if arrays[0][i][j] == 0:
                        continue
                    table_intersectoral_flows.append((i,arrays[0][i][j],j,arrays[0][i][j],'col_' + sector_names[i].lower()))
        
        if diagram_type =='symmetrical':
            # number of sectors represented = 2*(number of sectors)
            # the row sectors position are represented in order but the columns' position is inversed
            # e.g. sector0_out, sector1_out, sector1_in, sector0_in
            table_intersectoral_flows=[]
            for i in range(nbr_sectors):
                for j in range(nbr_sectors):
                    #do not append if the flow is 0
                    if arrays[0][i][j] == 0:
                        continue
                    table_intersectoral_flows.append((i,arrays[0][i][j],2*nbr_sectors-1-j,arrays[0][i][j],'col_' + sector_names[i].lower()))
            
    elif flow_type == 'sector_inputs':

        if diagram_type == 'merged':
            # number of sectors represented = number of sectors
            table_intersectoral_flows=[]
            for i in range(nbr_sectors):
                for j in range(nbr_sectors):
                    #do not append if the flow is 0
                    if arrays[0][i][j] == 0:
                        continue
                    table_intersectoral_flows.append((i,arrays[0][i][j],j,arrays[0][i][j],'col_' + sector_names[j].lower()))
        
        if diagram_type =='symmetrical':
            # number of sectors represented = 2*(number of sectors)
            # the row sectors position are represented in order but the columns' position is inversed
            # e.g. sector0_out, sector1_out, sector1_in, sector0_in
            table_intersectoral_flows=[]
            for i in range(nbr_sectors):
                for j in range(nbr_sectors):
                    #do not append if the flow is 0
                    if arrays[0][i][j] == 0:
                        continue
                    table_intersectoral_flows.append((i,arrays[0][i][j],2*nbr_sectors-1-j,arrays[0][i][j],'col_' + sector_names[j].lower()))
                    

    elif flow_type == 'cyclic_acyclic':

        if diagram_type == 'merged':
            # number of sectors represented = number of sectors
            table_intersectoral_flows=[]            
            for flow_type_nbr in range(len(arrays)/4):                             
                for i in range(nbr_sectors):
                    for j in range(nbr_sectors):
                        #do not append if the flow is 0
                        if arrays[4*flow_type_nbr][i][j] == 0:
                            continue
                        table_intersectoral_flows.append((i,arrays[4*flow_type_nbr][i][j],j,arrays[4*flow_type_nbr][i][j],'col_flowtype_' + str(flow_type_nbr)))

        if diagram_type =='symmetrical':
            # number of sectors represented = 2*(number of sectors)
            # the row sectors position are represented in order but the columns' position is inversed
            # e.g. sector0_out, sector1_out, sector1_in, sector0_in
            table_intersectoral_flows=[]            
            for flow_type_nbr in range(len(arrays)/4):                                         
                for i in range(nbr_sectors):
                    for j in range(nbr_sectors):
                        #do not append if the flow is 0
                        if arrays[4*flow_type_nbr][i][j] == 0:
                            continue
                        table_intersectoral_flows.append((i,arrays[4*flow_type_nbr][i][j],2*nbr_sectors-1-j,arrays[4*flow_type_nbr][i][j],'col_flowtype_' + str(flow_type_nbr)))
    else:
       sys.exit('''Error: the flow_type argument passed to create_links_data_txt function is not one expected''') 

# then I need to sort that table depending whether   size_desc, size_asc or native
#remember:
    # column 0: positions of the giving sectors in the ideogram
    # column 1: output from from sector
    # column 2: positions of the receiving sectors in the ideogram
    # column 3: input from from sector
    # column 4: color of the ribbon
    if ribbon_order =='size_desc':
        #see function sort_table(table, cols) for more info on the following
        #or table_intersectoral_flows.sort(key=lambda a: a[0])
        sorted_table_intersectoral_flows = sorted(table_intersectoral_flows, key=lambda a: ( a[0], -a[1]))  
        
    elif ribbon_order =='size_asc':
        #see function sort_table(table, cols) for more info on the following
        #or table_intersectoral_flows.sort(key=lambda a: a[0])
        sorted_table_intersectoral_flows = sorted(table_intersectoral_flows, key=lambda a: ( a[0], a[1]))
        
    elif ribbon_order == 'native':
        
        if  diagram_type == 'symmetrical':
            nbr_represented_sectors = 2*nbr_sectors
        elif diagram_type == 'merged':
            nbr_represented_sectors = nbr_sectors
        order_list_of_end_segments=range(nbr_represented_sectors)
        #get the first sector in the center of the list
        positions_to_shift=int(nbr_represented_sectors/2)
        order_list_of_end_segments = order_list_of_end_segments[positions_to_shift+1:] + order_list_of_end_segments[:positions_to_shift+1]
        
        flows_in_table = nbr_sectors*len(arrays)/4
        
        sorted_table_intersectoral_flows=[]
        # need to sort by first column so I parse the table in tmp tables according to sector segment. 
        table_intersectoral_flows.sort(key=lambda a:  a[0])
        # for each sector, reorder the end side of the flow        
        for i in range(nbr_sectors):
            
            # get the rows with of output sector
            # there are always nbr_sectors lines for each sector (Assuming a previous ordering according to the first column)
            tmp=table_intersectoral_flows[flows_in_table*i:flows_in_table*(i+1)]
            # then, order the rows from that sector according to its relative position of the ends.
            #pdb.set_trace()
            tmp.sort(key=lambda a: (a[0], order_list_of_end_segments.index(a[2])))
            # shift one position
            order_list_of_end_segments=order_list_of_end_segments[1:] + order_list_of_end_segments[:1]
            sorted_table_intersectoral_flows.extend(tmp)
        #pdb.set_trace()
        #for i in range(nbr_represented_sectors):

            #order_list_for_end_segment=[range(nbr_represented_sectors,nbr_represented_sectors/2,-1),range(0,nbr_represented_sectors,1)]

#==============================================================================
#         for i in range(nbr_represented_sectors):
#             for j in range(len(table_intersectoral_flows-1)):            
#                 current_line=table_intersectoral_flows[j]
#                 if (i in current_line[0] or i in current_line[2]):
#                     next_line=table_intersectoral_flows[j+1]
#                     if (i in next_line[0] or i in next_line[2]):
#                         compare the order
#                     else:
#                        for j in range(j,len(table_intersectoral_flows-1)):
#                            next_line=table_intersectoral_flows[j+1]
#                            if (i in next_line[0] or i in next_line[2]):
#                                compare the order
#==============================================================================
                        
    else:
        sys.exit('''Error: the ribbon_order argument passed to create_links_data_txt function is not one expected''')     


# then I will need to transform the sorted_table_intersectoral_flows into one readable by circos 
# three things to do: 1: change sector position by names, 2: add 2 columns for start/end position of each ribbon and 3: set the absolute references.

# here I am doing 2 

    # just extend the columns       
    final_table=[]
    for i in range(len(sorted_table_intersectoral_flows)):
        #remember:
        # column 0: positions of the giving sectors in the ideogram
        # column 1: output from from sector
        # column 2: positions of the receiving sectors in the ideogram
        # column 3: input from from sector
        # column 4: color of the ribbon
        final_table.extend([(sorted_table_intersectoral_flows[i][0],0,sorted_table_intersectoral_flows[i][1],sorted_table_intersectoral_flows[i][2],0,sorted_table_intersectoral_flows[i][3],sorted_table_intersectoral_flows[i][4])])
    # final_table content
    # column 0: positions of the giving sectors in the ideogram
    # column 1: 0
    # column 2: flow value 
    # column 3: positions of the receiving sectors in the ideogram
    # column 4: 0 
    # column 5: flow value            
    # column 6: color of the ribbon   

# Now, doing 1 and 3: changing the name and placing the start/end positions of each flow

    #create a list of sector names
    if diagram_type == 'merged':
        represented_sector_names = sector_names
    if diagram_type == 'symmetrical':
        represented_sector_names = []
        for i in range(len(sector_names)):
            represented_sector_names.append(sector_names[i]+'_out')
        for i in range(len(sector_names)-1,-1,-1):
            represented_sector_names.append(sector_names[i]+'_in')

    if diagram_type == 'merged':
        #calculating total outputs
        sum_intersectoral_matrices=np.zeros((nbr_sectors,nbr_sectors))
        sum_resource_vectors=np.zeros((1,nbr_sectors))
        for i in range(len(arrays)/4):
            sum_intersectoral_matrices=arrays[4*i] + sum_intersectoral_matrices
            sum_resource_vectors=arrays[4*i+1] + sum_resource_vectors

        # the outputs start after the primary resources 
        # the inputs start after the primary resources + TOTAL sum of sectoral outputs.
        # I think I can do a generic sum (no need of cyclic_acyclic case....)
        #pdb.set_trace()
        outputs_start = sum_resource_vectors.flatten()
        last_output_position = outputs_start
        inputs_start= sum_resource_vectors.flatten() + np.sum(sum_intersectoral_matrices,axis=1)
        last_input_position = inputs_start
        
        for i in range(len(final_table)):
            output_flow_start = last_output_position[final_table[i][0]]
            output_flow_end = output_flow_start + final_table[i][2]
            #pdb.set_trace()
            input_flow_start = last_input_position[final_table[i][3]]
            input_flow_end = input_flow_start + final_table[i][5]
            last_output_position[final_table[i][0]] = output_flow_end
            last_input_position[final_table[i][3]] = input_flow_end
            final_table[i]=(represented_sector_names[final_table[i][0]],output_flow_start, output_flow_end,represented_sector_names[final_table[i][3]],input_flow_start,input_flow_end,final_table[i][6])

    if diagram_type == 'symmetrical':
        # the outputs start at the beginning of the (output) segment
        # the inputs start after the TOTAL sum of sectoral PRIMARY inputs.
        # I think I can do a generic sum (no need of cyclic_acyclic case....)            
        outputs_start = np.zeros(len(sector_names))
        last_output_position = outputs_start
        #calculating total priimary resources
        sum_resource_vectors=np.zeros(nbr_sectors)
        for i in range(len(arrays)/4):
            sum_resource_vectors = arrays[4*i+1].flatten() + sum_resource_vectors
        inputs_start= sum_resource_vectors
        last_input_position = inputs_start
        # careful, the last positions need to be reversed
        last_sectoral_position=last_output_position.tolist()+last_input_position.tolist()[::-1]
        #pdb.set_trace()
        for i in range(len(final_table)):
            output_flow_start = last_sectoral_position[final_table[i][0]]
            output_flow_end = output_flow_start + final_table[i][2]
            input_flow_start = last_sectoral_position[final_table[i][3]]
            input_flow_end = input_flow_start + final_table[i][5]
            last_sectoral_position[final_table[i][0]] = output_flow_end
            last_sectoral_position[final_table[i][3]] = input_flow_end
            final_table[i]=(represented_sector_names[final_table[i][0]],output_flow_start, output_flow_end,represented_sector_names[final_table[i][3]],input_flow_start,input_flow_end,final_table[i][6])    

    #pdb.set_trace()

    # NOW I JUST NEED TO WRITE THE DATA TO THE FILE
    # Remember that if you want to add more options, you cannot leave spaces between the commas separating the options
    # no decimals allowed; to round "%.0f" % round(nbr_to_round,0)
    for i in range(len(final_table)):
        tmp = '''{0}  {1}  {2}  {3}  {4}  {5} {6}\n'''.format(final_table[i][0], "%.0f" % round(final_table[i][1],0),"%.0f" % round(final_table[i][2],0), final_table[i][3], "%.0f" % round(final_table[i][4],0), "%.0f" % round(final_table[i][5],0),'color='+ final_table[i][6]+'_a2')
        links_data_txt_file.write(tmp)
         
    links_data_txt_file.close()
    
    return()
   
###################### /data/links_data.txt END ######################## 

def execute_circos(parent_name, specific_circos_dir, working_dir, circos_open_images):
    ''' This function executes circos so that the image is generated.'''
    
    os.chdir(working_dir)
    os.chdir('etc')
    circos_program_name='circos-0.65-pre2'
    print('\n+++ Running Circos +++')
    # note: do not run circos in the background, otherwise you won't get the the debugging output in the log. However, if you want to speed up phymetec while drawing you can try to add an & after the last argument of TheCommand. 
    TheCommand='''{0} -conf circos.conf -noparanoid'''.format(circos_program_name)
    os.system(TheCommand)
    print('\n+++ Running Circos has finished, continuing ... +++')
    os.chdir(working_dir)
    os.chdir('img')
    image_name=parent_name+'_'+specific_circos_dir # careful: should be the same defined in image.conf
    if circos_open_images:
        if os.name == 'posix':
            #note: run the visualisation as background; otherwise it might stop phymetec.
            os.system('eog {0}.png &'.format(image_name))
    
    return()