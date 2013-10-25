#!/usr/bin/python

# Filename: metabx.py
#revision history
#v0.1 change calculation of minimum flow : after check if the sum of cycles going a node is inferior or equal to the node minimal throughput. If not, the cycles flows need to be resized according to their flow probabilities to pass through the node (NOW according to CIRCUIT PROBABILITIES INSTEAD OF THE FLOW PROB)
#v0.2: added 2 sub-routines: cycle_decomposition_v01 (imported as cd) which uses Ulanowicz (1983) to calculate and extract all cycles; and draw_sankeys_v02 (imported as draw_sankeys) which draws the sankey diagrams for cycling matrix only (I wanted to do for the straight flows as well but I found a better way to represent the flows so I just did the other one). The function saves a png in the working directory/images with the name and then the image is recovered later in the main program to be added in the xls output. 
#v0.3: makes structural and cycle analysis for all output-based (or product-based) production structures (inter-cycling, self-cycling, direct acyclic and indirect acyclic). Akso added circos interface to generate the config and data files automatically.


__version__ = '0.3'

# TODO: something 
# XXX: MARKER of source
 
#for debugging: uncomment 'import pdb' and place pdb.set_trace() b4 the line I need to start debugging
import pdb #pdb.set_trace()

import os as os
import sys as sys
import numpy as np
from numpy import linalg as LA# NOTE: the numpy version of linalg is the lite version of the one contained in scipy
import pprint as pprint #to print tables nicely
import time
# Make all matlib functions accessible at the top level via M.func()
# import numpy.matlib as M #I rather stay consistent and use numpy arrays only, the matlib package returns matrix objects
# Make some matlib functions accessible directly at the top level via, e.g. rand(3,3)
# from numpy.matlib import rand,zeros,ones,empty,eye #I rather stay consistent and use numpy arrays only, the matlib package returns matrix objects
#import networkx as nx # not requiered here, imported in the function cycle_decomposition_v01
import xlwt as xlwt
import xlrd as xlrd
import cycle_decomposition as cd
#import draw_sankeys as draw_sankeys # the draw sankeys does not work very well
import circos_interface as circos_interface
import backward_trace as backward_trace

# Make some shorcuts
T = np.transpose    #    np.transpose(A) --> T(A)
P=pprint.pprint

#class definition used to write to a log file and the standard output at the same time (similar to tee command in shell)
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)


######START PROGRAM###############

##############################################################################
##############################################################################


###### Configuration of the program

##  Ask for working directory and file to analyse
# NOTE: I could get rid of the differentiation nt posix by using os.path.join()
if os.name == 'nt':
    #dirPath=input("Type the absolute working directory in single quotes separated by two backslahses (ex: 'C:\\this\\is\\a\\windows\\path'):")    
    dirPath='C:\\Users\\amartin\\Dropbox\\PhyMetEc\\spyder_project\\PhyMetEc'    
    #enter the working dir
    os.chdir(dirPath)
    #create "images" directory already if it does not exists in the working directory.
elif os.name == 'posix':
    #dirPath=input("Type the absolute working directory in single quotes (ex: '/this/is/a/linux/path'):")    
    dirPath='/home/aleix/PhD/Dropbox/PhyMetEc/spyder_project/PhyMetEc_DATA'
    #enter the working dir
    os.chdir(dirPath)
    #create "images" directory already if it does not exists in the working directory.
else:
    sys.exit('''Error: the operating system was not recognised as 'nt' nor 'posix', exiting.''')

#loading the input data
#data_filename=input("Type the name of the xls file containing Z,r and f in brackets (it is assumed to be inside it, or type a relative address relative to the working dir):")
data_filename='PIOT_ITA.xls'
#data_filename='MIOT_Br_1995_10_setores2.xls'
#data_filename='Ulanowicz example.xls'

#asking for the output file name
#output_filename=input("Type the name of the output xls you\'d like (in single quotes) or just type '' to append a timestamp to input file:")
output_filename='' #temporary for debugging
#fill the name if left blank
time_at_start = time.strftime("%Y%m%d_%H%M")
if output_filename == '':
    output_filename=os.path.splitext(data_filename)[0]+'_OUT_'+time_at_start+'.xls'
output_binary_file=os.path.splitext(output_filename)[0]+'.npz'    
#open a logfile to be able to write to it. Note: the log file is only writen when it is closed at the end of the program.
logfile = open(os.path.splitext(output_filename)[0]+".log", "w")
#write to a log file and the standard output at the same time using the Tee function
sys.stdout = Tee(sys.stdout, logfile)


# Other configuration options
# TODO: create a parseable config file containing program switches

# Config for the circos_interface module
circos_draw = False
circos_execute = True
circos_open_images = True



###### intialise and check the workbook     ##################################
print('... Starting Phymetec version {0} at {1} (yyyymmdd_hhmm) '.format(__version__,time_at_start))
print('\n++++++++++ READING INPUT FILE ++++++++++++++++++++++++++++')
print('')

current_wb = xlrd.open_workbook(data_filename)
# check the required sheets in the workbook
sheetnames_list = current_wb.sheet_names()
if sheetnames_list.__contains__('Z'):
    Z_worksheet= current_wb.sheet_by_name('Z')
else:
    sys.exit('Error: the workbook does not contain the \'Z\' worksheet, exiting.')
if sheetnames_list.__contains__('f'):
    f_worksheet= current_wb.sheet_by_name('f')
else:
    sys.exit('Error: the workbook does not contain the \'f\' worksheet, exiting.')

if sheetnames_list.__contains__('r'):
    r_worksheet= current_wb.sheet_by_name('r')
else:
    sys.exit('Error: the workbook does not contain the \'r\' worksheet, exiting')
    
if sheetnames_list.__contains__('title and comments'):
    title_worksheet= current_wb.sheet_by_name('title and comments')
else:
    sys.exit('Error: the workbook does not contain the \'title and comments\' worksheet, exiting')
    

######  Creating the arrays     ##############################################
# first the headers and arrays of each worksheet are extracted as x_PRE_array
# then, the matrix/vector are transformed to float and stored as x_array
# finally, the headers and the x_array are stored together as x_array_with_headers# but I am not sure I am going to use that...

# 

####    Z       ################################################
##      Reading all values from Z worksheet
Z_PRE_array = []
for row_index in range(Z_worksheet.nrows):
     Z_PRE_array.append(Z_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead

##      create the Z array
Z_array = [[c for c in row[1:]] for row in Z_PRE_array[1:]] # XXX: ERASE
#this was supposed to be the same as below, but it is not. The issue is how to "rewrite! the [] that contains "loat(c)...row[1:]".
#for row in Z_PRE_array[1:]:
#    print row #each row is a list of cells
#    for col_index in row[1:]: #range(1,Z_worksheet.ncols) :#wrong because the row contains a list of cells, not integers
#        #print row[col_index]
#        Z_array = float(col_index)

##      merge headers and array in dictionary entry
Z_array_with_headers = {'column headings': Z_PRE_array[0][1:],'row headings': [row[0] for row in Z_PRE_array[1:]], 'array': np.array(Z_array)} # XXX: ERASE


####    r       ################################################
##      Reading all values from r
r_PRE_array = []
for row_index in range(r_worksheet.nrows):
     r_PRE_array.append(r_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead

##      create the r array
r_array = [[c for c in row[1:]] for row in r_PRE_array[0:]] # XXX: ERASE

##      merge headers and array in dictionary entry
r_array_with_headers = {'row headings': [row[0] for row in r_PRE_array[0:]], 'array': np.array(r_array)} # XXX: ERASE
 
####    f       ################################################
##      Reading all values from f
f_PRE_array = []
for row_index in range(f_worksheet.nrows):
     f_PRE_array.append(f_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead

##      create the f array #I had previously f_array = [[float(c) for c in row[0:]] for row in f_PRE_array[1:]]
# the f_array contains the fd and emissions
f_array = [[c for c in row[0:]] for row in f_PRE_array[1:]] # XXX: ERASE

##      merge headers and array in dictionary entry
f_array_with_headers = {'column headings': f_PRE_array[0][0:], 'array': np.array(f_array)} # XXX: ERASE
# note: the different column vectors are extracted later: the final demand (or useful outputs) is called fd_all, and the different related outputs are called 'w'+str(waste_index)+'_array', i.e. wi_array
    
####    title       ################################################
##      Reading all values from title sheet
title =  title_worksheet.row_values(0) # XXX: ERASE
title = str(title[0]) # XXX: ERASE
units =  title_worksheet.row_values(1) # XXX: ERASE
units = str(units[0]) # XXX: ERASE
comments =  title_worksheet.row_values(2) # XXX: ERASE
comments = str(comments[0]) # XXX: ERASE




##############################################################################
##############################################################################
# counting the disposals to nature based on header names. Originally, the ideas was to make the program flexible and accept any amount of wastes and any amount of final good columns. But this complicates the whole algorithm unnecessarily. So I finally assume there is only one fd as the first column of f_array althought this first implementation recognises all columns starting with w as waste.
NBR_disposals=0
for header_name in f_array_with_headers['column headings']:
    if header_name.startswith('w'):
        NBR_disposals += 1
if NBR_disposals >= 1:
    print('{0} disposals to nature detected'.format(NBR_disposals))    
else:
    sys.exit('''Error: the \'f\' worksheet does not contain any waste because no column header name starts by 'w', exiting.''')

###### convert the "arrays" (which are in fact lists) into numpy arrays
f_array=np.array(f_array) # XXX: ERASE
Z_array=np.array(Z_array) # XXX: ERASE
r_array=np.array(r_array) # XXX: ERASE



   


##############################################################################
########## IMPORTANT: the arrays are 2D even if they represent a vector ######
##########              solution: they can be flatten,e.g.: r_array.flatten() 
##############################################################################

    
######      check of the correct dimensions of the data input       ##########
####    check dimensions of the different arrays and quit if not matching
(Z_rows,Z_cols)=np.shape(Z_array)
(r_rows,r_cols)=np.shape(r_array)
(f_rows,f_cols)=np.shape(f_array)
if Z_rows != Z_cols:
    sys.exit('the Z matrix is not square, exiting.')
if r_cols != Z_cols:
    sys.exit('the Z matrix and r have not the same number of columns, exiting.')
if Z_rows != f_rows:
    sys.exit('the Z matrix and f have not the same number of rows, exiting.')

NBR_sectors=Z_rows#could be Z_cols as well
print('''The Z matrix has {0} sectors.\n'''.format(NBR_sectors))


# label dictionary
label_dictionary=dict()
label_dictionary['title']=str(title_worksheet.row_values(0)[0])
label_dictionary['units']=str(title_worksheet.row_values(1)[0])
label_dictionary['comments']=str(title_worksheet.row_values(2)[0])
label_dictionary['resource_labels']= [row[0] for row in r_PRE_array[0:]]
label_dictionary['row_sector_labels']= [row[0] for row in Z_PRE_array[1:]]
label_dictionary['column_sector_labels']= Z_PRE_array[0][1:]
label_dictionary['waste_labels']= f_PRE_array[0][1:] # assumes only one final demand
label_dictionary['fd_labels']= f_PRE_array[0][0] # assumes only one final demand


# Actual structure dictionary
actual_structure_dictionary=dict()
actual_structure_dictionary['r']=np.array([[c for c in row[1:]] for row in r_PRE_array[0:]])
actual_structure_dictionary['Z']=np.array([[c for c in row[1:]] for row in Z_PRE_array[1:]])
actual_structure_dictionary['fd']=np.array([[c for c in row[0:]] for row in f_PRE_array[1:]])[:][:,0:1] # assuming only one column --- could be [:,0]
actual_structure_dictionary['tot_final_outputs']=actual_structure_dictionary['fd']
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['w'+str(waste_index)]=np.array([[c for c in row[0:]] for row in f_PRE_array[1:]])[:][:,str(waste_index+1)].reshape((NBR_sectors,1))
    actual_structure_dictionary['tot_final_outputs']=actual_structure_dictionary['tot_final_outputs']+actual_structure_dictionary['w'+str(waste_index)]




#Create a column for each type of output
# fd_all      final demand vector  [assuming first vector is the one corresponding to fd!]
# wi_all      waste i vector

fd_all = f_array[:][:,0:1] # not sure if correct # XXX: ERASE
w_all=f_array[:][:,1:1+NBR_disposals] # XXX: ERASE
for waste_index in range(NBR_disposals): # XXX: ERASE
    exec 'w'+str(waste_index)+'_all = f_array[:,'+str(waste_index+1)+'].reshape((NBR_sectors,1))' # XXX: ERASE


######      check that the PIOT is balanced, i.e. total inputs= total outputs
#total_inputs=column sum of Z + r
total_inputs=np.sum(Z_array,axis=0)+r_array # XXX: ERASE
total_inputs=np.sum(actual_structure_dictionary['Z'],axis=0)+actual_structure_dictionary['r']
#total_inputs=total_inputs[0] # gives error because it is not a matrix anymore
#total_inputs=row sum of Z + f
total_outputs=np.sum(Z_array,axis=1).reshape(NBR_sectors,1)+np.sum(f_array,axis=1).reshape(NBR_sectors,1) # XXX: ERASE
total_outputs=np.sum(actual_structure_dictionary['Z'],axis=1).reshape(NBR_sectors,1)+actual_structure_dictionary['fd']
for waste_index in range(NBR_disposals):
    total_outputs=total_outputs+actual_structure_dictionary['w'+str(waste_index)]
actual_structure_dictionary['x']=total_outputs
# raise error if total_inputs are different from total_outputs for more than 'acceptable value'
max_balancing_difference=0.00001 # max_balancing_difference represents a percentage (so 1 is 100%)
for i_index in range(NBR_sectors):
    if total_inputs[0][i_index]-total_outputs[i_index][0] > max_balancing_difference*(total_inputs[0][i_index]+total_outputs[i_index][0])/2 :
        sys.exit('''Error: Total outputs different from total inputs for sector {0}, i.e, the IOT is not balanced, exiting.'''.format(i_index))
        
##############################################################################
##############################################################################
print(
'\n++++++++++   DATA ANALYSIS   +++++++++++++++++++++++++++++++++++++++++++++')


######  Calculate the technical coef matrix, endogenising all disposals to nature and calculate the Leontied inverse to be able to operate the PIOT with goods alone
#   name and description of the calculated variables
#   A     technical coefficient matrix for all flows
#   Ei    output coefficient matrices to endogenise the disposals to nature
#   Etot  auxiliar variable to calculate L # XXX: ERASE
#   L     Leontief inverse matrix taking endogenising all disposals to nature - see Altimiras-Martin (2013) for a detailed explanation
#   r_coefs input (resource) coeficients

A=np.dot(Z_array,LA.inv(np.diag(total_inputs[0])))#CAREFUL: total_outputs and tota_inputs are 2D arrays, so np.diag will extract their diagonal, that is why I took the first element of total_inputs, which is the vector (it would not work for total_outputs # XXX: ERASE
actual_structure_dictionary['A']=np.dot(Z_array,LA.inv(np.diag(total_inputs[0])))

# create all Ei and the sum of the Etot
# Remember: they are valid for all output structures
Etot=np.zeros((NBR_sectors,NBR_sectors))#the shape is a list (3,3), so the syntax is zeros((3,3)) # XXX: ERASE
for i in range(NBR_disposals):#need +1 because the range does not count the last # XXX: ERASE
    exec 'E'+str(i)+'=np.dot(LA.inv(np.diag(total_outputs.flatten())),w'+str(i)+'_all)' # XXX: ERASE
    exec 'E'+str(i)+'=np.diag(E'+str(i)+'.flatten())' # XXX: ERASE
    Etot=Etot+eval('E'+str(i)) # XXX: ERASE

L_tmp=np.eye(NBR_sectors)-actual_structure_dictionary['A']
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['E'+str(waste_index)]=np.diag(np.dot(LA.inv(np.diag(actual_structure_dictionary['x'].flatten())),actual_structure_dictionary['w'+str(waste_index)]).flatten())
    L_tmp=L_tmp-actual_structure_dictionary['E'+str(waste_index)]

#create Leontief including all wastes
L=LA.inv(np.eye(NBR_sectors)-A-Etot) # XXX: ERASE
actual_structure_dictionary['L']=LA.inv(L_tmp)

r_coefs=np.dot(r_array,LA.inv(np.diag(total_outputs.flatten()))) # XXX: ERASE
actual_structure_dictionary['r_coefs']=np.dot(r_array,LA.inv(np.diag(total_outputs.flatten())))



##############################################################################
######  Calculation of the PRODUCT-BASED production structure for each good (there will be "NBR_sectors" production structures)
#   name and description of the calculated variables # XXX: ERASE
#   r_coefs   input coefficients for the materials # XXX: ERASE
#   fi        one unit of final demand of sector i (i belongs to 0 to NBR_sectors-1) # XXX: ERASE
#the variable for each production structure are the same as the main variable with i appended to it. For example: # XXX: ERASE
#   ri        resources required to satisfy fi # XXX: ERASE
#   wji       type-j emissions generated to satisfy fi # XXX: ERASE
#   Twi     total emissions to satisfy fi # XXX: ERASE
#   Zi       intersectoral flows required to satisfy fi # XXX: ERASE
#   xi      total outputs generated to satisfy fi # XXX: ERASE
#   Toi     total external outputs (emissions+final goods) to satisfy fi # XXX: ERASE
#   fi_array    array containing fi and all wji # XXX: ERASE
#   wi_array    array containing all wji # XXX: ERASE


for i in range(NBR_sectors): # XXX: ERASE
    exec 'f'+str(i)+'=np.zeros(NBR_sectors)'#fi=(0...0) # XXX: ERASE
    exec 'f'+str(i)+'['+str(i)+']=1'#f1=(1 0 0) with 1 in the i position # XXX: ERASE
    exec 'f'+str(i)+'_array=np.array(f'+str(i)+').reshape(('+str(NBR_sectors)+',1))' # XXX: ERASE
    exec 'x'+str(i)+'=np.dot(L,f'+str(i)+')'#xi=L*fi # XXX: ERASE
    exec 'total_outputs_'+ str(i)+ '= x'+str(i) # XXX: ERASE
    exec 'r'+str(i)+'=np.dot(np.diag(r_coefs.flatten()),x'+str(i)+')'#ri=diag(r_coefs)*xi     # XXX: ERASE
    exec 'Tw'+str(i)+'=np.zeros((1,'+str(NBR_sectors)+'))'#initialise an array of zeros for the Total emissions. Remember that NBR_sectors has extra number. # XXX: ERASE
    exec 'f'+str(i)+'_array=f'+str(i)+'.reshape((NBR_sectors,1))'# will be hstacked later with emission vectors # XXX: ERASE
    for j in range(NBR_disposals): # XXX: ERASE
        exec "w"+str(j)+str(i)+"=np.dot(E"+str(j)+",x"+str(i)+')'#calculate each emission type wji - w_emType_Prod_struct # XXX: ERASE
        exec 'Tw'+str(i)+'+=w'+str(j)+str(i)#calculate the total emissions for the production structure Twi # XXX: ERASE
        exec 'f'+str(i)+'_array=np.hstack([f'+str(i)+'_array,w'+str(j)+str(i)+'.reshape((NBR_sectors,1))])' # XXX: ERASE
    if NBR_disposals == 0: # XXX: ERASE
        exec 'w'+str(i)+'_array= w0'+str(i)+'.reshape(('+str(NBR_sectors)+',1))' # XXX: ERASE
    elif NBR_disposals > 0: # XXX: ERASE
        exec 'w'+str(i)+'_array= w0'+str(i)+'.reshape(('+str(NBR_sectors)+',1))' # XXX: ERASE
        for p in range(NBR_disposals-1): # XXX: ERASE
            exec 'w'+str(i)+'_array= np.hstack([w'+str(i)+'_array, # XXX: ERASE w'+str(p+1)+str(i)+'.reshape(('+str(NBR_sectors)+',1))])'        # XXX: ERASE
    exec "Z"+str(i)+"=np.dot(A,np.diag(x"+str(i)+".flatten()))" # XXX: ERASE
    exec 'To'+str(i)+'=Tw'+str(i)+'+f'+str(i)#calculate total external outputs (emissions+final goods) # XXX: ERASE


# now all product-based structures will be stored within product_based_structures
# each product-based structure entails: r, Z, f, wi, x
product_based_structures=dict()
for sector_index in range(NBR_sectors):
    tmp_structure=dict()
    tmp_structure['fd']=np.zeros(NBR_sectors)
    tmp_structure['fd'][sector_index]=1
    tmp_structure['fd']=tmp_structure['fd'].reshape((NBR_sectors,1))
    tmp_structure['x']=np.dot(actual_structure_dictionary['L'],tmp_structure['fd'])
    tmp_structure['r']=np.dot(np.diag(actual_structure_dictionary['r_coefs'].flatten()),tmp_structure['x'])
    tmp_structure['tot_final_outputs']=tmp_structure['fd']
    for waste_index in range(NBR_disposals):
        tmp_structure['w'+str(waste_index)]=np.dot(actual_structure_dictionary['E'+str(waste_index)],tmp_structure['x'])
        tmp_structure['tot_final_outputs']=tmp_structure['tot_final_outputs']+tmp_structure['w'+str(waste_index)]
    tmp_structure['Z']=np.dot(actual_structure_dictionary['A'],np.diag(tmp_structure['x'].flatten()))
    product_based_structures['prod_based_struct_'+str(sector_index)]=tmp_structure

##############################################################################
#############################################################################
######  Structural analyses ##########################################
# name              description of the calculated variables
# --------    meso economic ------
# eff_all_i         sectoral efficiency of the whole economy for sector i
# eff_j_i           sectoral efficiency for production structure j for sector i
# --------  top-level macro economic -------
# tot_res_eff_all       resource efficienct for the whole economy
# tot_res_eff_i         resource efficienct for prod struct i
# tot_res_int_all       resource intensity for the whole economy (1/tot_res_eff_all)
# tot_res_int_i         resource intensity for prod struct i (1/tot_res_eff_i)
# tot_em_int_all    total emission intensity (sum of all emissions)
# tot_em_int_i      total emission intensity (sum of all emissions) for each production structure
# --------  macro economic -------
# em_int_i_all      total emission intensity of emission-type i
# em_int_i_all_j      total emission intensity of emission-type i sector j
# em_int_i_j        total emission intensity of emission-type i  for production structure j


#### Meso-economic efficiencies (same for all prod struct) ####
print('\n')
print(
'+++++++  FINDING SECTORAL EFFICIENCIES (Meso-economic efficiencies)  ++++++++'
)

##for the whole economy # XXX: ERASE

list_sectoral_eff_vars=[] # XXX: ERASE
#   name and description of the calculated variables # XXX: ERASE
#eff_all_i  efficiency of sector i,  defined as intermediate output + final outputs divided by intermediate inputs plus raw inputs. 
for i in range(NBR_sectors): # XXX: ERASE
    #eff=(sum(Z(row i))+f(i))/((Z(column i)+r(i)) # XXX: ERASE
    exec "eff_all_"+str(i)+"=(sum(Z_array["+str(i)+",:])+fd_all.flatten()["+str(i)+"])/(sum(Z_array[:,"+str(i)+"])+r_array.flatten()["+str(i)+"])" # XXX: ERASE
    list_sectoral_eff_vars.append(eval("eff_all_"+str(i))) # XXX: ERASE
list_sectoral_eff_vars = np.array(list_sectoral_eff_vars) # XXX: ERASE

meso_efficiencies=np.zeros(NBR_sectors)
for i in range(NBR_sectors):
    meso_efficiencies[i]=(sum(actual_structure_dictionary['Z'][i,:])+actual_structure_dictionary['fd'].flatten()[i])/(sum(actual_structure_dictionary['Z'][:,i])+actual_structure_dictionary['r'].flatten()[i])

## Meso efficiencies for each production structure # XXX: ERASE
#eff_j_i  production structure of sector j, efficiency of sector i,  defined as intermediate output + final outputs divided by intermediate inputs plus raw inputs. # XXX: ERASE
## IMPORTANT: this is worthless because the sectoral efficiencies are the same in all the production structures!!! but anyway.. it is done. # XXX: ERASE
for prod_struct in range(NBR_sectors): # XXX: ERASE
    exec 'list_sectoral_eff_vars_'+str(prod_struct)+'=[]' # XXX: ERASE
    for i in range(NBR_sectors): # XXX: ERASE
        #intuitive definition: eff=(sum(Z(row i))+f(i))/((Z(column i)+r(i)) # XXX: ERASE
        exec "eff_"+str(prod_struct)+"_"+str(i)+"=(sum(Z"+str(prod_struct)+"["+str(i)+",:])+f"+str(prod_struct)+".flatten()["+str(i)+"])/(sum(Z"+str(prod_struct)+"[:,"+str(i)+"])+r"+str(prod_struct)+".flatten()["+str(i)+"])"
        exec 'list_sectoral_eff_vars_'+str(prod_struct)+'.append(eval("eff_"+str(prod_struct)+"_"+str(i)))' # XXX: ERASE
    exec 'list_sectoral_eff_vars_'+str(prod_struct)+'=np.array(list_sectoral_eff_vars_'+str(prod_struct)+')' # XXX: ERASE

print('The sectoral efficiencies have been calculated individually but they should be the same in every production structure') # XXX: ERASE

#### TOP-LEVEL MACRO INDICATORS ####

## resource efficiencies, intensities and emission intensity for the whole economy
#
tot_res_eff_all=np.sum(fd_all.flatten())/np.sum(r_array.flatten()) # XXX: ERASE
tot_res_int_all=1/tot_res_eff_all # XXX: ERASE

actual_structure_dictionary['tot_res_eff']=sum(actual_structure_dictionary['fd'].flatten())/sum(actual_structure_dictionary['r'].flatten())
actual_structure_dictionary['tot_res_int']=1/tot_res_eff_all/actual_structure_dictionary['tot_res_eff']

#for each prod struct # XXX: ERASE
for prod_struct in range(NBR_sectors): # XXX: ERASE
    exec 'tot_res_eff_'+str(prod_struct)+'=np.sum(f'+str(prod_struct)+'.flatten())/np.sum(r'+str(prod_struct)+'.flatten())' # XXX: ERASE
    exec 'tot_res_int_'+str(prod_struct)+'=1/tot_res_eff_'+str(prod_struct) # XXX: ERASE

## TOP-LEVEL Emission intensities 
#for the whole economy
tot_em_int_all=(np.sum(f_array.flatten())-np.sum(fd_all.flatten()))/np.sum(fd_all.flatten()) # XXX: ERASE

actual_structure_dictionary['tot_em_int']=0
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['tot_em_int']=actual_structure_dictionary['tot_em_int']+sum(actual_structure_dictionary['w'+str(waste_index)].flatten())/sum(actual_structure_dictionary['r'].flatten())


for prod_struct in range(NBR_sectors): # XXX: ERASE
    exec 'tot_em_int_'+str(prod_struct)+'=np.sum(Tw'+str(prod_struct)+'.flatten())/np.sum(f'+str(prod_struct)+'.flatten())' # XXX: ERASE

# and for each prod struct

for sector_index in range(NBR_sectors):
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_eff']=sum(product_based_structures['prod_based_struct_'+str(sector_index)]['fd'].flatten())/sum(product_based_structures['prod_based_struct_'+str(sector_index)]['r'].flatten())
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_int']=1/product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_eff']
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int']=0
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int']=product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int']+sum(product_based_structures['prod_based_struct_'+str(sector_index)]['w'+str(waste_index)].flatten())/sum(product_based_structures['prod_based_struct_'+str(sector_index)]['r'].flatten())

#### MACRO INDICATORS #### 
# NOTE: I do not need to calculate them since they do not make sense for the actual structure
# and they are given by the product-based decomposition in case of each product-based.

##resource intensity of each sector for all production
res_int_all=r_array.flatten()/np.sum(fd_all.flatten()) # XXX: ERASE

for prod_struct in range(NBR_sectors): # XXX: ERASE
    exec 'res_eff_'+str(prod_struct)+'=r'+str(prod_struct) # XXX: ERASE
## Emission intensities for each emission type # XXX: ERASE
#for the whole economy # XXX: ERASE
for waste_index in range(NBR_disposals): # XXX: ERASE
    exec 'em_int_'+str(waste_index)+'_all = np.sum(w'+str(waste_index)+'_all.flatten()) / np.sum(fd_all.flatten())' # XXX: ERASE
    for sector in range(NBR_sectors): # XXX: ERASE
        exec 'em_int_'+str(waste_index)+'_all_'+str(sector)+' = w'+str(waste_index)+'_all.flatten()['+str(sector)+'] / np.sum(fd_all.flatten())' # XXX: ERASE
        
#for each prod struct. REMEMBER:  wji type-j emissions generated to satisfy fi # XXX: ERASE
for prod_struct in range(NBR_sectors): # XXX: ERASE
    for waste_index in range(NBR_disposals): # XXX: ERASE
        exec 'em_int_'+str(waste_index)+'_'+str(prod_struct)+' =  np.sum(w'+str(waste_index)+str(prod_struct)+'.flatten()) / np.sum(f'+str(prod_struct)+'.flatten())'     # XXX: ERASE
#    exec 'tot_em_int_'+str(prod_struct)+'=np.sum(Tw'+str(prod_struct)+'.flatten())/np.sum(f'+str(prod_struct)+'.flatten())' # XXX: ERASE



##############################################################################
#### Cycle decomposition of all flow   ###################################################

print('\n ++++++++++ CYCLE DECOMPOSITION OF THE ORIGINAL PIOT ++++++++++++++++') # XXX: ERASE
print('\n ++++++ CYCLIC-ACYCLIC/DIRECT-INDIRECT DECOMPOSITION OF ALL PRODUCT-BASED STRUCTURES +++++++++')


for struct_index in range(NBR_sectors):
    print('\n +++++ Started structural decomposition for product-based structure'+str(struct_index)+' +++++')
    print('\n +++ Decomposing Z between Zc and Zind +++')
    # finding Zc and Zind
    [product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'], product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'], product_based_structures['prod_based_struct_' +str(struct_index)]['self_cycling']] = cd.cycle_decomposition(product_based_structures['prod_based_struct_'+str(struct_index)]['Z'].__copy__(), product_based_structures['prod_based_struct_'+str(struct_index)]['tot_final_outputs'].__copy__())
    # finding cycling throughput (1xn)
    product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'] = [np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'],1)]
    

    print('\n +++ Finding the indirect-cyclic and indirect-acyclic structures +++')
    print('\n + Decomposing Zind between Zind,c and Zind,ac +')
    prop_c=np.zeros((1,3))
    prop_f=np.zeros((1,3))
    prop_z=np.zeros((1,3))
    for sector_index in range(NBR_sectors):
        prop_c[0][sector_index]= product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][0][sector_index] / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][0][sector_index])
        prop_f[0][sector_index]= product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][0][sector_index])
        prop_z[0][sector_index]= np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][0][sector_index])
    # finding proportion for acyclic flows
    prop_ac=prop_f+prop_z
    # using the proportions to find Zind_c and Zind_ac
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c'] = np.dot(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'],np.diag(prop_c.flatten()))
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac'] = np.dot(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'],np.diag(prop_ac.flatten()))

    print('\n + Calculating rind_ac  +')
    # finding rind_ac: rind_ac = (Zind . i + f ) . <meso_efficiencies>^(-1) - i . Zind,ac
    product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac'] = np.dot(
    (    np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'],1) + product_based_structures['prod_based_struct_'+str(struct_index)]['fd'].flatten())
    ,LA.inv(np.diag(meso_efficiencies))
    ) - np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac'],0)

    print('\n + Calculating find  +')
    # finding find
    product_based_structures['prod_based_struct_'+str(struct_index)]['find'] = np.dot(
    np.dot(
    np.diag(meso_efficiencies),
    np.diag(np.dot(np.ones(NBR_sectors),
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac']
    ))),
    product_based_structures['prod_based_struct_'+str(struct_index)]['fd'])

    print('\n + Decomposing Zind,ac between Zind,ac,a and Zind,ac,c and finding rind,ac,a and rind,ac,c +')
    [product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_a'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_c'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c']] = backward_trace.main(
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['find'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac'],
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c'])







print('\n +++ creating cycling indicators +++')
# name                          description of the calculated variables
# ---- Indicators of cyclic component ----
# cycling_throughput_all        cycling throughput (self+inter) that goes through each sector  [nx1]
# self_cycling_all              self-cycling throughput of each sector  [nx1]
# inter_cycling_all             inter-cycling throughput that goes through each sector  [nx1]
# tot_cycling_throughput_all    total cycling throughput of the system [1x1]
# tot_self_cycling_all          total self-cycling throughput of the system [1x1]
# tot_inter_cycling_all         total inter-cycling throughput of the system [1x1]

# ---- Indicators of feeding flows (inputs) to maintain the cyclic component ----
# feeding_flows_all                 inputs required to maintain the cycling throughput (self+inter) [nx1]
# self_cycling_feeding_flows_all    inputs required to maintain the self-cycling throughput of each sector  [nx1]
# inter_cycling_feeding_flows_all   the inputs required to maintain the inter-cycling throughput of each sector  [nx1]
# tot_feeding_flows_all             total inputs required to maintain the cycling throughput (self+inter) of the system [1x1]
# tot_self_cycling_feeding_flows_all    total inputs required to maintain the self-cycling throughput of the system [1x1]
# tot_inter_cycling_feeding_flows_all   total inputs required to maintain the inter-cycling throughput of the system [1x1]

# ---- Indicators on straight inputs that generate the acyclic component --------
# raw_straight_inputs_all       raw inputs required to feed the acyclic flows including final goods plus the acyclic component of production structure (=raw inputs - feeding_flows_all ) [nx1]
# 
# tot_raw_straight_inputs_all   total raw inputs required to feed the acyclic flows of the system including final goods plus the acyclic component of production structure (=raw inputs - feeding_flows_all ) [1x1]
# tot_intermediate_straight_inputs_all total intermediate inputs due to acyclic component of production structure  of the system (=raw inputs - feeding_flows_all ) [1x1]
# tot_straight_inputs_all           equal to tot_raw_straight_inputs_all [1x1]

# ---- Indicators of final demand due to indirect and direct acyclic flows ----
# indirect_fd_all       fd produced by indirect flows [nx1]
#direct_fd_all          fd produced by direct flows [nx1]
#tot_indirect_fd_all    total fd produced by indirect flows  [1x1]
#tot_direct_fd_all      total fd produced by direct flows [1x1]


# ---- Indicators of cycling losses due to the cyclic component and corresponding cyclic inputs----
# cycling_losses_all        system outputs due to maintaining all cycling (self + inter) (= feeding_flows_all)  [nx1]
# self_cycling_losses_all   system outputs due to maintaining self-cycling (= self_cycling_feeding_flows_all) [nx1]
# inter_cycling_losses_all  system outputs due to maintaining inter-cycling (= inter_cycling_feeding_flows_all) [nx1]
# tot_cycling_losses_all        system outputs due to maintaining all cycling (self + inter) (= tot_feeding_flows_all)  [1x1]
# tot_self_cycling_losses_all   system outputs due to maintaining self-cycling (= tot_self_cycling_feeding_flows_all) [1x1]
# tot_inter_cycling_losses_all  system outputs due to maintaining inter-cycling (= tot_inter_cycling_feeding_flows_all) [1x1]

# ---- Indicators of straight losses due to the acyclic component and corresponding straight inputs----
# fd_straight_losses_all        =straight_losses_all but also =raw_straight_inputs_all*(1-list_sectoral_eff_vars) [nx1]
# indirect_acyclic_losses_all      emissions due to all acyclic indirect flows  [nx1]
# straight_losses_all                system output due to all straight flows (=fd_straight_losses_all OR =total_losses-cycling_losses_all) [nx1]
# tot_fd_straight_losses_all   =straight_losses_all but also =raw_straight_inputs_all*(1-list_sectoral_eff_vars) [1x1]
# tot_intermediate_straight_losses_all system output due to all intermediate flows only which are the acyclic component [1x1]
# tot_straight_losses_all           system output due to all straight flows (=fd_straight_losses_all OR =total_losses-cycling_losses_all) [1x1]

# total_losses_all                  total losses due to straight and cycling (=system_outputs-final goods)
# tot_total_losses_all              total of total losses due to straight and cycling (=system_outputs-final goods)

# ---- Indicators of the system throughput due to cyclic and acyclic components ----
# total_cycling_output_all          total throughput due to cycling  [nx1]
# total_straight_output_all         total throughput due to straight flows (inter+final goods+ emission) [note that the emissions are calculated from raw_inputs only] [nx1]
#total_self_cycling_output_all total throughput due to self-cycling [nx1]
#total_inter_cycling_output_all total throughput due to inter-cycling [nx1]
#total_direct_acyclic_output_all total throughput due to direct acyclic flows [nx1]
#total_indirect_acyclic_output_all total throughput due to indirect acyclic flows [nx1]
# tot_total_cycling_output_all      total of total throughput due to cycling (self+inter+losses) [1x1]
# tot_total_straight_output_all     total of total throughput due to straight flows (inter+final goods+emission) [1x1]


# --- emissions part due to SC, IC, IA, DA
# w_i_SC_all  is the emission vector of emission i due to SC
# w_i_IC_all  is the emission vector of emission i due to SC
# w_i_IA_all  is the emission vector of emission i due to SC
# w_i_DA_all  is the emission vector of emission i due to SC




#the inter-secoral matrix is decomposed between its cyclic and acyclic components in the cd.cycle_decomposition function, which returns its cyclic [nxn], acyclic [nxn] and self-loop components [1xn]

####################################################################
##  IMPORTANT NOTE ON MODIFYING VARIABLES IN SUB-FUNCTIONS 
## : assigning is not copying, so if I enter a value in a funtion and modify it within the funcion, it will be modified directly at the root where the assignment was made. To avoid that I need to ***pass a copy*** of the array, ***not an assignment*** of it. Note that this has nothing to do with local or global vars. 
## THE cd.cycle_decomposition function is an example because it modifies the array by subtracting the diagonal from it
#####################################################################
[Z_array_cyclic,Z_array_acyclic,self_cycling_all]=cd.cycle_decomposition(Z_array.__copy__(), f_array.__copy__())
self_cycling_all=self_cycling_all.flatten() # XXX: ERASE

#Indicators of cyclic component
cycling_throughput_all= np.sum(Z_array_cyclic,axis=1) # XXX: ERASE
inter_cycling_all=cycling_throughput_all-self_cycling_all # XXX: ERASE
tot_cycling_throughput_all = np.sum(cycling_throughput_all.flatten()) # XXX: ERASE
tot_self_cycling_all = np.sum(self_cycling_all.flatten()) # XXX: ERASE
tot_inter_cycling_all = np.sum(inter_cycling_all.flatten()) # XXX: ERASE
Z_array_self_cycling=np.diag(self_cycling_all) # XXX: ERASE
Z_array_inter_cycling=Z_array_cyclic-Z_array_self_cycling # XXX: ERASE


#Indicators derived from indicators of cyclic component
feeding_flows_all = []
self_cycling_feeding_flows_all = []
inter_cycling_feeding_flows_all = []
for i in range(NBR_sectors):#I could have done this in matricial notation
    feeding_flows_all.append(cycling_throughput_all[i] * (1 - list_sectoral_eff_vars[i]) / list_sectoral_eff_vars[i])
    self_cycling_feeding_flows_all.append(self_cycling_all[i] * (1 - list_sectoral_eff_vars[i]) / list_sectoral_eff_vars[i])
    inter_cycling_feeding_flows_all.append(inter_cycling_all[i] * (1 - list_sectoral_eff_vars[i]) / list_sectoral_eff_vars[i])

feeding_flows_all = np.array(feeding_flows_all)
self_cycling_feeding_flows_all = np.array(self_cycling_feeding_flows_all)
inter_cycling_feeding_flows_all = np.array(inter_cycling_feeding_flows_all)
tot_feeding_flows_all = np.sum(feeding_flows_all)
tot_self_cycling_feeding_flows_all = np.sum(self_cycling_feeding_flows_all)
tot_inter_cycling_feeding_flows_all = np.sum(inter_cycling_feeding_flows_all)

# Indicators on acyclic inputs
raw_straight_inputs_all = r_array.flatten()-feeding_flows_all
intermediate_production_all = np.sum(Z_array_acyclic, axis=1)
intermediate_use_all= np.sum(Z_array_acyclic, axis=0)
# I originally had LA.inv(np.diag(fd_all.flatten()+intermediate_production_all)) 
# which led to error when some value fd_all.flatten()+intermediate_production_all =0
# I just needed the inverse for the values neq to 0
frac_interm_prod_over_tot_prod=[]
for x in fd_all.flatten()+intermediate_production_all:
    if x == 0:
        frac_interm_prod_over_tot_prod.append(0)
    elif x > 0:
        frac_interm_prod_over_tot_prod.append(1/x)
frac_interm_prod_over_tot_prod=np.array(frac_interm_prod_over_tot_prod)
# TODO: add change to product-based structures
# TODO: solve new problem: for sparse matrices (e.g. ulanowicz), some inter use is greater than
# inter prod leading to negative values in indirect acyclic resources 
raw_indirect_straight_inputs_all =np.dot(LA.inv(np.diag(list_sectoral_eff_vars)),intermediate_production_all)-np.dot(np.diag(np.dot(np.diag(frac_interm_prod_over_tot_prod),intermediate_production_all)),intermediate_use_all)
#raw_indirect_straight_inputs_all = np.dot(LA.inv(np.diag(list_sectoral_eff_vars)), intermediate_production_all) -np.dot(np.diag(np.dot(LA.inv(np.diag(fd_all.flatten() + intermediate_production_all)), intermediate_production_all)), intermediate_use_all)
raw_direct_straight_inputs_all =raw_straight_inputs_all-raw_indirect_straight_inputs_all 


tot_raw_straight_inputs_all = np.sum(raw_straight_inputs_all)
tot_raw_indirect_straight_inputs_all = np.sum(raw_indirect_straight_inputs_all)
tot_raw_direct_straight_inputs_all = np.sum(raw_direct_straight_inputs_all)
#remember that the total raw inputs (cyclic+acyclic) are the r_array

# ---- Indicators of final demand due to indirect and direct acyclic flows ----
indirect_fd_all=np.dot(np.diag(np.dot(np.diag(np.dot(LA.inv(np.diag(fd_all.flatten()+intermediate_production_all)),fd_all.flatten())),intermediate_use_all)),list_sectoral_eff_vars)
direct_fd_all=fd_all.flatten()-indirect_fd_all
tot_indirect_fd_all=np.sum(indirect_fd_all)
tot_direct_fd_all=np.sum(direct_fd_all)


# ---- Indicators of emissions due to the cyclic component ----
# XXX: TODO I always worked with one emission type so I used to say that cyclic emissions = resource for cycling but
# the issue is that the repartition of those losses amongst the differerent emission types is unknow...
# I guess the way forward is to calculate the total_outputs or inputs due to the cycling component and then
# calculate the emissions components. I had completely forgot about that.
cycling_losses_all=feeding_flows_all
self_cycling_losses_all = self_cycling_feeding_flows_all
inter_cycling_losses_all = inter_cycling_feeding_flows_all
tot_cycling_losses_all = tot_feeding_flows_all
tot_self_cycling_losses_all = tot_self_cycling_feeding_flows_all
tot_inter_cycling_losses_all = tot_inter_cycling_feeding_flows_all

# ---- Indicators of emissions due to the acyclic component ----
indirect_acyclic_losses_all=np.dot(np.eye(NBR_sectors)-np.diag(list_sectoral_eff_vars),raw_indirect_straight_inputs_all+intermediate_use_all)
acyclic_losses_all = np.sum(f_array, axis=1) - fd_all.flatten()- cycling_losses_all
direct_acyclic_losses_all = acyclic_losses_all - indirect_acyclic_losses_all

tot_direct_acyclic_losses_all = np.sum(direct_acyclic_losses_all)
tot_straight_losses_all = np.sum(acyclic_losses_all)
tot_indirect_acyclic_losses_all = np.sum(indirect_acyclic_losses_all)

#total losses (cycling+straight) [for each prod struc I will need to iterate?]
total_losses_all = np.sum(f_array, axis=1).flatten()-fd_all.flatten()
tot_total_losses_all=np.sum(total_losses_all)

# ---- Indicators of the total outputs due to cyclic and acyclic components ----
# WITH THIS TOTAL OUTPUTS I CAN CALCULATE THEIR RESPECTIVE COMPONENT IN THE EMISSIONS.
# aggregated: cyclic-acyclic
total_cycling_output_all=cycling_losses_all+np.sum(Z_array_cyclic, axis=1)
total_straight_output_all=fd_all.flatten()+acyclic_losses_all+np.sum(Z_array_acyclic, axis=1)
tot_total_cycling_output_all = np.sum(total_cycling_output_all)
tot_total_straight_output_all = np.sum(total_straight_output_all)

# disaggregated SC, IC, IA, DA
total_self_cycling_output_all = self_cycling_all +self_cycling_feeding_flows_all
total_inter_cycling_output_all = inter_cycling_all + inter_cycling_feeding_flows_all
total_direct_acyclic_output_all = direct_acyclic_losses_all + direct_fd_all
total_indirect_acyclic_output_all = intermediate_production_all + indirect_fd_all + indirect_acyclic_losses_all

# --- emissions part due to SC, IC, IA, DA
# w_i_SC_all  is the emission vector of emission i due to SC
# w_i_IC_all  is the emission vector of emission i due to SC
# w_i_IA_all  is the emission vector of emission i due to SC
# w_i_DA_all  is the emission vector of emission i due to SC
for i in range(NBR_disposals):
    exec 'w_'+str(i)+'_SC_all=np.dot(E'+str(i)+',total_self_cycling_output_all).reshape((NBR_sectors,1))'
    exec 'w_'+str(i)+'_IC_all=np.dot(E'+str(i)+',total_inter_cycling_output_all).reshape((NBR_sectors,1))'
    exec 'w_'+str(i)+'_IA_all=np.dot(E'+str(i)+',total_indirect_acyclic_output_all).reshape((NBR_sectors,1))'
    exec 'w_'+str(i)+'_DA_all=np.dot(E'+str(i)+',total_direct_acyclic_output_all).reshape((NBR_sectors,1))'
    
#create arrays with all emissions
w_array_SC_all=w_0_SC_all.reshape((NBR_sectors,1))
w_array_IC_all=w_0_IC_all.reshape((NBR_sectors,1))
w_array_IA_all=w_0_IA_all.reshape((NBR_sectors,1))
w_array_DA_all=w_0_DA_all.reshape((NBR_sectors,1))
#pdb.set_trace()
for i in range(NBR_disposals-1):
    exec 'w_array_SC_all= np.hstack((w_array_SC_all,w_'+str(i+1)+'_SC_all))'
    exec 'w_array_IC_all= np.hstack((w_array_IC_all,w_'+str(i+1)+'_IC_all))'
    exec 'w_array_IA_all= np.hstack((w_array_IA_all,w_'+str(i+1)+'_IA_all))' 
    exec 'w_array_DA_all= np.hstack((w_array_DA_all,w_'+str(i+1)+'_DA_all))'   
  

#print to log
print('\n The cycling_throughput_all of each sector is:\n '+str(cycling_throughput_all))
print('\n The total_inputs are:\n '+str(total_inputs))
print('\n The feeding_flows_all (inputs) to maintain the cycles are:\n '+str(feeding_flows_all))
print('\n The raw_straight_inputs_all (inputs) that are used are :\n '+str(raw_straight_inputs_all))
print('\n The total_losses (or emissions) are:\n '+str(total_losses_all))
print('\n The cycling_losses_all due to cycling are:\n '+str(cycling_losses_all))
print('\n The straight_losses_all due to straight flows are:\n '+str(acyclic_losses_all))
print('\n The total_cycling_output_all due to cycling is:\n '+str(total_cycling_output_all))
print('\n The total_straight_output_all due to straight flows is:\n '+str(total_straight_output_all))



###############################################################################
################ DRAWING CIRCOS DIAGRAM #####################################
#==============================================================================
# def draw_circos_diagram(circos_execute, circos_open_images, diagram_type, scale_type, flow_type, ribbon_order, directory, data_filename, nbr_sectors, nbr_emissions, sector_names, *arrays):
#     '''This is the main function which takes the options for drawing the diagram, it will call sub-functions accordingly.
#     
#     the arguments options for the configuration of the diagram are
#     - unit:   [integer] number by which you multiplied the structure to avoid decimal positions because circos cannot draw them.
#     - diagram_type: merged or symmetrical
#     - scale_type: normalised or non_normalised
#     - flow_type: sector_outputs, sector_inputs, cyclic_acyclic
#     - ribbon_order: size_asc, size_desc or native (same as in circos)
#     other options 
#     - directory: path where the config, data and image files are put, creates etc, data and img subfolders
#     the data passed to draw the diagram is
#     - nbr_sectors [integer]
#     - nbr_emissions [integer]
#     - sector_names [array containing sector names in the same order as in the other arrays]
#     - arrays: always in blocks of 4 with strict order: intersectoral_matrix [nbr_sectors x nbr_sectors],  primary_inputs[1 x nbr_sectors], final_goods [nbr_sectors x 1], emission_matrix [nbr_sectors x nbr_emissions]. By doing that the subroutine is flexible to calculate any kind of flow-type decomposition.
#    '''
#==============================================================================
#===========arrays to pass for SC, IC, IA and DA structures====================
# Z_array_self_cycling
# self_cycling_feeding_flows_all #self-cyclic resources
# np.zeros((1,NRB_sectors)) # the fd of self-cycling =0
# w_array_SC_all # the emissions matrix 
# 
# Z_array_inter_cycling
# inter_cycling_feeding_flows_all #inter-cyclic resources
# np.zeros((NRB_sectors,NRB_sectors)) # the fd of inter-cycling =0
# w_array_IC_all# the emissions matrix 
# 
# Z_array_acyclic # the indirect acyclic  array is the Z_array_acyclic
# raw_indirect_straight_inputs_all #indirect-acyclic resources
# indirect_fd_all # fd for indirect acyclic
# w_array_IA_all # emissions for indirect acyclic
# 
# 
# np.zeros((NRB_sectors,NRB_sectors)) # the direct acyclic  array is a zero array
# raw_direct_straight_inputs_all #  direct acyclic resources
# direct_fd_all # fd for direct acyclic
# w_array_DA_all # emissions for direct acyclic
#==============================================================================

#XXX: todo: current ribbon ordering is output based. It would be nice to have it also input-based.

if circos_draw:
    #### CircosFolder: where you want to put the circos drawings
    CircosFolder=os.path.join(dirPath,'circos_graphs_' + time_at_start + '_' + data_filename + '_full_structure')
    os.chdir(dirPath)
    if os.path.split(CircosFolder)[1] not in os.listdir('./'):
        #CHECK IF DIRECTORY EXISTS. IF not, create it.
        os.mkdir(CircosFolder)    
    
    unit=1

# STOPPED: check whether I included circos_execute,circos_open_images in the production structures and make the corresponding amendments in the draw_circos_diagram function

    #circos interface for flow_by_sector: sector_outputs or sector inputs
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'merged', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers['column headings'], Z_array, r_array, fd_all, w_all)
    
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers['column headings'], Z_array, r_array, fd_all, w_all)
    
    # circos interface for flow_by_type: cyclic_acyclic
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'merged', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers['column headings'], Z_array_self_cycling, self_cycling_feeding_flows_all.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_SC_all, Z_array_inter_cycling, inter_cycling_feeding_flows_all.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_IC_all, Z_array_acyclic, raw_indirect_straight_inputs_all.reshape((1,NBR_sectors)), indirect_fd_all.reshape((NBR_sectors,1)) , w_array_IA_all, np.zeros((NBR_sectors,NBR_sectors)), raw_direct_straight_inputs_all.reshape((1,NBR_sectors)), direct_fd_all.reshape((NBR_sectors,1)), w_array_DA_all)
    
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers['column headings'], Z_array_self_cycling, self_cycling_feeding_flows_all.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_SC_all, Z_array_inter_cycling, inter_cycling_feeding_flows_all.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_IC_all, Z_array_acyclic, raw_indirect_straight_inputs_all.reshape((1,NBR_sectors)), indirect_fd_all.reshape((NBR_sectors,1)) , w_array_IA_all, np.zeros((NBR_sectors,NBR_sectors)), raw_direct_straight_inputs_all.reshape((1,NBR_sectors)), direct_fd_all.reshape((NBR_sectors,1)), w_array_DA_all)


#### Draw the sankey diagram for each piot #####################################
#it will save the created drawing as png
#draw_sankeys.sankey_of_cyclic_flows(units, title, NBR_sectors, total_inputs, feeding_flows_all, raw_straight_inputs_all, total_losses_all, cycling_losses_all, acyclic_losses_all, fd_all, Z_array_cyclic, Z_array_acyclic, self_cycling_all,  Images_Path, 'sankey.cycles.all.'+output_filename)




##############################################################################
#### Cycle decomposition of EACH PRODUCTION STRUCTURE   ###################################################

for prod_struct in range(NBR_sectors):
    print('\n ++++++++++ CYCLE DECOMPOSITION OF THE PRODUCTION STRUCTURE OF PRODUCT '+str(prod_struct)+'  ++++++++++++++++')
    #the inter-secoral matrix is decomposed between its cyclic and acyclic components in the cd.cycle_decomposition function, which returns its cyclic [nxn], acyclic [nxn] and self-loop components [1xn]
    exec '[Z_array_cyclic_'+str(prod_struct)+' ,Z_array_acyclic_'+str(prod_struct)+' ,self_cycling_'+str(prod_struct)+']=cd.cycle_decomposition(Z'+str(prod_struct)+'.__copy__(), f'+str(prod_struct)+'_array.__copy__())'
    exec 'self_cycling_'+str(prod_struct)+'= self_cycling_'+str(prod_struct)+'.flatten()'   
    
    print('\n +++ creating cycling indicators +++')
    #this indicators are explained in the previous section.

    #Indicators of cyclic component
    exec 'cycling_throughput_'+ str(prod_struct)+ ' = np.sum(Z_array_cyclic_'+ str(prod_struct)+ ',axis=1)'
    exec 'inter_cycling_'+ str(prod_struct)+ '=cycling_throughput_'+ str(prod_struct)+ '-self_cycling_'+ str(prod_struct)
    exec 'tot_cycling_throughput_'+ str(prod_struct)+ ' = np.sum(cycling_throughput_'+ str(prod_struct)+ '.flatten())'
    exec 'tot_self_cycling_'+ str(prod_struct)+ ' = np.sum(self_cycling_'+ str(prod_struct)+ '.flatten())'
    exec 'tot_inter_cycling_'+ str(prod_struct)+ ' = np.sum(inter_cycling_'+ str(prod_struct)+ '.flatten())'
    exec 'Z_array_self_cycling_'+ str(prod_struct)+ ' = np.diag(self_cycling_'+ str(prod_struct)+ ')'
    exec 'Z_array_inter_cycling_'+ str(prod_struct)+ ' = Z_array_cyclic_'+ str(prod_struct)+ '-Z_array_self_cycling_'+ str(prod_struct)
    

    #Inputs derived from indicators of cyclic component

    exec 'feeding_flows_'+ str(prod_struct)+ '=[]'
    exec 'self_cycling_feeding_flows_'+ str(prod_struct)+ ' = []'
    exec 'inter_cycling_feeding_flows_'+ str(prod_struct)+ ' = []'
    for i in range(NBR_sectors):
        exec 'feeding_flows_'+ str(prod_struct)+ '.append(cycling_throughput_'+ str(prod_struct)+ '[i] * (1 - list_sectoral_eff_vars_'+ str(prod_struct)+ '[i]) / list_sectoral_eff_vars_'+ str(prod_struct)+ '[i])'
        exec 'self_cycling_feeding_flows_'+ str(prod_struct)+ '.append(self_cycling_'+ str(prod_struct)+ '[i] * (1 - list_sectoral_eff_vars_'+ str(prod_struct)+ '[i]) / list_sectoral_eff_vars_'+ str(prod_struct)+ '[i])'
        exec 'inter_cycling_feeding_flows_'+ str(prod_struct)+ '.append(inter_cycling_'+ str(prod_struct)+ '[i] * (1 - list_sectoral_eff_vars_'+ str(prod_struct)+ '[i]) / list_sectoral_eff_vars_'+ str(prod_struct)+ '[i])'
    
    exec 'feeding_flows_'+str(prod_struct)+'=np.array(feeding_flows_'+str(prod_struct)+')'
    exec 'self_cycling_feeding_flows_'+str(prod_struct)+' = np.array(self_cycling_feeding_flows_'+str(prod_struct)+')'
    exec 'inter_cycling_feeding_flows_'+str(prod_struct)+' = np.array(inter_cycling_feeding_flows_'+str(prod_struct)+')'
    
    exec 'tot_feeding_flows_'+str(prod_struct)+' = np.sum(feeding_flows_'+str(prod_struct)+')'
    exec 'tot_self_cycling_feeding_flows_'+str(prod_struct)+' = np.sum(self_cycling_feeding_flows_'+str(prod_struct)+')'
    exec 'tot_inter_cycling_feeding_flows_'+str(prod_struct)+' = np.sum(inter_cycling_feeding_flows_'+str(prod_struct)+')'

    # Indicators on acyclic inputs
    exec 'intermediate_production_'+str(prod_struct)+' = np.sum(Z_array_acyclic_'+str(prod_struct)+', axis=1)'
    exec 'intermediate_use_'+str(prod_struct)+' = np.sum(Z_array_acyclic_'+str(prod_struct)+', axis=0)'
    exec 'raw_indirect_straight_inputs_'+str(prod_struct)+' = np.dot(LA.inv(np.diag(list_sectoral_eff_vars_'+ str(prod_struct) + ')) ,intermediate_production_'+ str(prod_struct)+ ' )-np.dot(np.diag(np.dot(LA.inv(np.diag(f'+str(prod_struct) +'+intermediate_production_'+str(prod_struct)+ ')) ,intermediate_production_'+str(prod_struct)+')), intermediate_use_'+str(prod_struct)+ ')'
    exec 'raw_straight_inputs_'+str(prod_struct)+' = r'+str(prod_struct)+'.flatten()-feeding_flows_'+str(prod_struct)
    exec 'raw_direct_straight_inputs_'+str(prod_struct)+' = raw_straight_inputs_'+str(prod_struct)+'-raw_indirect_straight_inputs_'+str(prod_struct) 
    
    exec 'tot_raw_straight_inputs_'+str(prod_struct)+' = np.sum(raw_straight_inputs_'+str(prod_struct)+')'

    exec 'tot_straight_inputs_'+str(prod_struct)+' = tot_raw_straight_inputs_'+str(prod_struct)
    #remember that the total raw inputs (cyclic+acyclic) are the ri vectors
    
    # ---- Indicators of final demand
    exec 'indirect_fd_'+ str(prod_struct)+'=np.dot(np.diag(np.dot(np.diag(np.dot(LA.inv(np.diag(f'+str(prod_struct)+'.flatten()+intermediate_production_'+str(prod_struct)+')),f'+str(prod_struct)+'.flatten())),intermediate_use_'+str(prod_struct)+')),list_sectoral_eff_vars_'+ str(prod_struct)+')'
    exec 'direct_fd_'+ str(prod_struct)+'=f'+str(prod_struct)+'-indirect_fd_'+ str(prod_struct)
    


    # ---- Indicators of cycling emissions ----
    exec 'cycling_losses_'+ str(prod_struct)+'=feeding_flows_'+str(prod_struct)
    exec 'self_cycling_losses_'+ str(prod_struct)+' = self_cycling_feeding_flows_'+str(prod_struct)
    exec 'inter_cycling_losses_'+ str(prod_struct)+' = inter_cycling_feeding_flows_'+str(prod_struct)
    exec 'tot_cycling_losses_'+ str(prod_struct)+' = tot_feeding_flows_'+str(prod_struct)
    exec 'tot_self_cycling_losses_'+ str(prod_struct)+' = tot_self_cycling_feeding_flows_'+str(prod_struct)
    exec 'tot_inter_cycling_losses_'+ str(prod_struct)+' = tot_inter_cycling_feeding_flows_'+str(prod_struct)

    # ---- Indicators of acyclic emissions ---- 
    exec 'indirect_acyclic_losses_'+ str(prod_struct)+' =np.dot(np.eye(NBR_sectors)-np.diag(list_sectoral_eff_vars_'+ str(prod_struct)+'),raw_indirect_straight_inputs_'+ str(prod_struct)+'+intermediate_use_'+ str(prod_struct)+')'
    exec 'acyclic_losses_'+ str(prod_struct)+' =np.sum(f'+str(prod_struct)+'_array, axis=1)- f'+str(prod_struct)+'.flatten()- cycling_losses_'+ str(prod_struct)
    exec 'direct_acyclic_losses_'+ str(prod_struct)+' =acyclic_losses_'+ str(prod_struct)+'-indirect_acyclic_losses_'+ str(prod_struct)
    
#OBSOLETE
#    exec 'raw_straight_losses_'+ str(prod_struct)+' = raw_straight_inputs_'+ str(prod_struct)+'*(1-list_sectoral_eff_vars_'+ str(prod_struct)+')'
#    exec 'intermediate_straight_losses_'+ str(prod_struct)+' = np.sum(Z_array_acyclic_'+ str(prod_struct)+ ', axis = 0 ) * (1 - list_sectoral_eff_vars_'+ str(prod_struct)+')'
#    exec 'straight_losses_'+ str(prod_struct)+ ' = raw_straight_losses_'+ str(prod_struct)+' + intermediate_straight_losses_'+ str(prod_struct) 
#    
#    exec 'tot_raw_straight_losses_'+ str(prod_struct)+ ' = np.sum(raw_straight_losses_'+ str(prod_struct)+ ')'
#    exec 'tot_straight_losses_'+str(prod_struct)+' = np.sum(straight_losses_'+ str(prod_struct)+ ')'
#    exec 'tot_intermediate_straight_losses_'+ str(prod_struct)+ ' = np.sum(intermediate_straight_losses_'+ str(prod_struct)+ ')'

    #total losses (cycling+straight) [for each prod struc I will need to iterate?]
    exec 'total_losses_'+ str(prod_struct)+ ' = np.sum(f'+ str(prod_struct)+ '_array, axis=1).flatten()-f'+ str(prod_struct)+ '.flatten()'
    exec 'tot_total_losses_'+ str(prod_struct)+ '=np.sum(total_losses_'+ str(prod_struct)+ ')'
    
    # ---- Indicators of the total outputs ----
    exec 'total_cycling_output_'+ str(prod_struct)+ '=cycling_losses_'+ str(prod_struct)+ '+np.sum(Z_array_cyclic_'+ str(prod_struct)+ ', axis=1)'
    exec 'total_straight_output_'+ str(prod_struct)+ '=f'+ str(prod_struct)+ '.flatten()+acyclic_losses_'+ str(prod_struct)+ '+np.sum(Z_array_acyclic_'+ str(prod_struct)+ ', axis=1)'
    exec 'total_self_cycling_output_'+ str(prod_struct)+ '=self_cycling_'+ str(prod_struct)+ '+self_cycling_feeding_flows_'+ str(prod_struct)
    exec 'total_inter_cycling_output_'+ str(prod_struct)+ '=inter_cycling_'+ str(prod_struct)+ '+inter_cycling_feeding_flows_'+ str(prod_struct)
    exec 'total_direct_acyclic_output_'+ str(prod_struct)+ '= direct_acyclic_losses_'+ str(prod_struct)+ '+direct_fd_'+ str(prod_struct)
    exec 'total_indirect_acyclic_output_'+ str(prod_struct)+ '= intermediate_production_'+ str(prod_struct)+ '+indirect_fd_'+ str(prod_struct)+'+indirect_acyclic_losses_'+ str(prod_struct)
    
    
    exec 'tot_total_cycling_output_'+ str(prod_struct)+ ' = np.sum(total_cycling_output_'+ str(prod_struct)+ ')'
    exec 'tot_total_straight_output_'+ str(prod_struct)+ ' = np.sum(total_straight_output_'+ str(prod_struct)+ ')'
     
    # --- emissions part due to SC, IC, IA, DA
    # w_i_SC_ProdStruct  is the emission vector of emission i due to SC
    # w_i_IC_ProdStruct  is the emission vector of emission i due to IC
    # w_i_IA_ProdStruct  is the emission vector of emission i due to IA
    # w_i_DA_ProdStruct  is the emission vector of emission i due to DA
    for i in range(NBR_disposals):
        exec 'w_'+str(i)+'_SC_'+ str(prod_struct)+ '=np.dot(E'+ str(i)+ ',total_self_cycling_output_'+ str(prod_struct)+ ').reshape((NBR_sectors,1))'
        exec 'w_'+str(i)+'_IC_'+ str(prod_struct)+ '=np.dot(E'+ str(i)+ ',total_inter_cycling_output_'+ str(prod_struct)+ ').reshape((NBR_sectors,1))'
        exec 'w_'+str(i)+'_IA_'+ str(prod_struct)+ '=np.dot(E'+ str(i)+ ',total_indirect_acyclic_output_'+ str(prod_struct)+ ').reshape((NBR_sectors,1))'
        exec 'w_'+str(i)+'_DA_'+ str(prod_struct)+ '=np.dot(E'+ str(i)+ ',total_direct_acyclic_output_'+ str(prod_struct)+ ').reshape((NBR_sectors,1))'     
     
     
    #create arrays with all emissions
    exec 'w_array_SC_'+ str(prod_struct)+ '=w_0_SC_'+ str(prod_struct)+'.reshape((NBR_sectors,1))'
    exec 'w_array_IC_'+ str(prod_struct)+ '=w_0_IC_'+ str(prod_struct)+'.reshape((NBR_sectors,1))'
    exec 'w_array_IA_'+ str(prod_struct)+ '=w_0_IA_'+ str(prod_struct)+'.reshape((NBR_sectors,1))'
    exec 'w_array_DA_'+ str(prod_struct)+ '=w_0_DA_'+ str(prod_struct)+'.reshape((NBR_sectors,1))'
    for i in range(NBR_disposals-1):
        exec 'w_array_SC_'+ str(prod_struct)+ '= np.hstack((w_array_SC_'+ str(prod_struct)+',w_'+str(i+1)+'_SC_'+ str(prod_struct)+'))'
        exec 'w_array_IC_'+ str(prod_struct)+ '= np.hstack((w_array_IC_'+ str(prod_struct)+',w_'+str(i+1)+'_IC_'+ str(prod_struct)+'))'
        exec 'w_array_IA_'+ str(prod_struct)+ '= np.hstack((w_array_IA_'+ str(prod_struct)+',w_'+str(i+1)+'_IA_'+ str(prod_struct)+'))'    
        exec 'w_array_DA_'+ str(prod_struct)+ '= np.hstack((w_array_DA_'+ str(prod_struct)+',w_'+str(i+1)+'_DA_'+ str(prod_struct)+'))' 

    #print to log
    tmp=0 #this is just to avoid syntax errors, tmp will be overwritten by the exec statements but otherwise the syntax check says that tmp has not been defined    
    exec 'tmp=cycling_throughput_'+str(prod_struct)
    print('\n The cycling_throughput_'+str(prod_struct)+' of each sector is:\n '+str(tmp))
    exec 'tmp=x'+str(prod_struct)
    print('\n The total_inputs x'+str(prod_struct)+' are:\n '+str(tmp))
    exec 'tmp=feeding_flows_'+str(prod_struct)
    print('\n The feeding_flows_'+str(prod_struct)+' (inputs) to maintain the cycles are:\n '+str(tmp))
    exec 'tmp=raw_straight_inputs_'+str(prod_struct)
    print('\n The straight_inputs_'+str(prod_struct)+' (inputs) that are used are :\n '+str(tmp))
    exec 'tmp=total_losses_'+str(prod_struct)
    print('\n The total_losses_'+str(prod_struct)+' (or emissions) are:\n '+str(tmp))
    exec 'tmp=cycling_losses_'+str(prod_struct)
    print('\n The cycling_losses_'+str(prod_struct)+' due to cycling are:\n '+str(tmp))
    exec 'tmp=acyclic_losses_'+str(prod_struct)
    print('\n The acyclic_losses_'+str(prod_struct)+' due to straight flows are:\n '+str(tmp))
    exec 'tmp=total_cycling_output_'+str(prod_struct)
    print('\n The total_cycling_output_'+str(prod_struct)+' due to cycling is:\n '+str(tmp))
    exec 'tmp=total_straight_output_'+str(prod_struct)
    print('\n The total_straight_output_'+str(prod_struct)+' due to straight flows is:\n '+str(tmp))

# OBSOLETE    
#    # ---- Direct -indirect decomposition ---- ##Values  
#    # name and description indicators
#    # dir_feeding_flows_i
#    # indir_feeding_flows_i
#    # dir_straight_inputs_i
#    # indir_straight_inputs_i
#    # dir_total_inputs_i
#    # indir_total_inputs_i
#    # dir_straight_losses_i
#    # indir_straight_losses_i
#    # dir_cycling_losses_i
#    # indir_cycling_losses_i
#    # dir_total_losses_i
#    # indir_total_losses_i
#
#    #direct-indirect feeding flows (cycling inputs)    
#    exec 'dir_feeding_flows_'+ str(prod_struct)+'=feeding_flows_'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_feeding_flows_'+ str(prod_struct)+'=np.sum(np.delete(feeding_flows_'+ str(prod_struct)+','+ str(prod_struct)+'))'
#    #direct-indirect straight inputs
#    exec 'dir_straight_inputs_'+ str(prod_struct)+'=raw_straight_inputs_'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_straight_inputs_'+ str(prod_struct)+'=np.sum(np.delete(raw_straight_inputs_'+ str(prod_struct)+','+ str(prod_struct)+'))'
#    #direct-indirect total inputs
#    exec 'dir_total_inputs_'+ str(prod_struct)+'=r'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_total_inputs_'+ str(prod_struct)+'=np.sum(np.delete(r'+ str(prod_struct)+','+ str(prod_struct)+'))'
#    #direct-indirect straight losses
#    exec 'dir_straight_losses_'+ str(prod_struct)+'=straight_losses_'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_straight_losses_'+ str(prod_struct)+'=np.sum(np.delete(straight_losses_'+ str(prod_struct)+','+ str(prod_struct)+'))'
#    #direct-indirect cycling losses
#    exec 'dir_cycling_losses_'+ str(prod_struct)+'=cycling_losses_'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_cycling_losses_'+ str(prod_struct)+'=np.sum(np.delete(cycling_losses_'+ str(prod_struct)+','+ str(prod_struct)+'))' 
#    #direct-indirect total losses
#    exec 'dir_total_losses_'+ str(prod_struct)+'=total_losses_'+ str(prod_struct)+'['+ str(prod_struct)+']'
#    exec 'indir_total_losses_'+ str(prod_struct)+'=np.sum(np.delete(total_losses_'+ str(prod_struct)+','+ str(prod_struct)+'))' 
#    
    
 
    #### Draw the sankey diagram for each piot #####################################
    
    #it will save the created drawing as png
    # IF I REALLY USE THIS AT SOME POINT IN THE FUTURE, I WILL NEED TO UPDATE THE
    #exec 'draw_sankeys.sankey_of_cyclic_flows(units,title,NBR_sectors,x'+str(prod_struct)+',feeding_flows_'+str(prod_struct)+',raw_straight_inputs_'+str(prod_struct)+',total_losses_'+str(prod_struct)+',cycling_losses_'+str(prod_struct)+',acyclic_losses_'+str(prod_struct)+',f'+str(prod_struct)+',Z_array_cyclic_'+str(prod_struct)+',Z_array_acyclic_'+str(prod_struct)+',self_cycling_'+str(prod_struct)+',Images_Path,\'sankey.cycles.prod_'+str(prod_struct)+'.\'+output_filename)'

#####################################################
####### DRAW CIRCOS DIAGRAM FOR EACH PROD STRUCTURE

#### CAREFUL: THE PROD STRUCT ARE CALCULATED FOR 1 UNIT OF FD
####          BUT CIRCOS CANNOT USE DECIMALS IN POSITION OF IDEOGRAM
####            SO YOU NEED TO MULTIPLY EVERYTHING BY 100 OR 1000 OR WHATEVER
####            SO THAT YOU CAN DRAW IT. PASS THE NUMBER YOU INCREASES AS "UNIT"
####            ARGUMENT TO CORRECT IT

#===========arrays to pass for SC, IC, IA and DA structures====================
# Z_array_self_cycling
# self_cycling_feeding_flows_all #self-cyclic resources
# np.zeros((1,NRB_sectors)) # the fd of self-cycling =0
# w_array_SC_all # the emissions matrix 
# 
# Z_array_inter_cycling
# inter_cycling_feeding_flows_all #inter-cyclic resources
# np.zeros((NRB_sectors,NRB_sectors)) # the fd of inter-cycling =0
# w_array_IC_all# the emissions matrix 
# 
# Z_array_acyclic # the indirect acyclic  array is the Z_array_acyclic
# raw_indirect_straight_inputs_all #indirect-acyclic resources
# indirect_fd_all # fd for indirect acyclic
# w_array_IA_all # emissions for indirect acyclic
# 
# 
# np.zeros((NRB_sectors,NRB_sectors)) # the direct acyclic  array is a zero array
# raw_direct_straight_inputs_all #  direct acyclic resources
# direct_fd_all # fd for direct acyclic
# w_array_DA_all # emissions for direct acyclic
#==============================================================================

#XXX: working here
    if circos_draw:
    # CircosFolder: where you want to put the circos drawings
        CircosFolder=os.path.join(dirPath,'circos_graphs_'+time_at_start + data_filename + '_prod_structure_{0}'.format(prod_struct))
        os.chdir(dirPath)
        if os.path.split(CircosFolder)[1] not in os.listdir('./'):
            #CHECK IF DIRECTORY EXISTS. IF not, create it.
            os.mkdir(CircosFolder)    
        
        # circos interface for flow_by_sector: sector_outputs or sector inputs
        unit=1000    
        exec 'circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit, \'merged\', \'normalised\', \'sector_outputs\', \'size_desc\',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers[\'column headings\'], Z'+ str(prod_struct)+', r'+ str(prod_struct)+'.reshape((1,NBR_sectors)), f'+ str(prod_struct)+'.reshape((NBR_sectors,1)), w'+ str(prod_struct)+'_array)'
        exec 'circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit, \'symmetrical\', \'normalised\', \'sector_outputs\', \'size_desc\',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers[\'column headings\'], Z'+ str(prod_struct)+', r'+ str(prod_struct)+'.reshape((1,NBR_sectors)), f'+ str(prod_struct)+'.reshape((NBR_sectors,1)), w'+ str(prod_struct)+'_array)'
        
      
        # circos interface for flow_by_type: cyclic_acyclic
        exec 'circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit, \'merged\', \'normalised\', \'cyclic_acyclic\', \'size_desc\',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers[\'column headings\'], Z_array_self_cycling_'+ str(prod_struct)+',self_cycling_feeding_flows_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_SC_'+ str(prod_struct)+', Z_array_inter_cycling_'+ str(prod_struct)+', inter_cycling_feeding_flows_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_IC_'+ str(prod_struct)+', Z_array_acyclic_'+ str(prod_struct)+', raw_indirect_straight_inputs_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), indirect_fd_'+ str(prod_struct)+'.reshape((NBR_sectors,1)) , w_array_IA_'+ str(prod_struct)+', np.zeros((NBR_sectors,NBR_sectors)), raw_direct_straight_inputs_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), direct_fd_'+ str(prod_struct)+'.reshape((NBR_sectors,1)), w_array_DA_'+ str(prod_struct)+')'
        
        exec 'circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit, \'symmetrical\', \'normalised\', \'cyclic_acyclic\', \'size_desc\',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, Z_array_with_headers[\'column headings\'], Z_array_self_cycling_'+ str(prod_struct)+',self_cycling_feeding_flows_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_SC_'+ str(prod_struct)+', Z_array_inter_cycling_'+ str(prod_struct)+', inter_cycling_feeding_flows_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), np.zeros((NBR_sectors,1)), w_array_IC_'+ str(prod_struct)+', Z_array_acyclic_'+ str(prod_struct)+', raw_indirect_straight_inputs_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), indirect_fd_'+ str(prod_struct)+'.reshape((NBR_sectors,1)) , w_array_IA_'+ str(prod_struct)+', np.zeros((NBR_sectors,NBR_sectors)), raw_direct_straight_inputs_'+ str(prod_struct)+'.reshape((1,NBR_sectors)), direct_fd_'+ str(prod_struct)+'.reshape((NBR_sectors,1)), w_array_DA_'+ str(prod_struct)+')'


###############################################################################
##############################################################################
############### WRITING THE OUTPUT FILES ######################

###### Saving the data to a new xls file

output_workbook = xlwt.Workbook()
#setting STYLES
style_grey_bold = xlwt.easyxf('pattern: pattern solid, fore_colour periwinkle;''font: bold true;')
style_header_lalign= xlwt.easyxf('border: left thin, right thin, top thin, bottom thin;''alignment: horizontal left;')
style_header_center= xlwt.easyxf('border: left thin, right thin, top thin, bottom thin;''alignment: horizontal center;')
style_header_lalign_bold= xlwt.easyxf('border: left thin, right thin, top thin, bottom thin;''alignment: horizontal left;''font: bold true;')

style_nbr_3dec= xlwt.easyxf('border: left thin, right thin, top thin, bottom thin;',num_format_str = "#,###0.000;-#,###0.000" )
style_link = xlwt.easyxf('font: underline single')


###############################################################################
###### Saving the analyses for the whole economy in worksheet called 'All flows structure'
##############################################################################

## create sheet to add images
#out_sheet_all_image = output_workbook.add_sheet('All flows structure Images')
#out_sheet_all_image.insert_bitmap(Images_Path+'/'+'sankey.cycles.all.'+output_filename+'.png', 0, 0)#the insert_bitmap function does not accept pngs...


## 'All flows structure' is called internally out_sheet_all
out_sheet_all = output_workbook.add_sheet('All flows output structure')

#first row with title
out_sheet_all.write(0,0,'Production structure for all products',style_grey_bold)
out_sheet_all.row(0).set_style(style_grey_bold)


#Industry column headers start at third row, second column
i=1#column index
for column_headers in Z_array_with_headers['column headings']:
    out_sheet_all.write(2,i,column_headers,style_header_center)
    i+=1#this means i=i+1

#Industry row headers start at 1st column row, fourth row
i=3#row index
for row_headers in Z_array_with_headers['row headings']:
    out_sheet_all.write(i,0,row_headers,style_header_lalign)
    i+=1#this means i=i+1

#Z matrix content starts at fourth row and second column
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+3,col_index+1,Z_array[row_index][col_index],style_nbr_3dec)

#r vector headings
out_sheet_all.write(NBR_sectors+3,0,r_array_with_headers['row headings'],style_header_lalign)
#r vector content at NBR_sectors+3
for col_index in range(NBR_sectors):
    out_sheet_all.write(NBR_sectors+3,col_index+1,r_array.flatten()[col_index],style_nbr_3dec)

#total inputs header 
out_sheet_all.write(NBR_sectors+4,0,'Total inputs',style_header_center)
#write total inputs data 
for col_index in range(NBR_sectors):
    out_sheet_all.write(NBR_sectors+4,col_index+1,total_inputs.flatten()[col_index],style_nbr_3dec)

#f array (outputs) data
#column headers for final goods AND wastes start at column NBR_sectors+1, fourth row
i=NBR_sectors+1#row index
for column_headers in f_array_with_headers['column headings']:
    out_sheet_all.write(2,i,column_headers,style_header_center)
    i+=1#this means i=i+1
    
#data for final goods starts at fourth row and NBR_sectors+1 column
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+3,NBR_sectors+1,fd_all.flatten()[row_index],style_nbr_3dec)
#data for wastes starting at fourth row and 1+NBR_sectors+1+waste_index column
for waste_index in range(NBR_disposals):
    for row_index in range(NBR_sectors):
        exec 'out_sheet_all.write('+str(row_index+3)+','+str(1+NBR_sectors+1+waste_index)+',w'+str(waste_index)+'_all.flatten()['+str(row_index)+'],style_nbr_3dec)'

#total output header: start at column 1+NBR_sectors+1+NBR_disposals, fourth row
out_sheet_all.write(2,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)
#total output data
for row_index in range(NBR_sectors):
        exec 'out_sheet_all.write('+str(row_index+3)+','+str(1+NBR_sectors+1+NBR_disposals)+',total_outputs.flatten()['+str(row_index)+'],style_nbr_3dec)'

#### Meso- and macro-economic resource indicators (efficiencies and  intensities)

#section starting row:
row_section_start=NBR_sectors+5

#section title
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Meso- and macro-economic resource indicators (efficiencies and  intensities)',style_grey_bold)

#meso economic efficiencies top headers
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,0,1,'Meso indicators',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,0,1,'Resource efficiencies',style_header_center)
#meso economic efficiencies row headers and values
for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)
        out_sheet_all.write(row_index+row_section_start+3,1,list_sectoral_eff_vars[row_index],style_nbr_3dec)

#write TOP-LEVEL MACRO INDICATORS
#top header
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,3,4,'Top-level macro indicators',style_header_center)
#row headers
out_sheet_all.write(row_section_start+2,3,'Resource efficiency',style_header_lalign)
out_sheet_all.write(row_section_start+4,3,'Resource intensity',style_header_lalign)
out_sheet_all.write(row_section_start+5,3,'Emission intensity',style_header_lalign)
#indicators
out_sheet_all.write(row_section_start+2,4,tot_res_eff_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4,4,tot_res_int_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+5,4,tot_em_int_all,style_nbr_3dec)

#write MACRO INDICATORS 
#top header
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,6,7+NBR_disposals,'Macro indicators (intensities)',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,6,7,'Resource intensities',style_header_center)


#macro economic Resource intensities row headers and values
for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3,6,Z_array_with_headers['row headings'][row_index],style_header_lalign)
        out_sheet_all.write(row_index+row_section_start+3,7,res_int_all[row_index],style_nbr_3dec)
#macro economic TOTAL Resource intensities row headers and values
out_sheet_all.write(row_index+row_section_start+4,6,'Totals',style_header_lalign)
out_sheet_all.write(row_index+row_section_start+4,7,tot_res_int_all,style_nbr_3dec)

# Emission intensities column headers and values 
for waste_index in range(NBR_disposals):
    #column header
    out_sheet_all.write(row_section_start+2,8+waste_index,f_array_with_headers['column headings'][1+waste_index]+' intensity',style_header_center)
    #values
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index + row_section_start + 3, 8 + waste_index,eval('em_int_'+str(waste_index)+'_all_'+str(row_index)),style_nbr_3dec)# FIXME: need to solve this, for that I need to create the sectoral intensities which I believe I did not create previously.
    exec 'out_sheet_all.write(row_index+row_section_start+4,8+'+str(waste_index)+',em_int_'+str(waste_index)+'_all,style_nbr_3dec)' 



#### Leontief Inverse:
#section starting row:
row_section_start=2*NBR_sectors+9
#section header
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Leontief inverse with related outputs endogenised [L=(I-A-Etot)^-1] (Since it is a characteristic of the sector, it will be the same for all production structures, even  calculated with the specific production structure variables)',style_grey_bold)

# write L starting at row_section_start+1
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+1,col_index+1,L[row_index][col_index],style_nbr_3dec)

#### Cycle decomposition:
#write section header starting at colummn 0, row 3*NBR_sectors+10
out_sheet_all.row(3*NBR_sectors+10).set_style(style_grey_bold)
out_sheet_all.write(3*NBR_sectors+10,0,'Cyclic-acyclic decomposition of the inter-sectoral matrix based on Ulanowicz (1983)',style_grey_bold)

#header for Cyclic component
out_sheet_all.write(3*NBR_sectors+11,0,'Cyclic component',style_header_lalign)
# write cycle_matrix starting at colummn 0, row 3*NBR_sectors+12
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+3*NBR_sectors+12,col_index+1,Z_array_cyclic[row_index][col_index],style_nbr_3dec)

#header for Acyclic component   
out_sheet_all.write(4*NBR_sectors+13,0,'Acyclic component',style_header_lalign)
# write acyclic_matrix starting at colummn 0, row 4*NBR_sectors+14
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+4*NBR_sectors+14,col_index+1,Z_array_acyclic[row_index][col_index],style_nbr_3dec)    

#### SECTION: Cyclic-acyclic indicators starting at colummn 0, row 5*NBR_sectors+14

#section starting row:
row_section_start=5*NBR_sectors+14  

#SECTION TITLE  
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Cyclic-acyclic indicators',style_grey_bold)

#ROW HEADERS for sectors
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)   
#row header for totals
out_sheet_all.write(row_section_start+5+row_index,0,'TOTALS',style_header_lalign)   

## COLUMN HEADERS OF indicators

##cyclic flows COLUMN HEADERS section
#cyclic flows top level headers
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,1,3,'Cyclic flows within the inter-sectoral matrix',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,1,3,'Cycling throughput',style_header_center)
#cyclic flows disaggregated level headers
out_sheet_all.write(row_section_start+3,1,'Self-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,2,'Inter-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,3,'Total',style_header_center)

##System inputs COLUMN HEADERS section
#System inputs top level headers
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,5,11,'System inputs (primary resources)',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,5,7,'Cyclic',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,8,10,'Acyclic',style_header_center)
out_sheet_all.write(row_section_start+2,11,'Total inputs',style_header_center)

#System inputs disaggregated level headers
out_sheet_all.write(row_section_start+3,5,'Self-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,6,'Inter-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,7,'Total',style_header_center)

out_sheet_all.write(row_section_start+3,8,'Direct',style_header_center)
out_sheet_all.write(row_section_start+3,9,'Indirect',style_header_center)
out_sheet_all.write(row_section_start+3,10,'Total',style_header_center)

out_sheet_all.write(row_section_start+3,11,'Cycling + Acyclic',style_header_center)

##System outputs COLUMN HEADERS section
#System outputs top level headers
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,13,21,'System outputs (final goods and emissions)',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,13,14,'Final demand',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,15,17,'Cyclic emissions',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,18,20,'Acyclic emissions',style_header_center)
out_sheet_all.write(row_section_start+2,21,'Total Emissions',style_header_center)

#System outputs disaggregated level headers
out_sheet_all.write(row_section_start+3,13,'Direct',style_header_center)
out_sheet_all.write(row_section_start+3,14,'Indirect',style_header_center)
out_sheet_all.write(row_section_start+3,15,'Self-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,16,'Inter-cycling',style_header_center)
out_sheet_all.write(row_section_start+3,17,'Total',style_header_center)

out_sheet_all.write(row_section_start+3,18,'Direct',style_header_center)
out_sheet_all.write(row_section_start+3,19,'Indirect',style_header_center)
out_sheet_all.write(row_section_start+3,20,'Total',style_header_center)

out_sheet_all.write(row_section_start+3,21,'Cycling + Acyclic',style_header_center)

##Total outputs COLUMN HEADERS section
#Total outputs top level headers
out_sheet_all.write_merge(row_section_start+1,row_section_start+1,23,27,'Total outputs',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,23,24,'Cycling',style_header_center)
out_sheet_all.write_merge(row_section_start+2,row_section_start+2,25,26,'Acyclic',style_header_center)
out_sheet_all.write(row_section_start+2,27,'Total',style_header_center)

#Total outputs disaggregated level headers
out_sheet_all.write(row_section_start+3,23,'Self',style_header_center)
out_sheet_all.write(row_section_start+3,24,'Inter',style_header_center)
out_sheet_all.write(row_section_start+3,25,'Direct',style_header_center)
out_sheet_all.write(row_section_start+3,26,'Indirect',style_header_center)
out_sheet_all.write(row_section_start+3,27,'Cyclic + Acyclic',style_header_center)

# ---- Indicators of cyclic component ----
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,1,self_cycling_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,2,inter_cycling_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,3,cycling_throughput_all[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,1,tot_self_cycling_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,2,tot_inter_cycling_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,3,tot_cycling_throughput_all,style_nbr_3dec)

# ---- Indicators of feeding flows (inputs) to maintain the cyclic component ----
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,5,self_cycling_feeding_flows_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,6,inter_cycling_feeding_flows_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,7,feeding_flows_all[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,5,tot_self_cycling_feeding_flows_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,6,tot_inter_cycling_feeding_flows_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,7,tot_feeding_flows_all,style_nbr_3dec)

# ---- Indicators on straight inputs that generate the acyclic component --------
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,8,raw_direct_straight_inputs_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,9,raw_indirect_straight_inputs_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,10,raw_straight_inputs_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,11,r_array.flatten()[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,8,tot_raw_direct_straight_inputs_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,9,tot_raw_indirect_straight_inputs_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,10,tot_raw_straight_inputs_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,11,np.sum(r_array),style_nbr_3dec)

# ---- Indicators of cycling losses due to the cyclic component and corresponding cyclic inputs----
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,13,direct_fd_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,14,indirect_fd_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,15,self_cycling_losses_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,16,inter_cycling_losses_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,17,cycling_losses_all[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,13,tot_direct_fd_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,14,tot_indirect_fd_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,15,tot_self_cycling_losses_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,16,tot_inter_cycling_losses_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,17,tot_cycling_losses_all,style_nbr_3dec)

# ---- Acyclic emissions related indicators----

for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,18, direct_acyclic_losses_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,19, indirect_acyclic_losses_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,20,acyclic_losses_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,21,total_losses_all[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,18,tot_direct_acyclic_losses_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,19,tot_indirect_acyclic_losses_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,20,tot_straight_losses_all,style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,21,tot_total_losses_all,style_nbr_3dec)

# ---- Indicators of the total outputs  ----
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index,23,total_self_cycling_output_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,24,total_inter_cycling_output_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,25,total_direct_acyclic_output_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,26,total_indirect_acyclic_output_all[row_index],style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index,27,total_outputs.flatten()[row_index],style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1,23,np.sum(total_self_cycling_output_all),style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,24,np.sum(total_inter_cycling_output_all),style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,25,np.sum(total_direct_acyclic_output_all),style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,26,np.sum(total_indirect_acyclic_output_all),style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1,27,np.sum(total_outputs),style_nbr_3dec)

# this was an old hyperlink to the corresponding sankey diagram - now the sankey is not even saved
#out_sheet_all.write(row_section_start+NBR_sectors+5,0, xlwt.Formula('HYPERLINK(\"./images/sankey.cycles.'+output_filename+'.all.png\";"Link to a generated sankey diagram representing the cycling structure - will be substituted by Circos diagrams")'),style_link)    ### THE PROBLEMS Is THAT LIBREOFFICE does not open the link


#### Cyclic and acyclic structures section:
#section starting row:
row_section_start=6*NBR_sectors+20 

#write subsection header starting at colummn 0, row 6*NBR_sectors+20

out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Cyclic and acyclic structures',style_grey_bold)


### Cyclic structure
out_sheet_all.write(row_section_start+1,0,'Cyclic structure',style_header_lalign_bold)

# write cycle_matrix starting at colummn 0, row 3*NBR_sectors+12
for row_index in range(NBR_sectors):
    #row headers intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    
    for col_index in range(NBR_sectors):              
        #intersectoral flows        
        out_sheet_all.write(row_index+row_section_start+3,col_index+1,Z_array_cyclic[row_index][col_index],style_nbr_3dec)
#INPUTS
#Feeding flows header
out_sheet_all.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)
#Feeding flows values
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,feeding_flows_all[col_index],style_nbr_3dec)
#total_cycling_output_all flows header (ACTUALLY = INPUTS)
out_sheet_all.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5,1+col_index,total_cycling_output_all[col_index],style_nbr_3dec)

#OUTPUTS
#final demand = 0
out_sheet_all.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors,0,style_nbr_3dec)
#cycling losses flows 
out_sheet_all.write(row_section_start+2,2+NBR_sectors,'Emissions',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,2+NBR_sectors,feeding_flows_all[row_index],style_nbr_3dec)
#total_cycling_output_all
out_sheet_all.write(row_section_start+2,3+NBR_sectors,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,3+NBR_sectors,total_cycling_output_all[row_index],style_nbr_3dec)



### Acyclic structure         
row_section_start=7*NBR_sectors+26         
out_sheet_all.write(row_section_start,0,'Acyclic structure',style_header_lalign_bold)
# write acyclic_matrix starting at colummn 0, row 4*NBR_sectors+14
for row_index in range(NBR_sectors):
    #row headers  intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+2,col_index+1,Z_array_acyclic[row_index][col_index],style_nbr_3dec)      

#INPUTS
#straight raw input flows header
out_sheet_all.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)
#straight raw input flows  values
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+col_index,raw_straight_inputs_all.flatten()[col_index],style_nbr_3dec)
#total_straight_output_all (ACTUALLY = INPUTS) flows header
out_sheet_all.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,total_straight_output_all.flatten()[col_index],style_nbr_3dec)

#OUTPUTS
#Final goods
out_sheet_all.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors,fd_all.flatten()[row_index],style_nbr_3dec)
#Straight losses
out_sheet_all.write(row_section_start+1,2+NBR_sectors,'Emissions',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,2+NBR_sectors,acyclic_losses_all.flatten()[row_index],style_nbr_3dec)
#	total straight output
out_sheet_all.write(row_section_start+1,3+NBR_sectors,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,3+NBR_sectors,total_straight_output_all[row_index],style_nbr_3dec)


#### DISAGGREGATED cyclic structures section:
#section starting row:
row_section_start=8*NBR_sectors+32 

#write subsection header starting at colummn 0, row 6*NBR_sectors+20

out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Disaggregated Cyclic structures (self and inter-cycling)',style_grey_bold)


### SELF-Cyclic structure
out_sheet_all.write(row_section_start+1,0,'Self-cycling structure',style_header_lalign_bold)

# write cycle_matrix starting at colummn 0, row 3*NBR_sectors+12
for row_index in range(NBR_sectors):
    #row headers intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    
    for col_index in range(NBR_sectors):              
        #intersectoral flows        
        out_sheet_all.write(row_index+row_section_start+3,col_index+1,Z_array_self_cycling[row_index][col_index],style_nbr_3dec)

#INPUTS
#Feeding flows header
out_sheet_all.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)
#Feeding flows values
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,self_cycling_feeding_flows_all[col_index],style_nbr_3dec)
#total_cycling_output_all flows header (ACTUALLY = INPUTS)
out_sheet_all.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5,1+col_index,total_self_cycling_output_all[col_index],style_nbr_3dec)

## OUTPUTS
# fd: final demand = 0
out_sheet_all.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors,0,style_nbr_3dec)
# Emissions
for i in range(NBR_disposals):
    # write header
    out_sheet_all.write(row_section_start+2,1+NBR_sectors+1+i,f_array_with_headers['column headings'][i+1],style_header_lalign)

    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors+1+i,eval('w_'+str(i)+'_SC_all')[row_index][0],style_nbr_3dec)

#total_cycling_output_all
out_sheet_all.write(row_section_start+2,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors+1+NBR_disposals,total_self_cycling_output_all[row_index],style_nbr_3dec)



### INTER-CYCLIC structure         
row_section_start=9*NBR_sectors+38         
out_sheet_all.write(row_section_start,0,'Inter-cycling structure',style_header_lalign_bold)

for row_index in range(NBR_sectors):
    #row headers  intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+2,col_index+1,Z_array_inter_cycling[row_index][col_index],style_nbr_3dec)      

#INPUTS
#resources header
out_sheet_all.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)
#straight raw input flows  values
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+col_index,inter_cycling_feeding_flows_all.flatten()[col_index],style_nbr_3dec)
#total_straight_output_all (ACTUALLY = INPUTS) flows header
out_sheet_all.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,total_inter_cycling_output_all.flatten()[col_index],style_nbr_3dec)

## OUTPUTS
# Final goods
out_sheet_all.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors,0,style_nbr_3dec)
# Emissions 
for i in range(NBR_disposals):
    out_sheet_all.write(row_section_start+1,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors+1+i,eval('w_'+str(i)+'_IC_all')[row_index][0],style_nbr_3dec)
#	total straight output
out_sheet_all.write(row_section_start+1,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors+1+NBR_disposals,total_inter_cycling_output_all[row_index],style_nbr_3dec)


#### DISAGGREGATED acyclic structures section:
#section starting row:
row_section_start=10*NBR_sectors+44 

#write subsection header starting at colummn 0, row row_section_start

out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write(row_section_start,0,'Disaggregated acyclic structures (direct and indirect)',style_grey_bold)


### Direct acyclic structure
out_sheet_all.write(row_section_start+1,0,'Direct acyclic structure',style_header_lalign_bold)

# write cycle_matrix starting at colummn 0, row 3*NBR_sectors+12
for row_index in range(NBR_sectors):
    #row headers intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    
    for col_index in range(NBR_sectors):              
        #intersectoral flows        
        out_sheet_all.write(row_index+row_section_start+3,col_index+1,0,style_nbr_3dec)

#INPUTS
#Resources 
out_sheet_all.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,raw_direct_straight_inputs_all[col_index],style_nbr_3dec)
#total inputs
out_sheet_all.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5,1+col_index,total_direct_acyclic_output_all[col_index],style_nbr_3dec)

#OUTPUTS
# final demand 
out_sheet_all.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors,direct_fd_all[row_index],style_nbr_3dec)
# emissions
for i in range(NBR_disposals):
    out_sheet_all.write(row_section_start+2,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors+1+i,eval('w_'+str(i)+'_DA_all')[row_index][0],style_nbr_3dec)
#total_direct_acyclic_output_all
out_sheet_all.write(row_section_start+2,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+NBR_sectors+1+NBR_disposals,total_direct_acyclic_output_all[row_index],style_nbr_3dec)



### Indirect acyclic structure         
row_section_start=11*NBR_sectors+50         
out_sheet_all.write(row_section_start,0,'Indirect acyclic structure',style_header_lalign_bold)

#Intersectoral matrix
for row_index in range(NBR_sectors):
    #row headers  intersectoral matrix
    out_sheet_all.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)
    #column headers  intersectoral matrix
    out_sheet_all.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index], style_header_lalign)
    #values
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+2,col_index+1,Z_array_acyclic[row_index][col_index],style_nbr_3dec)      

#INPUTS
#resources header
out_sheet_all.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)
#straight raw input flows  values
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3,1+col_index,raw_indirect_straight_inputs_all[col_index],style_nbr_3dec)
#total inputs
out_sheet_all.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4,1+col_index,total_indirect_acyclic_output_all[col_index],style_nbr_3dec)

#OUTPUTS
#Final goods
out_sheet_all.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors,indirect_fd_all[row_index],style_nbr_3dec)
#Emissions
for i in range(NBR_disposals):
    out_sheet_all.write(row_section_start+1,1+NBR_sectors+1+i,f_array_with_headers['column headings'][i+1],style_header_lalign)
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors+1+i,eval('w_'+str(i)+'_IA_all')[row_index][0],style_nbr_3dec)
#total outputs
out_sheet_all.write(row_section_start+1,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+2,1+NBR_sectors+1+NBR_disposals,total_indirect_acyclic_output_all[row_index],style_nbr_3dec)




##############################################################################
##############################################################################
###### Writing data for all production structures in worksheets called 'Prod i structure'
###############################################################################

#create a sheets for each product
list_of_prod_sheets=[]
for prod_struct in range(NBR_sectors):
    exec 'tmp=Z_array_with_headers[\'column headings\']['+str(prod_struct)+']'
    exec 'out_sheet_'+str(prod_struct)+'=output_workbook.add_sheet(\''+str(tmp)+' output structure\')'
    list_of_prod_sheets.append('out_sheet_'+str(prod_struct))

## add the results in each production structure sheet
for prod_sheet in list_of_prod_sheets:
    exec str(prod_sheet)+'.write(0,0,\'Production structure for product '+str(list_of_prod_sheets.index(prod_sheet))+' ('+str( Z_array_with_headers.get('column headings')[list_of_prod_sheets.index(prod_sheet)])+')\',style_grey_bold)'
    exec str(prod_sheet)+'.row(0).set_style(style_grey_bold)'
   #Industry column headers start at third row, second column
    for column_headers in Z_array_with_headers['column headings']:
       exec str(prod_sheet)+'.write(2,1+Z_array_with_headers[\'column headings\'].index(column_headers),column_headers,style_header_center)'
    #Industry row headers start at 1st column row, fourth row
    for row_headers in Z_array_with_headers['row headings']:
       exec str(prod_sheet)+'.write(3+Z_array_with_headers[\'row headings\'].index(row_headers),0,row_headers,style_header_lalign)'
      #Z matrix content starts at fourth row and second column
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+3,col_index+1,Z'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'
#r vector headings
    exec str(prod_sheet)+'.write(NBR_sectors+3,0,r_array_with_headers[\'row headings\'],style_header_lalign)'
#r vector content at NBR_sectors+3
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(NBR_sectors+3,col_index+1,r'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[col_index],style_nbr_3dec)'

#total inputs header 
    exec str(prod_sheet)+'.write(NBR_sectors+4,0,\'Total inputs\',style_header_lalign)'
#write total inputs data 
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(NBR_sectors+4,col_index+1,x'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[col_index],style_nbr_3dec)'

#f array (outputs) data
#column headers for final goods AND wastes start at column NBR_sectors+1, fourth row
    for column_headers in f_array_with_headers['column headings']:
        exec str(prod_sheet)+'.write(2,NBR_sectors+1+f_array_with_headers[\'column headings\'].index(column_headers),column_headers,style_header_lalign)'
#data for final goods starts at fourth row and NBR_sectors+1 column
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+3,NBR_sectors+1,f'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
#data for wastes starting at fourth row and 1+NBR_sectors+1+waste_index column
    for waste_index in range(NBR_disposals):
        for row_index in range(NBR_sectors):
           exec str(prod_sheet)+'.write('+str(row_index+3)+','+str(1+NBR_sectors+1+waste_index)+',w'+str(waste_index)+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()['+str(row_index)+'],style_nbr_3dec)'

#total output header: start at column 1+NBR_sectors+1+NBR_disposals, fourth row
    exec str(prod_sheet)+'.write(2,1+NBR_sectors+1+NBR_disposals,\'Total outputs\',style_header_lalign)'
#total output data
    for row_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write('+str(row_index+3)+','+str(1+NBR_sectors+1+NBR_disposals)+',x'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()['+str(row_index)+'],style_nbr_3dec)'

#### Meso- and macro-economic resource indicators (efficiencies and  intensities)
    #section starting row:
    row_section_start=NBR_sectors+5
    #section title
    exec str(prod_sheet)+'.row(row_section_start).set_style(style_grey_bold)'
    exec str(prod_sheet)+'.write(row_section_start,0,\'Meso- and macro-economic resource indicators (efficiencies and  intensities)\',style_grey_bold)'
    
    #meso economic efficiencies top headers
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,0,1,'Meso efficiencies',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,0,1,'Resource efficiencies',style_header_center)'''
    #meso economic efficiencies row headers and values REMEMBER THEY ARE THE SAME SO NO NEED TO GET THE PROD_SHEET NUMBER
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,1,list_sectoral_eff_vars[row_index],style_nbr_3dec)'''

    #write TOP-LEVEL MACRO INDICATORS
    #top header
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,3,4,'Top-level macro indicators',style_header_center)'''

    #row headers
    exec str(prod_sheet)+'''.write(row_section_start+2,3,'Resource efficiency',style_header_lalign)'''
    exec str(prod_sheet)+'''.write(row_section_start+4,3,'Resource intensity',style_header_lalign)'''
    exec str(prod_sheet)+'''.write(row_section_start+5,3,'Emission intensity',style_header_lalign)'''
    
    #indicators
    exec str(prod_sheet)+'.write(row_section_start+2,4,tot_res_eff_'+str(list_of_prod_sheets.index(prod_sheet))+',style_nbr_3dec)'
    exec str(prod_sheet)+'.write(row_section_start+4,4,tot_res_int_'+str(list_of_prod_sheets.index(prod_sheet))+',style_nbr_3dec)'
    exec str(prod_sheet)+'.write(row_section_start+5,4,tot_em_int_'+str(list_of_prod_sheets.index(prod_sheet))+',style_nbr_3dec)'


    #write MACRO INDICATORS 
    #top header
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,6,7+NBR_disposals,'Macro indicators (intensities)',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,6,7,'Resource intensities',style_header_center)'''

    #macro economic Resource intensities row headers and values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,6,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,7,r'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
        
    #macro economic TOTAL Resource intensities row headers and values
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,6,'Totals',style_header_lalign)'''
    exec str(prod_sheet)+'.write(row_index+row_section_start+4,7,tot_res_int_'+str(list_of_prod_sheets.index(prod_sheet))+',style_nbr_3dec)'
    # Emission intensities column headers and values 
    for waste_index in range(NBR_disposals):
        #column header
        exec str(prod_sheet)+'''.write(row_section_start+2,8+waste_index,f_array_with_headers['column headings'][1+waste_index]+' intensities',style_header_center)'''
        #values
        for row_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index + row_section_start + 3, 8 + waste_index,w'+str(waste_index)+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()['+str(row_index)+'],style_nbr_3dec)'#        
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,8+waste_index,em_int_'+str(waste_index)+'_'+str(list_of_prod_sheets.index(prod_sheet))+',style_nbr_3dec)'


            
#### Leontief Inverse:
#section starting row:
    row_section_start=2*NBR_sectors+9
#section header
    exec str(prod_sheet)+'.row('+str(row_section_start)+').set_style(style_grey_bold)'
    exec str(prod_sheet)+'.write('+str(row_section_start)+''',0,'Leontief inverse with related outputs endogenised [L=(I-A-Etot)^-1] (It is the same for all structures)',style_grey_bold)'''
        
# write L starting at row_section_start+1
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write('+str(row_index+row_section_start+1)+','+str(col_index+1)+',L['+str(row_index)+']['+str(col_index)+'],style_nbr_3dec)'


    #### Cycle decomposition:
    #write subsection header starting at colummn 0, row 3*NBR_sectors+10
    exec str(prod_sheet)+'.row(3*NBR_sectors+10).set_style(style_grey_bold)'
    exec str(prod_sheet)+'''.write(3*NBR_sectors+10,0,'Cyclic-acyclic decomposition of the inter-sectoral matrix based on Ulanowicz (1983)',style_grey_bold)'''
    
    exec str(prod_sheet)+'''.write(3*NBR_sectors+11,0,'Cyclic component',style_header_lalign)'''
    # write cycle_matrix starting at colummn 0, row 3*NBR_sectors+12
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+3*NBR_sectors+12,col_index+1,Z_array_cyclic_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'
            
    exec str(prod_sheet)+'''.write(4*NBR_sectors+13,0,'Acyclic component',style_header_lalign)'''
    # write acyclic_matrix starting at colummn 0, row 4*NBR_sectors+14
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+4*NBR_sectors+14,col_index+1,Z_array_acyclic_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'    

    
    #### SECTION: Cyclic-acyclic indicators starting at colummn 0, row 5*NBR_sectors+14

    #section starting row:
    row_section_start=5*NBR_sectors+14      

    #SECTION TITLE 
    exec str(prod_sheet)+'.row(row_section_start).set_style(style_grey_bold)'
    exec str(prod_sheet)+'''.write(row_section_start,0,'Cyclic-acyclic indicators',style_grey_bold)'''
    
    #ROW HEADERS for sectors
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'''.write(row_section_start+4+row_index,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''     
    #row header for totals
    exec str(prod_sheet)+'''.write(row_section_start+5+row_index,0,'Totals',style_header_lalign)'''
   
    ## COLUMN HEADERS OF indicators

    ##cyclic flows COLUMN HEADERS section
    #cyclic flows top level headers
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,1,3,'Cyclic flows within the inter-sectoral matrix',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,1,3,'Cycling throughput',style_header_center)'''
    #cyclic flows disaggregated level headers
    exec str(prod_sheet)+'''.write(row_section_start+3,1,'Self-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,2,'Inter-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,3,'Total',style_header_center)'''
    
    ##System inputs COLUMN HEADERS section
    #System inputs top level headers

    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,5,11,'System inputs (primary resources)',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,5,7,'Cyclic',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,8,10,'Acyclic',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+2,11,'Total inputs',style_header_center)'''
    
    #System inputs disaggregated level headers
    exec str(prod_sheet)+'''.write(row_section_start+3,5,'Self-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,6,'Inter-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,7,'Total',style_header_center)'''
    
    exec str(prod_sheet)+'''.write(row_section_start+3,8,'Direct',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,9,'Indirect',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,10,'Total',style_header_center)'''
    
    exec str(prod_sheet)+'''.write(row_section_start+3,11,'Cyclic + Acyclic',style_header_center)'''
    
    ##System outputs COLUMN HEADERS section
    #System outputs top level headers
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,13,21,'System outputs (final goods and emissions)',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,13,14,f_array_with_headers['column headings'][0],style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,15,17,'Cyclic emissions',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,18,20,'Acyclic emissions',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+2,21,'Total emissions',style_header_center)'''
    
    #System outputs disaggregated level headers
    exec str(prod_sheet)+'''.write(row_section_start+3,13,'Direct',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,14,'Indirect',style_header_center)'''    
    
    exec str(prod_sheet)+'''.write(row_section_start+3,15,'Self-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,16,'Inter-cycling',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,17,'Total',style_header_center)'''
    
    exec str(prod_sheet)+'''.write(row_section_start+3,18,'Direct',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,19,'Indirect',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,20,'Total',style_header_center)'''
    
    exec str(prod_sheet)+'''.write(row_section_start+3,21,'Cyclic + Acyclic',style_header_center)'''
    
    ##Total outputs COLUMN HEADERS section
    #Total outputs top level headers
    exec str(prod_sheet)+'''.write_merge(row_section_start+1,row_section_start+1,23,27,'Total outputs',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,23,24,'Cyclic',style_header_center)'''
    exec str(prod_sheet)+'''.write_merge(row_section_start+2,row_section_start+2,25,26,'Acyclic',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+2,27,'Total',style_header_center)'''
    
    #Total outputs disaggregated level headers
    exec str(prod_sheet)+'''.write(row_section_start+3,23,'Self',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,24,'Inter',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,25,'Direct',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,26,'Indirect',style_header_center)'''
    exec str(prod_sheet)+'''.write(row_section_start+3,27,'All',style_header_center)'''
    
    # ------------- VALUES ---------------------

    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index, 1, self_cycling_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,2,inter_cycling_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,3,cycling_throughput_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,1,tot_self_cycling_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,2,tot_inter_cycling_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,3,tot_cycling_throughput_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    
    # ---- Indicators of feeding flows (inputs) to maintain the cyclic component ----#
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,5,self_cycling_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,6,inter_cycling_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,7,feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,5,tot_self_cycling_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,6,tot_inter_cycling_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,7,tot_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    
    # ---- Indicators on straight inputs that generate the acyclic component --------

    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,8,raw_direct_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,9,raw_indirect_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,10,raw_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,11,r'+ str(list_of_prod_sheets.index(prod_sheet))+ '.flatten()[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,8,np.sum(raw_direct_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,9,np.sum(raw_indirect_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,10,tot_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,11,np.sum(r'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    
    # ---- Indicators of final demand----    
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,13,direct_fd_'+ str(list_of_prod_sheets.index(prod_sheet))+ '.flatten()[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,14,indirect_fd_'+ str(list_of_prod_sheets.index(prod_sheet))+ '.flatten()[row_index],style_nbr_3dec)'
    #totals 
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,13,np.sum(direct_fd_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,14,np.sum(indirect_fd_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'        
        
    # ---- Indicators of cycling losses due to the cyclic component and corresponding cyclic inputs----
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,15,self_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,16,inter_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,17,cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,15,tot_self_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,16,tot_inter_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,17,tot_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    
    # ---- Indicators of acyclic emissions (direct and indirect)----
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,18,direct_acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,19,indirect_acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,20,acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,21,total_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,18,np.sum(direct_acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,19,np.sum(indirect_acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,20,np.sum(acyclic_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,21,tot_total_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
    
    # ---- Indicators of the total outputs ----
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,23,total_self_cycling_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,24,total_inter_cycling_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,25,total_direct_acyclic_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,26,total_indirect_acyclic_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
        exec str(prod_sheet)+ '.write(row_section_start+4+row_index,27,total_outputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '.flatten()[row_index],style_nbr_3dec)'
    #totals
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,23,np.sum(total_self_cycling_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,24,np.sum(total_inter_cycling_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,25,np.sum(total_direct_acyclic_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,26,np.sum(total_indirect_acyclic_output_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'
    exec str(prod_sheet)+ '.write(row_section_start+4+row_index+1,27,np.sum(total_outputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ '),style_nbr_3dec)'

#THIS IS SOMETHING i DID BEFORE HAVING CLEARLY THOUGHT ABOUT THE DIRECT/INDIRECT ACYCLIC STRUCTURES, SO I JUST COMMENTED IT OUT. i AM NOT EVEN GOING TO BOTHER TO CHECK IT OUT, MAYBE IT IS CORRECT BUT I WILL DO THE DIREC/INDIRECT ACYCLIC DECOMPOSITION AS PERFORMED IN THE MAIN SPREADSHEET
#    ##Direct -indirect decomposition COLUMN HEADERS section
#    #System outputs top level headers    
#    # dir_feeding_flows_i
#    # indir_feeding_flows_i
#    # dir_straight_inputs_i
#    # indir_straight_inputs_i
#    # dir_total_inputs_i
#    # indir_total_inputs_i
#    # dir_straight_losses_i
#    # indir_straight_losses_i
#    # dir_cycling_losses_i
#    # indir_cycling_losses_i
#    # dir_total_losses_i
#    # indir_total_losses_i
#    exec str(prod_sheet)+ '''.write_merge(row_section_start+1, row_section_start+1, 26,29, 'Direct -indirect decomposition',style_header_center)'''
#    exec str(prod_sheet)+ '''.write_merge(row_section_start+2, row_section_start+2, 26,27, 'Direct flows',style_header_center)'''
#    exec str(prod_sheet)+ '''.write_merge(row_section_start+2, row_section_start+2, 28,29, 'Indirect flows',style_header_center)'''
#    #DIRECT indicators row headers and values     
#    exec str(prod_sheet)+'''.write(row_section_start+3,26,'Cycling inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+3,27, dir_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+4,26,'Straight inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+4,27, dir_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+5,26,'Total inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+5,27, dir_total_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+6,26,'Cycling losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+6,27, dir_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+7,26,'Straight losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+7,27, dir_straight_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+8,26,'Total losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+8,27, dir_total_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#
#    #INDIRECT indicators row headers and values     
#    exec str(prod_sheet)+'''.write(row_section_start+3,28,'Cycling inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+3,29, indir_feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+4,28,'Straight inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+4,29, indir_straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+5,28,'Total inputs ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+5,29, indir_total_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+6,28,'Cycling losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+6,29, indir_cycling_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+7,28,'Straight losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+7,29, indir_straight_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'
#    exec str(prod_sheet)+'''.write(row_section_start+8,28,'Total losses ',style_header_lalign)'''
#    exec str(prod_sheet)+'.write(row_section_start+8,29, indir_total_losses_'+ str(list_of_prod_sheets.index(prod_sheet))+ ',style_nbr_3dec)'

    
#    #Indicators
#    for row_index in range(NBR_sectors):
#        exec str(prod_sheet)+ '.write(5*NBR_sectors+17+ row_index, 1, cycling_throughput_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index], style_nbr_3dec)'    
#        #empty column
#        exec str(prod_sheet)+ '.write(5*NBR_sectors+17+ row_index,3,feeding_flows_'+ str(list_of_prod_sheets.index(prod_sheet))+ '[row_index],style_nbr_3dec)'
#        exec str(prod_sheet)+ '.write(5*NBR_sectors+17+ row_index,4,straight_inputs_'+ str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
#        #empty column
#        exec str(prod_sheet)+'.write(5*NBR_sectors+17+row_index,6,total_losses_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
#        exec str(prod_sheet)+'.write(5*NBR_sectors+17+row_index,7,cycling_losses_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
#        exec str(prod_sheet)+'.write(5*NBR_sectors+17+row_index,8,straight_losses_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
#        exec str(prod_sheet)+'.write(5*NBR_sectors+17+row_index,9,f'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'



# this was an old hyperlink to the corresponding sankey diagram - now the sankey is not even saved
#    tmp=output_filename+'_prod_'+str(list_of_prod_sheets.index(prod_sheet))
#    exec str(prod_sheet)+'''.write(6*NBR_sectors+18,0, xlwt.Formula('HYPERLINK(\"./images/sankey.cycles.'+tmp+'.png\";"Link to a generated sankey diagram representing the cycling structure - will be substituted by Circos diagrams")'),style_link)'''    ### THE PROBLEMS Is THAT LIBREOFFICE does not open the link
    
    
    #### Cyclic and acyclic structures:
    #write subsection header starting at colummn 0, row 6*NBR_sectors+20
    row_section_start=6*NBR_sectors+20
    exec str(prod_sheet)+'''.row(row_section_start).set_style(style_grey_bold)'''
    exec str(prod_sheet)+'''.write(row_section_start,0,'Cyclic and acyclic structures',style_grey_bold)'''
    
    
    ### Cyclic structure
    exec str(prod_sheet)+'''.write(row_section_start+1,0,'Cyclic structure',style_header_lalign_bold)'''
    
    # intersectoral matrix (headers and values)
    for row_index in range(NBR_sectors):
        #row headers intersectoral matrix
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       '''
        #column headers  intersectoral matrix
        exec str(prod_sheet)+'''.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    '''
        for col_index in range(NBR_sectors):              
            #values        
            exec str(prod_sheet)+'.write(row_index+row_section_start+3,col_index+1,Z_array_cyclic_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'

    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,feeding_flows_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    #Total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+5,1+col_index,total_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #final demand
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors,0,style_nbr_3dec)'    
    
    #Emissions 
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,2+NBR_sectors,'Emissions',style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,2+NBR_sectors,feeding_flows_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    #Total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,3+NBR_sectors,'Total outputs',style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,3+NBR_sectors,total_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    
    
    
    ### Acyclic structure         
    row_section_start=7*NBR_sectors+26
    
    exec str(prod_sheet)+'''.write(row_section_start,0,'Acyclic structure',style_header_lalign_bold)'''
    # Intersectoral matrix
    for row_index in range(NBR_sectors):
        #row headers
        exec str(prod_sheet)+'''.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''
        #column headers
        exec str(prod_sheet)+'''.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)'''
        #values
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+2,col_index+1,Z_array_acyclic_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'
    
    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+7*NBR_sectors+26+3,1+col_index,raw_straight_inputs_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[col_index],style_nbr_3dec)'
    #total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,total_straight_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #Final goods
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors,f'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[row_index],style_nbr_3dec)'
    #Emissions
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,2+NBR_sectors,'Emissions',style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,2+NBR_sectors,acyclic_losses_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    #	total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,3+NBR_sectors,'Total outputs',style_header_lalign)'''
    #Values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,3+NBR_sectors,total_straight_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'

    #### Disaggregated Cyclic structures (self and inter-cycling):
    #write subsection header starting at colummn 0, row 6*NBR_sectors+20
    row_section_start=8*NBR_sectors+32
    exec str(prod_sheet)+'''.row(row_section_start).set_style(style_grey_bold)'''
    exec str(prod_sheet)+'''.write(row_section_start,0,'Disaggregated Cyclic structures (self and inter-cycling)',style_grey_bold)'''
    
    
    ### Disaggregated Self-Cyclic structure
    exec str(prod_sheet)+'''.write(row_section_start+1,0,'Self-cycling structure',style_header_lalign_bold)'''
    
    # intersectoral matrix (headers and values)
    for row_index in range(NBR_sectors):
        #row headers intersectoral matrix
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       '''
        #column headers  intersectoral matrix
        exec str(prod_sheet)+'''.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    '''
        for col_index in range(NBR_sectors):              
            #values        
            exec str(prod_sheet)+'.write(row_index+row_section_start+3,col_index+1,Z_array_self_cycling_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'

    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,self_cycling_feeding_flows_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    #Total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+5,1+col_index,total_self_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #final demand
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors,0,style_nbr_3dec)'    
    #Emissions 
    #header
    for i in range(NBR_disposals):
        exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)'''
        #values
        for row_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors+1+i,w_'+str(i)+'_SC_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][0],style_nbr_3dec)'
    #Total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors+1+NBR_disposals,total_self_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    
    
    
    ### Disaggregated Inter-Cyclic structure        
    row_section_start=9*NBR_sectors+38
    
    exec str(prod_sheet)+'''.write(row_section_start,0,'Inter-Cyclic structure ',style_header_lalign_bold)'''
    # Intersectoral matrix
    for row_index in range(NBR_sectors):
        #row headers
        exec str(prod_sheet)+'''.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''
        #column headers
        exec str(prod_sheet)+'''.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)'''
        #values
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+2,col_index+1,Z_array_inter_cycling_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'
    
    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+ row_section_start+3,1+col_index,inter_cycling_feeding_flows_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[col_index],style_nbr_3dec)'
    #total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,total_inter_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #Final goods
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors,0,style_nbr_3dec)'
    #Emissions
    #header
    for i in range(NBR_disposals):
        exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)'''
        #values
        for row_index in range(NBR_sectors):
            exec str(prod_sheet) + '.write(row_index+row_section_start+2,1+NBR_sectors+1+i,w_'+ str(i)+'_IC_'+ str(list_of_prod_sheets.index(prod_sheet))+'[row_index][0],style_nbr_3dec)'
    #	total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)'''
    #Values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors+1+NBR_disposals,total_inter_cycling_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'


    #### Disaggregated Acyclic structures (direct and indirect):
    #write subsection header starting at colummn 0, row 6*NBR_sectors+20
    row_section_start=10*NBR_sectors+44 
    exec str(prod_sheet)+'''.row(row_section_start).set_style(style_grey_bold)'''
    exec str(prod_sheet)+'''.write(row_section_start,0,'Disaggregated Acyclic structures (direct and indirect)',style_grey_bold)'''
    
    
    ### Disaggregated Direct structure
    exec str(prod_sheet)+'''.write(row_section_start+1,0,'Direct acyclic structure',style_header_lalign_bold)'''
    
    # intersectoral matrix (headers and values)
    for row_index in range(NBR_sectors):
        #row headers intersectoral matrix
        exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)       '''
        #column headers  intersectoral matrix
        exec str(prod_sheet)+'''.write(row_section_start+2,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)    '''
        for col_index in range(NBR_sectors):              
            #values        
            exec str(prod_sheet)+'.write(row_index+row_section_start+3,col_index+1,0,style_nbr_3dec)'

    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,raw_direct_straight_inputs_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    #Total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+5,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+5,1+col_index,total_direct_acyclic_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #final demand
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors,direct_fd_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'    
    
    #Emissions
    for i in range(NBR_disposals):
        #header
        exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)'''
        #values
        for row_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors+1+i,w_'+ str(i)+'_DA_' +str(list_of_prod_sheets.index(prod_sheet))+'[row_index][0],style_nbr_3dec)'
    #Total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+2,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+3,1+NBR_sectors+1+NBR_disposals,total_direct_acyclic_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    
    
    
    ### Disaggregated Indirect acyclic structure        
    row_section_start=11*NBR_sectors+50
    
    exec str(prod_sheet)+'''.write(row_section_start,0,'Indirect acyclic structure',style_header_lalign_bold)'''
    # Intersectoral matrix
    for row_index in range(NBR_sectors):
        #row headers
        exec str(prod_sheet)+'''.write(row_index+row_section_start+2,0,Z_array_with_headers['row headings'][row_index],style_header_lalign)'''
        #column headers
        exec str(prod_sheet)+'''.write(row_section_start+1,1+row_index,Z_array_with_headers['column headings'][row_index],style_header_lalign)'''
        #values
        for col_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+2,col_index+1,Z_array_acyclic_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][col_index],style_nbr_3dec)'
    
    #INPUTS
    #Resources
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+3,0,'Resources',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+ row_section_start+3,1+col_index,raw_indirect_straight_inputs_'+str(list_of_prod_sheets.index(prod_sheet))+'.flatten()[col_index],style_nbr_3dec)'
    #total inputs
    #header
    exec str(prod_sheet)+'''.write(row_index+row_section_start+4,0,'Total inputs',style_header_lalign)'''
    #values
    for col_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+4,1+col_index,total_indirect_acyclic_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[col_index],style_nbr_3dec)'
    
    #OUTPUTS
    #Final goods
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors,f_array_with_headers['column headings'][0],style_header_center)'''
    #values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors,indirect_fd_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'
    #Emissions
    for i in range(NBR_disposals):
        #header
        exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors+1+i,f_array_with_headers['column headings'][1+i],style_header_lalign)'''
        #values
        for row_index in range(NBR_sectors):
            exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors+1+i,w_'+ str(i)+'_IA_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index][0],style_nbr_3dec)'
    #	total outputs
    #header
    exec str(prod_sheet)+'''.write(row_section_start+1,1+NBR_sectors+1+NBR_disposals,'Total outputs',style_header_lalign)'''
    #Values
    for row_index in range(NBR_sectors):
        exec str(prod_sheet)+'.write(row_index+row_section_start+2,1+NBR_sectors+1+NBR_disposals,total_indirect_acyclic_output_'+str(list_of_prod_sheets.index(prod_sheet))+'[row_index],style_nbr_3dec)'


time_at_end = time.strftime("%Y%m%d_%H%M")
# I need to redefine the working dir, otherwise files might end up in the circos working dir
os.chdir(dirPath)
#save the workbook as
output_workbook.save(output_filename)
#save all data processed
np.savez(output_binary_file)
#print what have been saved
print('\n++++++++++ WRITING OUTPUT FILES ++++++++++++++++++++++++++++')
print('')
print('... Ended caculations at {0} (yyyymmdd_hhmm)'.format(time_at_end))
print('The analysed data has been writen in the xls file: '+output_filename)
print('The internal arrays has been writen in the binary file: '+output_binary_file)
print('You can also check the log file: '+output_filename+".log")
print('')
print('Done. Enjoy the data. :-)')
#close the logfile (need to be done at the very end, after all prints)
logfile.close()