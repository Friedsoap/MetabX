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

# Config for the circos_interface module
circos_draw = False
circos_execute = True
circos_open_images = True
circos_prod_based_unit = 1000

zero_threshold = 1.0e-10 # threshold under which an absolute value is considered 0 to clean the arrays, also used to check negativity below its negative
max_difference=0.00001 # max_difference represents a percentage (so 1 is 100%)

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

####    Z       ################################################
##      Reading all values from Z worksheet
Z_PRE_array = []
for row_index in range(Z_worksheet.nrows):
     Z_PRE_array.append(Z_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead

####    r       ################################################
##      Reading all values from r
r_PRE_array = []
for row_index in range(r_worksheet.nrows):
     r_PRE_array.append(r_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead

 
####    f       ################################################
##      Reading all values from f
f_PRE_array = []
for row_index in range(f_worksheet.nrows):
     f_PRE_array.append(f_worksheet.row_values(row_index)) # in"Z_PRE_array.append(Z_worksheet.row(row_index))" the rows are lists of  xlrd.sheet.Cell objects. These objects have very few attributes, of which 'value' contains the actual value of the cell and 'ctype' contains the type of the cell. That is why I used row_values instead



##############################################################################
##############################################################################
# counting the disposals to nature based on header names. Originally, the ideas was to make the program flexible and accept any amount of wastes and any amount of final good columns. But this complicates the whole algorithm unnecessarily. So I finally assume there is only one fd as the first column of f_array althought this first implementation recognises all columns starting with w as waste.
NBR_disposals=0
for header_name in f_PRE_array[0][0:]:
    if header_name.startswith('w'):
        NBR_disposals += 1
if NBR_disposals >= 1:
    print('{0} disposals to nature detected'.format(NBR_disposals))    
else:
    sys.exit('''Error: the \'f\' worksheet does not contain any waste because no column header name starts by 'w', exiting.''')

##############################################################################
########## IMPORTANT: the arrays are 2D even if they represent a vector ######
##########              solution: they can be flatten,e.g.: r_array.flatten() 
##############################################################################


# Actual structure dictionary
actual_structure_dictionary=dict()
actual_structure_dictionary['r']=np.array([[c for c in row[1:]] for row in r_PRE_array[0:]]).flatten()
actual_structure_dictionary['Z']=np.array([[c for c in row[1:]] for row in Z_PRE_array[1:]])
actual_structure_dictionary['fd']=np.array([[c for c in row[0:]] for row in f_PRE_array[1:]])[:][:,0:1] # assuming only one column --- could be [:,0]

### check of the correct dimensions of the data input       ##########
# check dimensions of the different arrays and quit if not matching
(Z_rows,Z_cols)=np.shape(actual_structure_dictionary['Z'])
(r_rows,r_cols)=np.shape([actual_structure_dictionary['r']])
(f_rows,f_cols)=np.shape(actual_structure_dictionary['fd'])
if Z_rows != Z_cols:
    sys.exit('the Z matrix is not square, exiting.')
if r_cols != Z_cols:
    sys.exit('the Z matrix and r have not the same number of columns, exiting.')
if Z_rows != f_rows:
    sys.exit('the Z matrix and f have not the same number of rows, exiting.')
NBR_sectors=Z_rows#could be Z_cols as well
print('''The Z matrix has {0} sectors.\n'''.format(NBR_sectors))

# Finishing the actual structure dictionary
actual_structure_dictionary['tot_final_outputs'] = actual_structure_dictionary['fd'].copy()
actual_structure_dictionary['w'] = np.zeros((NBR_sectors,1))
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['w'+str(waste_index)]=np.array([[c for c in row[0:]] for row in f_PRE_array[1:]])[:][:,str(waste_index+1)].reshape((NBR_sectors,1))
    actual_structure_dictionary['tot_final_outputs'] += actual_structure_dictionary['w'+str(waste_index)]
    actual_structure_dictionary['w'] += actual_structure_dictionary['w'+str(waste_index)]
# create an array with all emissions stacked emissions
actual_structure_dictionary['w_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
for sector_index in range(NBR_sectors):
    for waste_index in range(NBR_disposals):
        actual_structure_dictionary['w_stacked'][sector_index][waste_index] =  actual_structure_dictionary['w'+str(waste_index)][sector_index][0]
        
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
label_dictionary['final_outputs_labels']=f_PRE_array[0][0:]


######      check that the PIOT is balanced, i.e. total inputs= total outputs
#t otal_inputs=column sum of Z + r
total_inputs = np.sum(actual_structure_dictionary['Z'],axis=0) + actual_structure_dictionary['r']
actual_structure_dictionary['x'] = np.sum(actual_structure_dictionary['Z'],axis=1).reshape(NBR_sectors,1) + actual_structure_dictionary['fd']
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['x'] = actual_structure_dictionary['x'] + actual_structure_dictionary['w'+str(waste_index)]
# raise error if total_inputs are different from total_outputs for more than acceptable value: max_difference
for i_index in range(NBR_sectors):
    if total_inputs[i_index]-actual_structure_dictionary['x'][i_index][0] > max_difference*(total_inputs[i_index]+actual_structure_dictionary['x'][i_index][0])/2 :
        sys.exit('''Error: Total outputs different from total inputs for sector {0}, i.e, the IOT is not balanced, exiting.'''.format(i_index))
        
##############################################################################
##############################################################################
print(
'\n++++++++++   DATA ANALYSIS   +++++++++++++++++++++++++++++++++++++++++++++')


######  Calculate the technical coef matrix, endogenising all disposals to nature and calculate the Leontied inverse to be able to operate the PIOT with goods alone
#   name and description of the calculated variables
#   A     technical coefficient matrix for all flows
#   Ei    output coefficient matrices to endogenise the disposals to nature
#   Etot  auxiliar variable
#   L     Leontief inverse matrix taking endogenising all disposals to nature - see Altimiras-Martin (2013) for a detailed explanation
#   r_coefs input (resource) coeficients

actual_structure_dictionary['A']=np.dot(actual_structure_dictionary['Z'], LA.inv(np.diag(actual_structure_dictionary['x'].flatten())))

L_tmp = np.eye(NBR_sectors) - actual_structure_dictionary['A']
actual_structure_dictionary['Etot'] = np.zeros((NBR_sectors,NBR_sectors))
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['E'+str(waste_index)] = np.diag(np.dot(LA.inv(np.diag(actual_structure_dictionary['x'].flatten())), actual_structure_dictionary['w'+str(waste_index)]).flatten())
    actual_structure_dictionary['Etot'] += actual_structure_dictionary['E'+str(waste_index)]
    L_tmp = L_tmp-actual_structure_dictionary['E'+str(waste_index)]

#create Leontief including all wastes
actual_structure_dictionary['L']=LA.inv(L_tmp)

actual_structure_dictionary['r_coefs']=np.dot(actual_structure_dictionary['r'],LA.inv(np.diag(actual_structure_dictionary['x'].flatten())))

# store each product-based structure component in the corresponing key within the product_based_structures dictionary
product_based_structures=dict()
for sector_index in range(NBR_sectors):
    tmp_structure=dict()
    tmp_structure['fd']=np.zeros(NBR_sectors)
    tmp_structure['fd'][sector_index]=1
    tmp_structure['fd']=tmp_structure['fd'].reshape((NBR_sectors,1))
    tmp_structure['x']=np.dot(actual_structure_dictionary['L'],tmp_structure['fd'])
    tmp_structure['r']=np.dot(np.diag(actual_structure_dictionary['r_coefs'].flatten()),tmp_structure['x']).flatten()
    tmp_structure['tot_final_outputs']=tmp_structure['fd'].copy()
    tmp_structure['w']=np.zeros((NBR_sectors,1))
    for waste_index in range(NBR_disposals):
        tmp_structure['w'+str(waste_index)]=np.dot(actual_structure_dictionary['E'+str(waste_index)],tmp_structure['x'])
        tmp_structure['tot_final_outputs'] += tmp_structure['w'+str(waste_index)]
        tmp_structure['w'] += tmp_structure['w'+str(waste_index)]
    tmp_structure['Z']=np.dot(actual_structure_dictionary['A'],np.diag(tmp_structure['x'].flatten()))
    # create an array with all emissions stacked emissions
    tmp_structure['w_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
    for sector_index_2 in range(NBR_sectors):
        for waste_index in range(NBR_disposals):
            tmp_structure['w_stacked'][sector_index_2][waste_index] =  tmp_structure['w'+str(waste_index)][sector_index_2][0]
    product_based_structures['prod_based_struct_'+str(sector_index)]=tmp_structure

##############################################################################
######      Structural analyses    ##########################################
##############################################################################

#### Meso-economic efficiencies (same for all prod struct) ####
print('\n +++++++  Finding meso-efficiencies and other indicators  ++++++++')
meso_efficiencies=np.zeros(NBR_sectors)
for i in range(NBR_sectors):
    meso_efficiencies[i] = (sum(actual_structure_dictionary['Z'][i,:]) + actual_structure_dictionary['fd'].flatten()[i])/(sum(actual_structure_dictionary['Z'][:,i]) + actual_structure_dictionary['r'][i])


#### TOP-LEVEL MACRO INDICATORS ####

## resource efficiencies, intensities and emission intensity for the whole economy
actual_structure_dictionary['tot_res_eff']=sum(actual_structure_dictionary['fd'].flatten())/sum(actual_structure_dictionary['r'])
actual_structure_dictionary['tot_res_int']=1/actual_structure_dictionary['tot_res_eff']

## TOP-LEVEL Emission intensities 
# for the whole economy
actual_structure_dictionary['tot_em_int']=0
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['tot_em_int'] = actual_structure_dictionary['tot_em_int'] + np.sum(actual_structure_dictionary['w'+str(waste_index)].flatten())/np.sum(actual_structure_dictionary['fd'].flatten())

# and for each prod struct
for sector_index in range(NBR_sectors):
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_eff']=sum(product_based_structures['prod_based_struct_'+str(sector_index)]['fd'].flatten())/sum(product_based_structures['prod_based_struct_'+str(sector_index)]['r'])
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_int']=1/product_based_structures['prod_based_struct_'+str(sector_index)]['tot_res_eff']
    product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int']=0
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int']=product_based_structures['prod_based_struct_'+str(sector_index)]['tot_em_int'] + np.sum(product_based_structures['prod_based_struct_'+str(sector_index)]['w'+str(waste_index)].flatten())/np.sum(product_based_structures['prod_based_struct_'+str(sector_index)]['fd'].flatten())


##############################################################################
#### CYCLIC-ACYCLIC/DIRECT-INDIRECT DECOMPOSITION OF 
#### ALL PRODUCT-BASED STRUCTURES AND THE AGGREGATED STRUCTURE   
##############################################################################

# initialise variables for the aggregate structure: they will be built as the
# product-based structures are found to avoid another iteration
# nxn arrays
actual_structure_dictionary['Zc'] = np.zeros((NBR_sectors,NBR_sectors))
actual_structure_dictionary['Zind'] = np.zeros((NBR_sectors,NBR_sectors))
actual_structure_dictionary['Zind_c'] = np.zeros((NBR_sectors,NBR_sectors))
actual_structure_dictionary['Zind_ac'] = np.zeros((NBR_sectors,NBR_sectors))
actual_structure_dictionary['Zind_ac_c'] = np.zeros((NBR_sectors,NBR_sectors))
actual_structure_dictionary['Zind_ac_a'] = np.zeros((NBR_sectors,NBR_sectors))
# 1xn arrays
actual_structure_dictionary['cycling_throughput'] = np.zeros(NBR_sectors)
actual_structure_dictionary['rind_ac'] = np.zeros(NBR_sectors)
actual_structure_dictionary['rind_ac_a'] = np.zeros(NBR_sectors)
actual_structure_dictionary['rind_ac_c'] = np.zeros(NBR_sectors)
actual_structure_dictionary['c_ind'] = np.zeros(NBR_sectors)
actual_structure_dictionary['c_dir'] = np.zeros(NBR_sectors)
actual_structure_dictionary['rc_dir'] = np.zeros(NBR_sectors)
actual_structure_dictionary['ra_dir'] = np.zeros(NBR_sectors)
# nx1 arrays
actual_structure_dictionary['find'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['fdir'] = np.zeros((NBR_sectors,1))

actual_structure_dictionary['wind_ac_a'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['wind_ac_c'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['wind_c'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['wc_dir'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['wa_dir'] = np.zeros((NBR_sectors,1))

actual_structure_dictionary['xind_ac_a'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['xind_ac_c'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['xind_c'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['xc_dir'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['xa_dir'] = np.zeros((NBR_sectors,1))

actual_structure_dictionary['xc'] = np.zeros((NBR_sectors,1))
actual_structure_dictionary['xa'] = np.zeros((NBR_sectors,1))

# indicators
actual_structure_dictionary['CIy'] = 0
actual_structure_dictionary['CIx'] = 0
actual_structure_dictionary['CLIy'] = 0
actual_structure_dictionary['CLIx'] = 0
actual_structure_dictionary['CCIy'] = 0
actual_structure_dictionary['CCIx'] = 0
actual_structure_dictionary['IIy'] = 0
actual_structure_dictionary['IIx'] = 0
actual_structure_dictionary['ILIy'] = 0
actual_structure_dictionary['ILIx'] = 0
actual_structure_dictionary['CIIy'] = 0
actual_structure_dictionary['CIIx'] = 0

# nx1 arrays for m emissions
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['wind_ac_a_'+str(waste_index)] = np.zeros((NBR_sectors,1))
    actual_structure_dictionary['wind_ac_c_'+str(waste_index)] = np.zeros((NBR_sectors,1))
    actual_structure_dictionary['wind_c_'+str(waste_index)] = np.zeros((NBR_sectors,1))
    actual_structure_dictionary['wc_dir_'+str(waste_index)] = np.zeros((NBR_sectors,1))
    actual_structure_dictionary['wa_dir_'+str(waste_index)] = np.zeros((NBR_sectors,1))

print('\n ++++++ CYCLIC-ACYCLIC/DIRECT-INDIRECT DECOMPOSITION OF ALL PRODUCT-BASED STRUCTURES AND THE AGGREGATED STRUCTURE +++++++++')


for struct_index in range(NBR_sectors):
    print('\n +++++ Started structural decomposition for product-based structure'+str(struct_index)+' +++++')
    print('\n +++ Decomposing Z between Zc and Zind +++')
    # finding Zc and Zind
    [product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'], product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'], product_based_structures['prod_based_struct_' +str(struct_index)]['self_cycling']] = cd.cycle_decomposition(product_based_structures['prod_based_struct_'+str(struct_index)]['Z'].__copy__(), product_based_structures['prod_based_struct_'+str(struct_index)]['tot_final_outputs'].__copy__())
    # finding cycling throughput (1xn)
    product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'],1)
    
    print('\n +++ Finding the indirect-cyclic and indirect-acyclic structures +++')
    print('\n + Decomposing Zind between Zind,c and Zind,ac +')
    prop_c=np.zeros((1,3))
    prop_f=np.zeros((1,3))
    prop_z=np.zeros((1,3))
    for sector_index in range(NBR_sectors):
        prop_c[0][sector_index]= product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][sector_index] / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][sector_index])
        prop_f[0][sector_index]= product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][sector_index])
        prop_z[0][sector_index]= np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) / (product_based_structures['prod_based_struct_'+str(struct_index)]['fd'][sector_index][0] + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'][sector_index]) + product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'][sector_index])
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

    # finding wind_ac_a, wind_ac_c and wind_c (as totals, i.e. all emissions generated)
    # the discrimination between different emissions is done later
    print('\n + Finding wind_ac_a, wind_ac_c and wind_c as aggregates +')
    product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'] = np.dot(
    (np.dot(np.ones(NBR_sectors), product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_a']) + product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a']),np.diag(np.ones(NBR_sectors))-np.diag(meso_efficiencies)).reshape((NBR_sectors,1))
    product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c'] = np.dot(
    (np.dot(np.ones(NBR_sectors), product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_c']) + product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c']),np.diag(np.ones(NBR_sectors))-np.diag(meso_efficiencies)).reshape((NBR_sectors,1))
    product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c'] = np.dot(np.ones(NBR_sectors), product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c']).reshape((NBR_sectors,1))
    
    # disaggregation of wind_ac_a, wind_ac_c and wind_c between the NBR_disposals
    # find the total outputs that generate the total emissions wind_ac_a, wind_ac_c and wind_c
    print('\n + Disaggregating wind_ac_a, wind_ac_c and wind_c into the different emission types +')
    product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_a'] = np.dot(LA.inv(actual_structure_dictionary['Etot']), product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_c'] = np.dot(LA.inv(actual_structure_dictionary['Etot']), product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['xind_c'] = np.dot(LA.inv(actual_structure_dictionary['Etot']), product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c'])
    # find the emissions for each emission type
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a_'+str(waste_index)] = np.dot(actual_structure_dictionary['E'+str(waste_index)], product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_a'])
        product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c_'+str(waste_index)] = np.dot(actual_structure_dictionary['E'+str(waste_index)], product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_c'])
        product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c_'+str(waste_index)] = np.dot(actual_structure_dictionary['E'+str(waste_index)], product_based_structures['prod_based_struct_'+str(struct_index)]['xind_c'])

    print('\n +++ Finding the direct-cyclic structure +++')
    print('\n + Finding rc_dir and wc_dir +')
    # Find c_ind
    product_based_structures['prod_based_struct_'+str(struct_index)]['c_ind'] = np.dot(np.dot(np.dot(np.ones(NBR_sectors), product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c']),np.diag(meso_efficiencies)),LA.inv(np.diag(np.ones(NBR_sectors))-np.diag(meso_efficiencies)))
    # Find c_dir
    product_based_structures['prod_based_struct_'+str(struct_index)]['c_dir'] = product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'] - product_based_structures['prod_based_struct_'+str(struct_index)]['c_ind']
    # Find rc_dir and wc_dir
    product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir'] = np.dot(np.dot(product_based_structures['prod_based_struct_' + str(struct_index)]['c_dir'], np.diag(np.ones(NBR_sectors)) - np.diag(meso_efficiencies)), LA.inv(np.diag(meso_efficiencies))).flatten()
    product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir'] = product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir'].reshape((NBR_sectors,1))
    # Disaggregate wc_dir for each emission type
    # find the total outputs
    print('\n + Disaggregating wc_dir into the different emission types +')
    product_based_structures['prod_based_struct_'+str(struct_index)]['xc_dir'] = np.dot(LA.inv(actual_structure_dictionary['Etot']), product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir'])
    # find the emissions for each emission type
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir_'+str(waste_index)] = np.dot(actual_structure_dictionary['E'+str(waste_index)], product_based_structures['prod_based_struct_'+str(struct_index)]['xc_dir'])

    print('\n +++ Finding the direct-acyclic structure +++')
    print('\n + Finding ra_dir +')
    product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'] = product_based_structures['prod_based_struct_'+str(struct_index)]['r'] - product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir'] - product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a'] - product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c']

    print('\n + Finding fdir +')
    product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'] = product_based_structures['prod_based_struct_'+str(struct_index)]['fd'] - product_based_structures['prod_based_struct_'+str(struct_index)]['find']
    
    # error check with the two ways to find fdir
    for i in range(NBR_sectors):
        # clean ra_dir array
        if product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'][i] < zero_threshold:
            product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'][i] = 0
        # raise error if difference with other method is greater than max_difference (defined at top)
        # but only for fdir diferent than 0!
        if product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'][i][0] != 0:
            if (product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'][i][0] - np.dot(product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'],np.diag(meso_efficiencies))[i])/product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'][i][0] > max_difference:
                sys.exit('Error: fdir as fd - find does not equal ra_dir*meso_efficiencies for product_based structure_{0}'.format(str(struct_index)))

    print('\n + Finding wdir +')
    # as aggregate emissions
    product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'] = product_based_structures['prod_based_struct_'+str(struct_index)]['w'] - product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir']-product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c'] -product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'] - product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c']
    # clean wa_dir
    for i in range(NBR_sectors):
        if np.abs(product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'][i][0]) < zero_threshold:
            product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'][i][0] = 0
        elif product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'][i][0] < -zero_threshold:
            sys.exit('Error: wa_dir from product_based structure_{0} is significantly negative'.format(str(struct_index)))
    
    # find xa_dir 
    product_based_structures['prod_based_struct_'+str(struct_index)]['xa_dir'] = np.dot(LA.inv(actual_structure_dictionary['Etot']), product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'])
        
    # for each emission type
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)] = product_based_structures['prod_based_struct_'+str(struct_index)]['w'+str(waste_index)] - product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir_'+str(waste_index)]-product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c_'+str(waste_index)] -product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a_'+str(waste_index)] - product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c_'+str(waste_index)]
        # clean wa_dir_
        for i in range(NBR_sectors):
            if np.abs(product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)][i][0]) < zero_threshold:
                product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)][i][0] = 0
            elif product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)][i][0] < -zero_threshold:
                sys.exit('Error: wa_dir_{1} from product_based structure_{0} is significantly negative'.format(str(struct_index),str(waste_index)))
            # raise error if difference with other method is greater than 0.001%
            # but only for wa_dir_ diferent than 0!
            if product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)][i][0] != 0:
                if (product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)][i][0] - np.dot(product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'],np.diag(np.ones(NBR_sectors)-meso_efficiencies))[i])/product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'][i][0] > max_difference:
                    sys.exit('Error: fdir as fd - find does not equal ra_dir*meso_efficiencies for product_based structure_{0}'.format(str(struct_index)))
                
    print('\n +++ Aggregating the overlaped structures into the cyclic-acyclic meta-structure +++')  
    # intermediate structures
    product_based_structures['prod_based_struct_'+str(struct_index)]['Zcyc'] = product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'] + product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_c']     
    product_based_structures['prod_based_struct_'+str(struct_index)]['Za'] = product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_a']
    # final goods
    product_based_structures['prod_based_struct_'+str(struct_index)]['fa'] = product_based_structures['prod_based_struct_'+str(struct_index)]['fd']
    # primary resources
    product_based_structures['prod_based_struct_'+str(struct_index)]['ra'] =     product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a'] + product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['rc'] = product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir']
    # emissions
    product_based_structures['prod_based_struct_'+str(struct_index)]['wa'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['wc'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c']
    # total outputs
    product_based_structures['prod_based_struct_'+str(struct_index)]['xa'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_a'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xa_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['xc'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xc_dir'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xind_c']    
    # for each emission type
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(struct_index)]['wa_'+str(waste_index)] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)]
        product_based_structures['prod_based_struct_'+str(struct_index)]['wc_'+str(waste_index)] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c_'+str(waste_index)]
    # stacking the emissions together
    product_based_structures['prod_based_struct_'+str(struct_index)]['wc_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
    product_based_structures['prod_based_struct_'+str(struct_index)]['wa_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
    for sector_index in range(NBR_sectors):
        for waste_index in range(NBR_disposals):
            product_based_structures['prod_based_struct_'+str(struct_index)]['wc_stacked'][sector_index][waste_index] =  product_based_structures['prod_based_struct_'+str(struct_index)]['wc_'+str(waste_index)][sector_index][0]
            product_based_structures['prod_based_struct_'+str(struct_index)]['wa_stacked'][sector_index][waste_index] =  product_based_structures['prod_based_struct_'+str(struct_index)]['wa_'+str(waste_index)][sector_index][0]

    print('\n +++ Aggregating the overlaped structures into the direct-indirect meta-structure +++')  
    # intermediate structures
    # No intermediate structures since I do not know Zc_ind nor Zc_dir   

    # final goods: same as previously calculated
    
    # primary resources
    product_based_structures['prod_based_struct_'+str(struct_index)]['rd'] =     product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir'] + product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['ri'] = product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a']
    # emissions
    product_based_structures['prod_based_struct_'+str(struct_index)]['wd'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['wi'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c']
    # for each emission type
    for waste_index in range(NBR_disposals):
        product_based_structures['prod_based_struct_'+str(struct_index)]['wd_'+str(waste_index)] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)]
        product_based_structures['prod_based_struct_'+str(struct_index)]['wi_'+str(waste_index)] =   product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a_'+str(waste_index)] + product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c_'+str(waste_index)]
    # total outputs
    product_based_structures['prod_based_struct_'+str(struct_index)]['xd'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['xc_dir'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xa_dir']
    product_based_structures['prod_based_struct_'+str(struct_index)]['xi'] =   product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_c'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_a'] + product_based_structures['prod_based_struct_'+str(struct_index)]['xind_c']
    # stacking the emissions together
    product_based_structures['prod_based_struct_'+str(struct_index)]['wd_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
    product_based_structures['prod_based_struct_'+str(struct_index)]['wi_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
    for sector_index in range(NBR_sectors):
        for waste_index in range(NBR_disposals):
            product_based_structures['prod_based_struct_'+str(struct_index)]['wd_stacked'][sector_index][waste_index] =  product_based_structures['prod_based_struct_'+str(struct_index)]['wd_'+str(waste_index)][sector_index][0]
            product_based_structures['prod_based_struct_'+str(struct_index)]['wi_stacked'][sector_index][waste_index] =  product_based_structures['prod_based_struct_'+str(struct_index)]['wi_'+str(waste_index)][sector_index][0]

    ### Finding CIy, CIx, CLIx, CCIx,IIy, IIx, RIy and RIx indicators for each product-based structure
    print('\n +++ Finding CIy, CIx, CLIx, CCIx,IIy, IIx, RIy and RIx indicators for each product-based structure +++')
    # cycling
    product_based_structures['prod_based_struct_'+str(struct_index)]['CIy'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['CIx'] = product_based_structures['prod_based_struct_'+str(struct_index)]['CIy'] / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['CLIy'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['wc'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['CLIx'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['CLIy']) / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['CCIy'] = ( np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zcyc']) +  np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['wc']) +
np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['find']))
    product_based_structures['prod_based_struct_'+str(struct_index)]['CCIx'] =     product_based_structures['prod_based_struct_'+str(struct_index)]['CCIy'] / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])
    # indirect
    product_based_structures['prod_based_struct_'+str(struct_index)]['IIy'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['IIx'] = product_based_structures['prod_based_struct_'+str(struct_index)]['IIy'] / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['ILIy'] = np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['wi'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['ILIx'] = product_based_structures['prod_based_struct_'+str(struct_index)]['ILIy'] / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])
    product_based_structures['prod_based_struct_'+str(struct_index)]['CIIy'] = (np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['Zind']) + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['find']) + np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['wi']))
    product_based_structures['prod_based_struct_'+str(struct_index)]['CIIx'] = product_based_structures['prod_based_struct_'+str(struct_index)]['CIIy'] / np.sum(product_based_structures['prod_based_struct_'+str(struct_index)]['x'])

    ###  building the arrays  for the aggregate structure
    print('\n +++ Using the product-based components to build the structural components of aggregated structure +++++')
    actual_structure_dictionary['Zc'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zc'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['Zind'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zind'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['cycling_throughput'] += product_based_structures['prod_based_struct_'+str(struct_index)]['cycling_throughput'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['Zind_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['Zind_ac'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['rind_ac'] += product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['find'] += product_based_structures['prod_based_struct_'+str(struct_index)]['find'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['Zind_ac_a'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_a'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['Zind_ac_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['Zind_ac_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['rind_ac_a'] += product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_a'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['rind_ac_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['rind_ac_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['wind_ac_a'] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['wind_ac_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['wind_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['c_ind'] += product_based_structures['prod_based_struct_'+str(struct_index)]['c_ind'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['c_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['c_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['rc_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['rc_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['wc_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['ra_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['ra_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['fdir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['fdir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['wa_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    # total outputs
    actual_structure_dictionary['xind_ac_a'] += product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_a'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['xind_ac_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['xind_ac_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['xind_c'] += product_based_structures['prod_based_struct_'+str(struct_index)]['xind_c'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['xc_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['xc_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    actual_structure_dictionary['xa_dir'] += product_based_structures['prod_based_struct_'+str(struct_index)]['xa_dir'] * actual_structure_dictionary['fd'][struct_index][0]
    #  disaggregated waste types
    for waste_index in range(NBR_disposals):
        actual_structure_dictionary['wind_ac_a_'+str(waste_index)] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_a_'+str(waste_index)] * actual_structure_dictionary['fd'][struct_index][0]
        actual_structure_dictionary['wind_ac_c_'+str(waste_index)] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_ac_c_'+str(waste_index)] * actual_structure_dictionary['fd'][struct_index][0]
        actual_structure_dictionary['wind_c_'+str(waste_index)] += product_based_structures['prod_based_struct_'+str(struct_index)]['wind_c_'+str(waste_index)] * actual_structure_dictionary['fd'][struct_index][0]
        actual_structure_dictionary['wc_dir_'+str(waste_index)] += product_based_structures['prod_based_struct_'+str(struct_index)]['wc_dir_'+str(waste_index)] * actual_structure_dictionary['fd'][struct_index][0]
        actual_structure_dictionary['wa_dir_'+str(waste_index)] += product_based_structures['prod_based_struct_'+str(struct_index)]['wa_dir_'+str(waste_index)] * actual_structure_dictionary['fd'][struct_index][0]
    
    # building the indicators for the aggregated structure
    actual_structure_dictionary['CIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['CIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['CLIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CLIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd'])     
    actual_structure_dictionary['CLIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CLIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd'])     
    actual_structure_dictionary['CCIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CCIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['CCIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CCIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['IIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['IIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['IIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['IIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['ILIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['ILIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['ILIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['ILIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['CIIy'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CIIy']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 
    actual_structure_dictionary['CIIx'] +=  product_based_structures['prod_based_struct_'+str(struct_index)]['CIIx']* actual_structure_dictionary['fd'][struct_index][0] / np.sum(actual_structure_dictionary['fd']) 

    ###########################################################################
    ###### DRAWING THE CIRCULAR DIAGRAM FOR EACH PROD-BASED STRUCTURE #########
    ###########################################################################
    if circos_draw:
        CircosFolder = os.path.join(dirPath,'circos_graphs_' + time_at_start + '_' + data_filename + '_prod_structure_'+str(struct_index))
        os.chdir(dirPath)
        if os.path.split(CircosFolder)[1] not in os.listdir('./'):
            #CHECK IF DIRECTORY EXISTS. IF not, create it.
            os.mkdir(CircosFolder)            
        unit = circos_prod_based_unit
    
        # draw flow_by_sector: sector_outputs or sector inputs
        circos_interface.draw_circos_diagram(circos_execute, circos_open_images, unit,'merged', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], product_based_structures['prod_based_struct_'+str(struct_index)]['Z'], product_based_structures['prod_based_struct_'+str(struct_index)]['r'].reshape((1,3)), product_based_structures['prod_based_struct_'+str(struct_index)]['fd'], product_based_structures['prod_based_struct_'+str(struct_index)]['w_stacked'])        
        circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], product_based_structures['prod_based_struct_'+str(struct_index)]['Z'], product_based_structures['prod_based_struct_'+str(struct_index)]['r'].reshape((1,3)), product_based_structures['prod_based_struct_'+str(struct_index)]['fd'], product_based_structures['prod_based_struct_'+str(struct_index)]['w_stacked'])

        # draw flow_by_type, specifically the cyclic and acyclic structures
        circos_interface.draw_circos_diagram(circos_execute, circos_open_images, unit,'merged', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], product_based_structures['prod_based_struct_'+str(struct_index)]['Zcyc'], product_based_structures['prod_based_struct_'+str(struct_index)]['rc'].reshape((1,3)), np.zeros((NBR_sectors,1)), product_based_structures['prod_based_struct_'+str(struct_index)]['wc_stacked'], product_based_structures['prod_based_struct_'+str(struct_index)]['Za'], product_based_structures['prod_based_struct_'+str(struct_index)]['ra'].reshape((1,3)), product_based_structures['prod_based_struct_'+str(struct_index)]['fd'], product_based_structures['prod_based_struct_'+str(struct_index)]['wa_stacked'])
        circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], product_based_structures['prod_based_struct_'+str(struct_index)]['Zcyc'], product_based_structures['prod_based_struct_'+str(struct_index)]['rc'].reshape((1,3)), np.zeros((NBR_sectors,1)), product_based_structures['prod_based_struct_'+str(struct_index)]['wc_stacked'], product_based_structures['prod_based_struct_'+str(struct_index)]['Za'], product_based_structures['prod_based_struct_'+str(struct_index)]['ra'].reshape((1,3)), product_based_structures['prod_based_struct_'+str(struct_index)]['fd'], product_based_structures['prod_based_struct_'+str(struct_index)]['wa_stacked'])  


print('\n +++ Aggregating the overlaped structures of the aggregated structure into the cyclic-acyclic meta-structure +++')  
# intermediate structures
actual_structure_dictionary['Zcyc'] = actual_structure_dictionary['Zc'] + actual_structure_dictionary['Zind_c'] + actual_structure_dictionary['Zind_ac_c']        
actual_structure_dictionary['Za'] = actual_structure_dictionary['Zind_ac_a']
# final goods
actual_structure_dictionary['fa'] = actual_structure_dictionary['fd']
# primary resources
actual_structure_dictionary['ra'] = actual_structure_dictionary['rind_ac_a'] + actual_structure_dictionary['ra_dir']
actual_structure_dictionary['rc'] = actual_structure_dictionary['rind_ac_c'] + actual_structure_dictionary['rc_dir']
# emissions
actual_structure_dictionary['wa'] = actual_structure_dictionary['wind_ac_a'] + actual_structure_dictionary['wa_dir']
actual_structure_dictionary['wc'] = actual_structure_dictionary['wind_ac_c'] + actual_structure_dictionary['wc_dir'] + actual_structure_dictionary['wind_c']
# for each emission type
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['wa_'+str(waste_index)] = actual_structure_dictionary['wind_ac_a_'+str(waste_index)] + actual_structure_dictionary['wa_dir_'+str(waste_index)]
    actual_structure_dictionary['wc_'+str(waste_index)] = actual_structure_dictionary['wind_ac_c_'+str(waste_index)] + actual_structure_dictionary['wc_dir_'+str(waste_index)] + actual_structure_dictionary['wind_c_'+str(waste_index)]
# stacking the emissions together
actual_structure_dictionary['wc_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
actual_structure_dictionary['wa_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
for sector_index in range(NBR_sectors):
    for waste_index in range(NBR_disposals):
        actual_structure_dictionary['wc_stacked'][sector_index][waste_index] =  actual_structure_dictionary['wc_'+str(waste_index)][sector_index][0]
        actual_structure_dictionary['wa_stacked'][sector_index][waste_index] =  actual_structure_dictionary['wa_'+str(waste_index)][sector_index][0]
# total outputs
actual_structure_dictionary['xa'] = actual_structure_dictionary['xind_ac_a'] + actual_structure_dictionary['xa_dir']
actual_structure_dictionary['xc'] = actual_structure_dictionary['xind_ac_c'] + actual_structure_dictionary['xc_dir'] + actual_structure_dictionary['xind_c']



print('\n +++ Aggregating the overlaped structures of the aggregated structure into the direct-indirect meta-structure +++')  
# intermediate structures
# No intermediate structures since I do not know Zc_ind nor Zc_dir   

# final goods: same as previously calculated

# primary resources
actual_structure_dictionary['rd'] = actual_structure_dictionary['rc_dir'] + actual_structure_dictionary['ra_dir']
actual_structure_dictionary['ri'] = actual_structure_dictionary['rind_ac_c'] + actual_structure_dictionary['rind_ac_a']
# emissions
actual_structure_dictionary['wd'] = actual_structure_dictionary['wc_dir'] + actual_structure_dictionary['wa_dir']
actual_structure_dictionary['wi'] = actual_structure_dictionary['wind_ac_c'] + actual_structure_dictionary['wind_ac_a'] + actual_structure_dictionary['wind_c']
# for each emission type
for waste_index in range(NBR_disposals):
    actual_structure_dictionary['wd_'+str(waste_index)] = actual_structure_dictionary['wc_dir_'+str(waste_index)] + actual_structure_dictionary['wa_dir_'+str(waste_index)]
    actual_structure_dictionary['wi_'+str(waste_index)] = actual_structure_dictionary['wind_ac_c_'+str(waste_index)] + actual_structure_dictionary['wind_ac_a_'+str(waste_index)] + actual_structure_dictionary['wind_c_'+str(waste_index)]
# stacking the emissions together
actual_structure_dictionary['wd_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
actual_structure_dictionary['wi_stacked'] = np.zeros((NBR_sectors, NBR_disposals))
for sector_index in range(NBR_sectors):
    for waste_index in range(NBR_disposals):
        actual_structure_dictionary['wd_stacked'][sector_index][waste_index] =  actual_structure_dictionary['wd_'+str(waste_index)][sector_index][0]
        actual_structure_dictionary['wi_stacked'][sector_index][waste_index] =  actual_structure_dictionary['wi_'+str(waste_index)][sector_index][0]
# total outputs
actual_structure_dictionary['xd'] = actual_structure_dictionary['xc_dir'] + actual_structure_dictionary['xa_dir']
actual_structure_dictionary['xi'] = actual_structure_dictionary['xind_ac_c'] + actual_structure_dictionary['xind_ac_a'] + actual_structure_dictionary['xind_c']


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
#     - arrays: always in blocks of 4 with strict order: 
#            1. intersectoral_matrix [nbr_sectors x nbr_sectors]
#            2. primary_inputs[1 x nbr_sectors]
#            3. final_goods [nbr_sectors x 1]
#            4. emission_matrix [nbr_sectors x nbr_emissions].
#            By doing that the subroutine is flexible to calculate any kind of flow-type decomposition (not yet implemented)
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

###########################################################################
###### DRAWING THE CIRCULAR DIAGRAM FOR THE ACTUAL STRUCTURE     #########
###########################################################################
if circos_draw:
    CircosFolder=os.path.join(dirPath,'circos_graphs_' + time_at_start + '_' + data_filename + '_full_structure')
    os.chdir(dirPath)
    if os.path.split(CircosFolder)[1] not in os.listdir('./'):
        #CHECK IF DIRECTORY EXISTS. IF not, create it.
        os.mkdir(CircosFolder)        
    unit = 1

    # draw flow_by_sector: sector_outputs or sector inputs
    circos_interface.draw_circos_diagram(circos_execute, circos_open_images, unit,'merged', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], actual_structure_dictionary['Z'], actual_structure_dictionary['r'].reshape((1,3)), actual_structure_dictionary['fd'], actual_structure_dictionary['w_stacked'])   
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'sector_outputs', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], actual_structure_dictionary['Z'], actual_structure_dictionary['r'].reshape((1,3)), actual_structure_dictionary['fd'], actual_structure_dictionary['w_stacked'])
    
    # draw flow_by_type, specifically the cyclic and acyclic structures
    circos_interface.draw_circos_diagram(circos_execute, circos_open_images, unit,'merged', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], actual_structure_dictionary['Zcyc'], actual_structure_dictionary['rc'].reshape((1,3)), np.zeros((NBR_sectors,1)), actual_structure_dictionary['wc_stacked'], actual_structure_dictionary['Za'], actual_structure_dictionary['ra'].reshape((1,3)), actual_structure_dictionary['fd'], actual_structure_dictionary['wa_stacked'])   
    circos_interface.draw_circos_diagram(circos_execute,circos_open_images, unit,'symmetrical', 'normalised', 'cyclic_acyclic', 'size_desc',  CircosFolder, data_filename, NBR_sectors, NBR_disposals, label_dictionary['column_sector_labels'], actual_structure_dictionary['Zcyc'], actual_structure_dictionary['rc'].reshape((1,3)), np.zeros((NBR_sectors,1)), actual_structure_dictionary['wc_stacked'], actual_structure_dictionary['Za'], actual_structure_dictionary['ra'].reshape((1,3)), actual_structure_dictionary['fd'], actual_structure_dictionary['wa_stacked'])


#### Draw the sankey diagram for each piot #####################################
#it will save the created drawing as png
#draw_sankeys.sankey_of_cyclic_flows(units, title, NBR_sectors, total_inputs, feeding_flows_all, raw_straight_inputs_all, total_losses_all, cycling_losses_all, acyclic_losses_all, fd_all, Z_array_cyclic, Z_array_acyclic, self_cycling_all,  Images_Path, 'sankey.cycles.all.'+output_filename)




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
###### Saving the analyses for the aggregated structure 
###### in worksheet called 'Actual structure decomposition'
##############################################################################

## create sheet to add images
#out_sheet_all_image = output_workbook.add_sheet('All flows structure Images')
#out_sheet_all_image.insert_bitmap(Images_Path+'/'+'sankey.cycles.all.'+output_filename+'.png', 0, 0)#the insert_bitmap function does not accept pngs...

print('\n +++++ Starting writing the xls for the actual structure +++++')


## 'All flows structure' is called internally out_sheet_all
out_sheet_all = output_workbook.add_sheet('Actual structure decomposition')

### SECTION: Original PIOT structure
# starting row = 0
out_sheet_all.write(0,0, 'Original PIOT', style_grey_bold)
out_sheet_all.row(0).set_style(style_grey_bold)

### intersectoral matrix Z
# column headers - start at third row, second column
i=1 #column index
for column_headers in label_dictionary['column_sector_labels']:
    out_sheet_all.write(2, i, column_headers, style_header_center)
    i += 1

# row headers - start at 1st column row, fourth row
i=3 #row index
for row_headers in label_dictionary['column_sector_labels']:
    out_sheet_all.write(i, 0, row_headers, style_header_lalign)
    i += 1  

# data -  starts at fourth row and second column
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+3, col_index+1, actual_structure_dictionary['Z'][row_index][col_index], style_nbr_3dec)

### primary resources (r)
# headings
out_sheet_all.write(NBR_sectors+3, 0, label_dictionary['resource_labels'], style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(NBR_sectors+3, col_index+1, actual_structure_dictionary['r'][col_index], style_nbr_3dec)

### total inputs (x)
#  header 
out_sheet_all.write(NBR_sectors+4, 0, 'Total inputs', style_header_center)
# data 
for col_index in range(NBR_sectors):
    out_sheet_all.write(NBR_sectors+4, col_index+1, actual_structure_dictionary['x'].flatten()[col_index], style_nbr_3dec)

### final goods and wastes (fd) 
# column headers for final goods AND wastes start
i=NBR_sectors+1#row index 
for column_headers in label_dictionary['final_outputs_labels']:
    out_sheet_all.write(2, i, column_headers, style_header_center)
    i+=1
    
# data for final goods ONLY
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+3, NBR_sectors+1, actual_structure_dictionary['fd'].flatten()[row_index], style_nbr_3dec)
# data for wastes ONLY
for waste_index in range(NBR_disposals):
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+3, 1+NBR_sectors+1+waste_index, actual_structure_dictionary['w'+str(waste_index)].flatten()[row_index], style_nbr_3dec)

### total outputs
# header - start at column 1+NBR_sectors+1+NBR_disposals, fourth row
out_sheet_all.write(2, 1+NBR_sectors+1+NBR_disposals, 'Total outputs', style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+3,  1+NBR_sectors+1+NBR_disposals,  actual_structure_dictionary['x'].flatten()[row_index],  style_nbr_3dec)
    
### SECTION: Meso- and macro-Indicators on resource efficiency and the cyclic-acylic and direct-indirect structures
# starting row for the section:
row_section_start = NBR_sectors + 6

# section title
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'Meso- and macro-Indicators on resource efficiency and the cyclic-acylic and direct-indirect structures', style_grey_bold)

row_section_start = row_section_start + 1
### meso economic efficiencies
# top headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 0, 1, 'Meso indicators', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 0, 1, 'Resource efficiencies', style_header_center)
# row headers AND values
for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)
        out_sheet_all.write(row_index+row_section_start+3, 1, meso_efficiencies[row_index], style_nbr_3dec)

#####  Aggregated macro indicators
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 3, 8, ' Aggregated macro indicators', style_header_center)

### about to system efficiency
row_section_start = row_section_start + 1
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 3, 4, 'About the system efficiency', style_header_center)
row_section_start = row_section_start + 1
# headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 3, 4, 'Resource efficiency', style_header_center)
out_sheet_all.write(row_section_start+2, 3, 'Resource efficiency', style_header_lalign)
out_sheet_all.write_merge(row_section_start+3, row_section_start+3, 3, 4, 'Intensities per unit of final good', style_header_center)

out_sheet_all.write(row_section_start+4, 3, 'Resource intensity', style_header_lalign)
out_sheet_all.write(row_section_start+5, 3, 'Emission intensity', style_header_lalign)
#indicators
out_sheet_all.write(row_section_start+2, 4, actual_structure_dictionary['tot_res_eff'], style_nbr_3dec)
out_sheet_all.write(row_section_start+4, 4, actual_structure_dictionary['tot_res_int'], style_nbr_3dec)
out_sheet_all.write(row_section_start+5, 4, actual_structure_dictionary['tot_em_int'], style_nbr_3dec)

### about cyclic structure CIy, CIx, CLIx, CCIx
row_section_start = row_section_start - 1
column_start = 5

# headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'About the cyclic structure', style_header_center)
row_section_start = row_section_start + 1
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'Amount of cycling', style_header_center)
out_sheet_all.write(row_section_start+2, column_start, 'CIy', style_header_lalign)
out_sheet_all.write(row_section_start+3, column_start, 'CIx', style_header_lalign)
out_sheet_all.write_merge(row_section_start+4, row_section_start+4, column_start, column_start+1, 'Emissions due to cycling', style_header_center)
out_sheet_all.write(row_section_start+5, column_start, 'CLIy', style_header_lalign)
out_sheet_all.write(row_section_start+6, column_start, 'CCIx', style_header_lalign)
out_sheet_all.write_merge(row_section_start+7, row_section_start+7, column_start, column_start+1, 'Total flows due to cycling', style_header_center)
out_sheet_all.write(row_section_start+8, column_start, 'CCIy', style_header_lalign)
out_sheet_all.write(row_section_start+9, column_start, 'CCIx', style_header_lalign)

# indicators
out_sheet_all.write(row_section_start+2, column_start+1, actual_structure_dictionary['CIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+3, column_start+1, actual_structure_dictionary['CIx'], style_nbr_3dec)
out_sheet_all.write(row_section_start+5, column_start+1, actual_structure_dictionary['CLIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+6, column_start+1, actual_structure_dictionary['CCIx'], style_nbr_3dec)
out_sheet_all.write(row_section_start+8, column_start+1, actual_structure_dictionary['CCIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+9, column_start+1, actual_structure_dictionary['CCIx'], style_nbr_3dec)

### about indirect structure IIy, IIx, RIy and RIx
row_section_start = row_section_start -1
column_start = 7

# headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'About the indirect structure', style_header_center)
row_section_start = row_section_start + 1
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'Amount of indirect flows', style_header_center)
out_sheet_all.write(row_section_start+2, column_start, 'IIy', style_header_lalign)
out_sheet_all.write(row_section_start+3, column_start, 'IIx', style_header_lalign)
out_sheet_all.write_merge(row_section_start+4, row_section_start+4, column_start, column_start+1, 'Emissions due to indirect flows', style_header_center)
out_sheet_all.write(row_section_start+5, column_start, 'ILIy', style_header_lalign)
out_sheet_all.write(row_section_start+6, column_start, 'ILIx', style_header_lalign)
out_sheet_all.write_merge(row_section_start+7, row_section_start+7, column_start, column_start+1, 'Total flows due to indirect flows', style_header_center)
out_sheet_all.write(row_section_start+8, column_start, 'CIIy', style_header_lalign)
out_sheet_all.write(row_section_start+9, column_start, 'CIIx', style_header_lalign)

# indicators
out_sheet_all.write(row_section_start+2, column_start+1, actual_structure_dictionary['IIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+3, column_start+1, actual_structure_dictionary['IIx'], style_nbr_3dec)
out_sheet_all.write(row_section_start+5, column_start+1, actual_structure_dictionary['ILIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+6, column_start+1, actual_structure_dictionary['ILIx'], style_nbr_3dec)
out_sheet_all.write(row_section_start+8, column_start+1, actual_structure_dictionary['CIIy'], style_nbr_3dec)
out_sheet_all.write(row_section_start+9, column_start+1, actual_structure_dictionary['CIIx'], style_nbr_3dec)

### Disaggregated macro- indicators
# top header
row_section_start = row_section_start-2
column_start = 10
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1+NBR_disposals, ' Disaggregated macro indicators (intensities per unit of final good)', style_header_center)
out_sheet_all.write(row_section_start+2,  column_start+1, 'Resource intensities', style_header_center)

# macro economic Resource intensities row headers and values
for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, column_start, label_dictionary['row_sector_labels'][row_index], style_header_lalign)
        out_sheet_all.write(row_index+row_section_start+3, column_start+1, 'only for product-based', style_nbr_3dec)
# macro economic TOTAL Resource intensities row headers and values
out_sheet_all.write(row_index+row_section_start+4, column_start, 'Totals', style_header_lalign)
out_sheet_all.write(row_index+row_section_start+4, column_start+1, 'only for product-based', style_nbr_3dec)

# Emission intensities column headers and values 
for waste_index in range(NBR_disposals):
    #column header
    out_sheet_all.write(row_section_start+2, column_start + 2 + waste_index, label_dictionary['final_outputs_labels'][1+waste_index]+' intensity', style_header_center)
    #values
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index + row_section_start + 3,  column_start + 2 + waste_index, 'only for product-based', style_nbr_3dec)
    out_sheet_all.write(row_index+row_section_start+4, column_start + 2 +waste_index, 'only for product-based', style_nbr_3dec)

### SECTION: Leontief Inverse section :
# section starting row:
row_section_start = row_section_start + NBR_sectors + 10
# section header
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'Leontief inverse with emissions endogenised [L=(I-A-Etot)^-1]', style_grey_bold)

# matrix header
out_sheet_all.write(row_section_start+2, 0, 'Leontief matrix (L)', style_header_lalign)

# write L matrix
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, actual_structure_dictionary['L'][row_index][col_index], style_nbr_3dec)

### SECTION: Intersectoral cyclic and indirect matrices
# section starting row:
row_section_start = row_section_start + NBR_sectors + 4     
    
# section header
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'Intersectoral cyclic and indirect matrices', style_grey_bold)

# header for Cyclic intersectoral flows (Zc)
out_sheet_all.write(row_section_start+2, 0, 'Cyclic intersectoral flows (Zc)', style_header_lalign)
# data for Cyclic intersectoral flows (Zc)
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, actual_structure_dictionary['Zc'][row_index][col_index], style_nbr_3dec)

# rebase the starting point
row_section_start = row_section_start + NBR_sectors + 4 
# header for Indirect intersectoral flows (Zind)
out_sheet_all.write(row_section_start, 0, 'Indirect intersectoral flows (Zind)', style_header_lalign)
# data for Indirect intersectoral flows (Zind)
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index + row_section_start + 1,  col_index+1,  actual_structure_dictionary['Zind'][row_index][col_index],  style_nbr_3dec) 

# rebase the starting point
row_section_start = row_section_start + NBR_sectors + 2
# header for Acyclic indirect intersectoral flows (Zind_ac_a)
out_sheet_all.write(row_section_start, 0, 'Acyclic Indirect intersectoral flows (Zind_ac_a)', style_header_lalign)
# data for Acyclic indirect intersectoral flows (Zind_ac_a)
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+1, col_index+1, actual_structure_dictionary['Zind_ac_a'][row_index][col_index], style_nbr_3dec)

# rebase the starting point
row_section_start = row_section_start + NBR_sectors + 2
# header for indirect intersectoral flows to maintain cycling (Zind_ac_c)
out_sheet_all.write(row_section_start, 0, 'Indirect intersectoral flows to maintain cycling (Zind_ac_c)', style_header_lalign)
# data for indirect intersectoral flows to maintain cycling (Zind_ac_a)
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+1,  col_index+1,  actual_structure_dictionary['Zind_ac_c'][row_index][col_index],  style_nbr_3dec)         

# rebase the starting point
row_section_start = row_section_start + NBR_sectors + 2
# header for indirect intersectoral consumed for cycling (Zind_c)
out_sheet_all.write(row_section_start, 0, 'Indirect intersectoral flows consumed for cycling (Zind_c)', style_header_lalign)
# data for indirect intersectoral consumed for cycling (Zind_c)
for row_index in range(NBR_sectors):
    for col_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+1,  col_index+1,  actual_structure_dictionary['Zind_c'][row_index][col_index],  style_nbr_3dec) 

### SECTION: Overlapped cyclic-acyclic/direct-indirect structural components
#section starting row:
row_section_start= row_section_start + NBR_sectors + 2  

# SECTION TITLE  
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'Overlapped cyclic-acyclic / direct-indirect components', style_grey_bold)

row_section_start = row_section_start+1
# row HEADERS representing the sectors for the whole section
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)   
out_sheet_all.write(row_section_start+5+row_index, 0, 'TOTALS', style_header_lalign)   

### COLUMN HEADERS for the whole section (there are 2 levels of headers)

## Cycling throughput
# top level
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 1, 3, 'Cyclic flows within the inter-sectoral matrix', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 1, 3, 'Cycling throughput', style_header_center)
#cyclic flows disaggregated level headers
out_sheet_all.write(row_section_start+3, 1, 'Direct (c_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 2, 'Indirect (c_ind)', style_header_center)
out_sheet_all.write(row_section_start+3, 3, 'Total (cycling_throughput)', style_header_center)

## System inputs (primary resources)
# top level headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 5, 11, 'System inputs (primary resources)', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 5, 7, 'Cyclic', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 8, 10, 'Acyclic', style_header_center)
out_sheet_all.write(row_section_start+2, 11, 'Total inputs', style_header_center)

# low_level  headers
out_sheet_all.write(row_section_start+3, 5, 'Direct (rc_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 6, 'Indirect (rind_ac_c)', style_header_center)
out_sheet_all.write(row_section_start+3, 7, 'Total cyclic inputs (rc)', style_header_center)

out_sheet_all.write(row_section_start+3, 8, 'Direct (ra_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 9, 'Indirect (rind_ac_a)', style_header_center)
out_sheet_all.write(row_section_start+3, 10,'Total acyclic inputs (ra)',style_header_center)

out_sheet_all.write(row_section_start+3,11,'Total (r)',style_header_center)

##  System outputs (final goods and emissions)
#  top level headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 13, 21, 'System outputs (final goods and emissions)', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 13, 14, 'Final demand', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 15, 17, 'Cyclic emissions', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 18, 20, 'Acyclic emissions', style_header_center)
out_sheet_all.write(row_section_start+2, 21, 'Total Emissions', style_header_center)

# low level headers
out_sheet_all.write(row_section_start+3, 13, 'Direct (fdir)', style_header_center)
out_sheet_all.write(row_section_start+3, 14, 'Indirect (find)', style_header_center)
out_sheet_all.write(row_section_start+3, 15, 'Direct (wc_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 16, 'Indirect (wind_c + wind_ac_c)', style_header_center)
out_sheet_all.write(row_section_start+3, 17, 'Total (wc)', style_header_center)

out_sheet_all.write(row_section_start+3, 18, 'Direct (wa_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 19, 'Indirect (wind_ac_a)', style_header_center)
out_sheet_all.write(row_section_start+3, 20, 'Total (wa)', style_header_center)

out_sheet_all.write(row_section_start+3, 21, 'Total (w)', style_header_center)

## Total outputs
# top level headers
out_sheet_all.write_merge(row_section_start+1, row_section_start+1, 23, 27, 'Total outputs', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 23, 24, 'Cyclic', style_header_center)
out_sheet_all.write_merge(row_section_start+2, row_section_start+2, 25, 26, 'Acyclic', style_header_center)
out_sheet_all.write(row_section_start+2, 27, 'Total', style_header_center)

# low level headers
out_sheet_all.write(row_section_start+3, 23, 'Direct (xc_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 24, 'Indirect (xind_c+xind_ac_c)', style_header_center)
out_sheet_all.write(row_section_start+3, 25, 'Direct (xa_dir)', style_header_center)
out_sheet_all.write(row_section_start+3, 26, 'Indirect (xind_ac_a)', style_header_center)
out_sheet_all.write(row_section_start+3, 27, 'Total (x)', style_header_center)

### Data for the whole section

# Cycling throughput
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 1, actual_structure_dictionary['c_dir'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 2, actual_structure_dictionary['c_ind'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 3, actual_structure_dictionary['cycling_throughput'][row_index], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 1, sum(actual_structure_dictionary['c_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 2, sum(actual_structure_dictionary['c_ind'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 3, sum(actual_structure_dictionary['cycling_throughput'].flatten()), style_nbr_3dec)

# Cyclic System inputs (primary resources)
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 5, actual_structure_dictionary['rc_dir'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 6, actual_structure_dictionary['rind_ac_c'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 7, actual_structure_dictionary['rc'][row_index], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 5, sum(actual_structure_dictionary['rc_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 6, sum(actual_structure_dictionary['rind_ac_c'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 7, sum(actual_structure_dictionary['rc'].flatten()), style_nbr_3dec)

# Acyclic System inputs (primary resources) AND total inputs
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 8, actual_structure_dictionary['ra_dir'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 9, actual_structure_dictionary['rind_ac_a'][row_index], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 10, actual_structure_dictionary['ra'][row_index], style_nbr_3dec)
    # total input
    out_sheet_all.write(row_section_start+4+row_index, 11, actual_structure_dictionary['r'][row_index], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 8, sum(actual_structure_dictionary['ra_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 9, sum(actual_structure_dictionary['rind_ac_a'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 10, sum(actual_structure_dictionary['ra'].flatten()), style_nbr_3dec)
# total input
out_sheet_all.write(row_section_start+4+row_index+1, 11,sum(actual_structure_dictionary['r'].flatten()), style_nbr_3dec)

# System outputs: Final demand AND Cyclic emissions
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 13, actual_structure_dictionary['fdir'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 14, actual_structure_dictionary['find'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 15, actual_structure_dictionary['wc_dir'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 16, actual_structure_dictionary['wind_c'][row_index][0] + actual_structure_dictionary['wind_ac_c'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 17, actual_structure_dictionary['wc'][row_index][0], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 13, sum(actual_structure_dictionary['fdir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 14, sum(actual_structure_dictionary['find'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 15, sum(actual_structure_dictionary['wc_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 16, sum(actual_structure_dictionary['wind_c'].flatten() + actual_structure_dictionary['wind_ac_c'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 17, sum(actual_structure_dictionary['wc'].flatten()), style_nbr_3dec)

# System outputs: Acyclic emissions AND Total Emissions
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 18,  actual_structure_dictionary['wa_dir'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 19,  actual_structure_dictionary['wind_ac_a'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 20, actual_structure_dictionary['wa'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 21, actual_structure_dictionary['w'][row_index][0], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 18, sum(actual_structure_dictionary['wa_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 19, sum(actual_structure_dictionary['wind_ac_a'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 20, sum(actual_structure_dictionary['wa'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 21, sum(actual_structure_dictionary['w'].flatten()), style_nbr_3dec)

# Total outputs: Cyclic, Acyclic	AND Total
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_section_start+4+row_index, 23, actual_structure_dictionary['xc_dir'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 24, actual_structure_dictionary['xind_c'][row_index][0] + actual_structure_dictionary['xind_ac_c'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 25, actual_structure_dictionary['xa_dir'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 26, actual_structure_dictionary['xind_ac_a'][row_index][0], style_nbr_3dec)
    out_sheet_all.write(row_section_start+4+row_index, 27, actual_structure_dictionary['x'][row_index][0], style_nbr_3dec)
#totals
out_sheet_all.write(row_section_start+4+row_index+1, 23, np.sum(actual_structure_dictionary['xc_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 24, np.sum(actual_structure_dictionary['xind_c'].flatten() + actual_structure_dictionary['xind_ac_c'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 25, np.sum(actual_structure_dictionary['xa_dir'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 26, np.sum(actual_structure_dictionary['xind_ac_a'].flatten()), style_nbr_3dec)
out_sheet_all.write(row_section_start+4+row_index+1, 27, np.sum(actual_structure_dictionary['x'].flatten()), style_nbr_3dec)

# this was an old hyperlink to the corresponding sankey diagram - now the sankey is not even saved
#out_sheet_all.write(row_section_start+NBR_sectors+5, 0,  xlwt.Formula('HYPERLINK(\"./images/sankey.cycles.'+output_filename+'.all.png\";"Link to a generated sankey diagram representing the cycling structure - will be substituted by Circos diagrams")'), style_link)    ### THE PROBLEMS Is THAT LIBREOFFICE does not open the link


### Section: Cyclic and acyclic meta-structures
# starting row:
row_section_start = row_section_start + NBR_sectors + 6 

# section header
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'The cyclic-acyclic meta-structure', style_grey_bold)
row_section_start += 1

# section header for the Cyclic structure
out_sheet_all.write(row_section_start+1, 0, 'Cyclic structure', style_header_lalign_bold)

## Zcyc only
for row_index in range(NBR_sectors):
    # row headers 
    out_sheet_all.write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
    # column headers 
    out_sheet_all.write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
    for col_index in range(NBR_sectors):              
        # data    
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, actual_structure_dictionary['Zcyc'][row_index][col_index], style_nbr_3dec)

## Primary resources
# header
out_sheet_all.write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4, 1+col_index, actual_structure_dictionary['rc'][col_index], style_nbr_3dec)

## total inputs (actually = total outputs) 
# header
out_sheet_all.write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5, 1+col_index, actual_structure_dictionary['xc'].flatten()[col_index], style_nbr_3dec)

## final demand
# header
out_sheet_all.write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
# data = 0 here
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 1+NBR_sectors, 0, style_nbr_3dec)
    
## emissions
for waste_index in range(NBR_disposals):
    # header
    out_sheet_all.write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, actual_structure_dictionary['wc_'+str(waste_index)][row_index][0], style_nbr_3dec)

## total outputs
# header
out_sheet_all.write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 3+NBR_sectors, actual_structure_dictionary['xc'].flatten()[row_index], style_nbr_3dec)


### Acyclic structure         
row_section_start = row_section_start + NBR_sectors + 5        
out_sheet_all.write(row_section_start+1, 0, 'Acyclic structure', style_header_lalign_bold)

## Za only
for row_index in range(NBR_sectors):
    # row headers 
    out_sheet_all.write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
    # column headers 
    out_sheet_all.write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
    for col_index in range(NBR_sectors):              
        # data    
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, actual_structure_dictionary['Za'][row_index][col_index], style_nbr_3dec)

## Primary resources
# header
out_sheet_all.write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4, 1+col_index, actual_structure_dictionary['ra'][col_index], style_nbr_3dec)

## total inputs (actually = total outputs) 
# header
out_sheet_all.write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5, 1+col_index, actual_structure_dictionary['xa'].flatten()[col_index], style_nbr_3dec)

## final demand
# header
out_sheet_all.write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 1+NBR_sectors, actual_structure_dictionary['fd'].flatten()[row_index], style_nbr_3dec)
    
## emissions
for waste_index in range(NBR_disposals):
    # header
    out_sheet_all.write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, actual_structure_dictionary['wa_'+str(waste_index)][row_index][0], style_nbr_3dec)

## total outputs
# header
out_sheet_all.write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 3+NBR_sectors, actual_structure_dictionary['xa'].flatten()[row_index], style_nbr_3dec)

### Section The direct-indirect meta-structure
#section starting row:
row_section_start = row_section_start + NBR_sectors + 6

# subsection header
out_sheet_all.row(row_section_start).set_style(style_grey_bold)
out_sheet_all.write_merge(row_section_start, row_section_start, 0, 5, 'The direct-indirect meta-structure', style_grey_bold)

### Direct structure         
row_section_start += 1
out_sheet_all.write(row_section_start+1, 0, 'Direct structure', style_header_lalign_bold)

## Zd only
for row_index in range(NBR_sectors):
    # row headers 
    out_sheet_all.write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
    # column headers 
    out_sheet_all.write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
    for col_index in range(NBR_sectors):              
        # data    
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, 'unknown', style_nbr_3dec)

## Primary resources
# header
out_sheet_all.write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4, 1+col_index, actual_structure_dictionary['rd'][col_index], style_nbr_3dec)

## total inputs (actually = total outputs) 
# header
out_sheet_all.write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5, 1+col_index, actual_structure_dictionary['xd'].flatten()[col_index], style_nbr_3dec)

## final demand
# header
out_sheet_all.write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 1+NBR_sectors, actual_structure_dictionary['fdir'].flatten()[row_index], style_nbr_3dec)
    
## emissions
for waste_index in range(NBR_disposals):
    # header
    out_sheet_all.write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, actual_structure_dictionary['wd_'+str(waste_index)][row_index][0], style_nbr_3dec)

## total outputs
# header
out_sheet_all.write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 3+NBR_sectors, actual_structure_dictionary['xd'].flatten()[row_index], style_nbr_3dec)

### Indirect structure         
row_section_start = row_section_start + NBR_sectors + 5        
out_sheet_all.write(row_section_start+1, 0, 'Indirect structure', style_header_lalign_bold)

## Zi
for row_index in range(NBR_sectors):
    # row headers 
    out_sheet_all.write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
    # column headers 
    out_sheet_all.write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
    for col_index in range(NBR_sectors):              
        # data    
        out_sheet_all.write(row_index+row_section_start+3, col_index+1, 'unknown', style_nbr_3dec)

## Primary resources
# header
out_sheet_all.write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+4, 1+col_index, actual_structure_dictionary['ri'][col_index], style_nbr_3dec)

## total inputs (actually = total outputs) 
# header
out_sheet_all.write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
# data
for col_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+5, 1+col_index, actual_structure_dictionary['xi'].flatten()[col_index], style_nbr_3dec)

## final demand
# header
out_sheet_all.write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 1+NBR_sectors, actual_structure_dictionary['find'].flatten()[row_index], style_nbr_3dec)
    
## emissions
for waste_index in range(NBR_disposals):
    # header
    out_sheet_all.write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        out_sheet_all.write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, actual_structure_dictionary['wi_'+str(waste_index)][row_index][0], style_nbr_3dec)

## total outputs
# header
out_sheet_all.write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
# data
for row_index in range(NBR_sectors):
    out_sheet_all.write(row_index+row_section_start+3, 3+NBR_sectors, actual_structure_dictionary['xi'].flatten()[row_index], style_nbr_3dec)


###############################################################################
####### Saving the structural decomposition for each product-based structure
####### in spreasheets called 'SECTOR-based structure'
###############################################################################

print('\n +++++ Starting writing the xls for each product-based structure +++++')
sheets_dictionary=dict()
for prod_struct in range(NBR_sectors):
    # create a sheet for each product-based structure
    sheets_dictionary['out_sheet_'+str(prod_struct)]=output_workbook.add_sheet(str(label_dictionary['row_sector_labels'][prod_struct])+'-based structure')

    print('\n +++ Writing structural decomposition for product-based structure '+str(prod_struct)+' +++')

    ### SECTION: Product-based structure
    # starting row = 0
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(0,0, str(label_dictionary['row_sector_labels'][prod_struct])+'-based structure', style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(0).set_style(style_grey_bold)

    ### intersectoral matrix Z
    # column headers - start at third row, second column
    i=1 #column index
    for column_headers in label_dictionary['column_sector_labels']:
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(2, i, column_headers, style_header_center)
        i += 1

    # row headers - start at 1st column row, fourth row
    i=3 #row index
    for row_headers in label_dictionary['column_sector_labels']:
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(i, 0, row_headers, style_header_lalign)
        i += 1  

    # data -  starts at fourth row and second column
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+3, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['Z'][row_index][col_index], style_nbr_3dec)

    ### primary resources (r)
    # headings
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(NBR_sectors+3, 0, label_dictionary['resource_labels'], style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(NBR_sectors+3, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['r'][col_index], style_nbr_3dec)

    ### total inputs (x)
    #  header 
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(NBR_sectors+4, 0, 'Total inputs', style_header_center)
    # data 
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(NBR_sectors+4, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['x'].flatten()[col_index], style_nbr_3dec)

    ### final goods and wastes (fd) 
    # column headers for final goods AND wastes start
    i=NBR_sectors+1#row index 
    for column_headers in label_dictionary['final_outputs_labels']:
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(2, i, column_headers, style_header_center)
        i+=1
        
    # data for final goods ONLY
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+3, NBR_sectors+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['fd'].flatten()[row_index], style_nbr_3dec)
    # data for wastes ONLY
    for waste_index in range(NBR_disposals):
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+3, 1+NBR_sectors+1+waste_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['w'+str(waste_index)].flatten()[row_index], style_nbr_3dec)

    ### total outputs
    # header - start at column 1+NBR_sectors+1+NBR_disposals, fourth row
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(2, 1+NBR_sectors+1+NBR_disposals, 'Total outputs', style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+3,  1+NBR_sectors+1+NBR_disposals,  product_based_structures['prod_based_struct_'+str(prod_struct)]['x'].flatten()[row_index],  style_nbr_3dec)
        
    ### SECTION: Meso- and macro-Indicators on resource efficiency and the cyclic-acylic and direct-indirect structures
    # starting row for the section:
    row_section_start = NBR_sectors + 6
    
    # section title
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'Meso- and macro-Indicators on resource efficiency and the cyclic-acylic and direct-indirect structures', style_grey_bold)
    
    row_section_start = row_section_start + 1
    ### meso economic efficiencies
    # top headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 0, 1, 'Meso indicators', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 0, 1, 'Resource efficiencies', style_header_center)
    # row headers AND values
    for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 1, meso_efficiencies[row_index], style_nbr_3dec)
    
    #####  Aggregated macro indicators
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 3, 8, ' Aggregated macro indicators', style_header_center)
    
    ### about to system efficiency
    row_section_start = row_section_start + 1
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 3, 4, 'About the system efficiency', style_header_center)
    row_section_start = row_section_start + 1
    # headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 3, 4, 'Resource efficiency', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 3, 'Resource efficiency', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+3, row_section_start+3, 3, 4, 'Intensities per unit of final good', style_header_center)
    
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4, 3, 'Resource intensity', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, 3, 'Emission intensity', style_header_lalign)
    #indicators
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 4, product_based_structures['prod_based_struct_'+str(prod_struct)]['tot_res_eff'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4, 4, product_based_structures['prod_based_struct_'+str(prod_struct)]['tot_res_int'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, 4, product_based_structures['prod_based_struct_'+str(prod_struct)]['tot_em_int'], style_nbr_3dec)
    
    ### about cyclic structure
    row_section_start = row_section_start - 1
    column_start = 5
    
    # headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'About the cyclic structure', style_header_center)
    row_section_start = row_section_start + 1
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'Amount of cycling', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, column_start, 'CIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, column_start, 'CIx', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+4, row_section_start+4, column_start, column_start+1, 'Emissions due to cycling', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, column_start, 'CLIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+6, column_start, 'CCIx', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+7, row_section_start+7, column_start, column_start+1, 'Total flows due to cycling', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+8, column_start, 'CCIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+9, column_start, 'CCIx', style_header_lalign)
    
    # indicators
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CIy'] , style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CIx'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CLIy'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+6, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CCIx'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+8, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CCIy'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+9, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CCIx'], style_nbr_3dec)
    
    ### about indirect structure
    row_section_start = row_section_start -1
    column_start = 7
    
    # headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'About the indirect structure', style_header_center)
    row_section_start = row_section_start + 1
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1, 'Amount of indirect flows', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, column_start, 'IIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, column_start, 'IIx', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+4, row_section_start+4, column_start, column_start+1, 'Emissions due indirect flows', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, column_start, 'ILIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+6, column_start, 'ILIx', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+7, row_section_start+7, column_start, column_start+1, 'Total flows due indirect flows', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+8, column_start, 'CIIy', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+9, column_start, 'CIIx', style_header_lalign)
    
    # indicators
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['IIy'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['IIx'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['ILIy'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+6, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['ILIx'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+8, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CIIy'], style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+9, column_start+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['CIIx'], style_nbr_3dec)
    
    ### Disaggregated macro- indicators
    # top header
    row_section_start = row_section_start-2
    column_start = 10
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, column_start, column_start+1+NBR_disposals, ' Disaggregated macro indicators (intensities per unit of final good)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2,  column_start+1, 'Resource intensities', style_header_center)
    
    # macro economic Resource intensities row headers and values
    for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, column_start, label_dictionary['row_sector_labels'][row_index], style_header_lalign)
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, column_start+1, 'only for product-based', style_nbr_3dec)
    # macro economic TOTAL Resource intensities row headers and values
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, column_start, 'Totals', style_header_lalign)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, column_start+1, 'only for product-based', style_nbr_3dec)
    
    # Emission intensities column headers and values 
    for waste_index in range(NBR_disposals):
        #column header
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, column_start + 2 + waste_index, label_dictionary['final_outputs_labels'][1+waste_index]+' intensity', style_header_center)
        #values
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index + row_section_start + 3,  column_start + 2 + waste_index, 'only for product-based', style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, column_start + 2 +waste_index, 'only for product-based', style_nbr_3dec)

    ### SECTION: Leontief Inverse section :
    # section starting row:
    row_section_start = row_section_start + NBR_sectors + 10
    # section header
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'Leontief inverse with emissions endogenised [L=(I-A-Etot)^-1]', style_grey_bold)

    # matrix header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 0, 'Leontief matrix (L)', style_header_lalign)

    # write L matrix
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, actual_structure_dictionary['L'][row_index][col_index], style_nbr_3dec)

    ### SECTION: Intersectoral cyclic and indirect matrices
    # section starting row:
    row_section_start = row_section_start + NBR_sectors + 4     
        
    # section header
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'Intersectoral cyclic and indirect matrices', style_grey_bold)

    # header for Cyclic intersectoral flows (Zc)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 0, 'Cyclic intersectoral flows (Zc)', style_header_lalign)
    # data for Cyclic intersectoral flows (Zc)
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['Zc'][row_index][col_index], style_nbr_3dec)

    # rebase the starting point
    row_section_start = row_section_start + NBR_sectors + 4 
    # header for Indirect intersectoral flows (Zind)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start, 0, 'Indirect intersectoral flows (Zind)', style_header_lalign)
    # data for Indirect intersectoral flows (Zind)
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index + row_section_start + 1,  col_index+1,  product_based_structures['prod_based_struct_'+str(prod_struct)]['Zind'][row_index][col_index],  style_nbr_3dec) 

    # rebase the starting point
    row_section_start = row_section_start + NBR_sectors + 2
    # header for Acyclic indirect intersectoral flows (Zind_ac_a)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start, 0, 'Acyclic Indirect intersectoral flows (Zind_ac_a)', style_header_lalign)
    # data for Acyclic indirect intersectoral flows (Zind_ac_a)
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+1, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['Zind_ac_a'][row_index][col_index], style_nbr_3dec)

    # rebase the starting point
    row_section_start = row_section_start + NBR_sectors + 2
    # header for indirect intersectoral flows to maintain cycling (Zind_ac_c)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start, 0, 'Indirect intersectoral flows to maintain cycling (Zind_ac_c)', style_header_lalign)
    # data for indirect intersectoral flows to maintain cycling (Zind_ac_a)
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+1,  col_index+1,  product_based_structures['prod_based_struct_'+str(prod_struct)]['Zind_ac_c'][row_index][col_index],  style_nbr_3dec)         

    # rebase the starting point
    row_section_start = row_section_start + NBR_sectors + 2
    # header for indirect intersectoral consumed for cycling (Zind_c)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start, 0, 'Indirect intersectoral flows consumed for cycling (Zind_c)', style_header_lalign)
    # data for indirect intersectoral consumed for cycling (Zind_c)
    for row_index in range(NBR_sectors):
        for col_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+1,  col_index+1,  product_based_structures['prod_based_struct_'+str(prod_struct)]['Zind_c'][row_index][col_index],  style_nbr_3dec) 

    ### SECTION: Overlapped cyclic-acyclic/direct-indirect structural components
    #section starting row:
    row_section_start= row_section_start + NBR_sectors + 2  

    # SECTION TITLE  
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'Overlapped cyclic-acyclic / direct-indirect components', style_grey_bold)

    row_section_start = row_section_start+1
    # row HEADERS representing the sectors for the whole section
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)   
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+5+row_index, 0, 'TOTALS', style_header_lalign)   

    ### COLUMN HEADERS for the whole section (there are 2 levels of headers)

    ## Cycling throughput
    # top level
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 1, 3, 'Cyclic flows within the inter-sectoral matrix', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 1, 3, 'Cycling throughput', style_header_center)
    #cyclic flows disaggregated level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 1, 'Direct (c_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 2, 'Indirect (c_ind)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 3, 'Total (cycling_throughput)', style_header_center)

    ## System inputs (primary resources)
    # top level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 5, 11, 'System inputs (primary resources)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 5, 7, 'Cyclic', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 8, 10, 'Acyclic', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 11, 'Total inputs', style_header_center)

    # low_level  headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 5, 'Direct (rc_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 6, 'Indirect (rind_ac_c)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 7, 'Total cyclic inputs (rc)', style_header_center)

    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 8, 'Direct (ra_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 9, 'Indirect (rind_ac_a)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 10,'Total acyclic inputs (ra)',style_header_center)

    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3,11,'Total (r)',style_header_center)

    ##  System outputs (final goods and emissions)
    #  top level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 13, 21, 'System outputs (final goods and emissions)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 13, 14, 'Final demand', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 15, 17, 'Cyclic emissions', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 18, 20, 'Acyclic emissions', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 21, 'Total Emissions', style_header_center)

    # low level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 13, 'Direct (fdir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 14, 'Indirect (find)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 15, 'Direct (wc_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 16, 'Indirect (wind_c + wind_ac_c)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 17, 'Total (wc)', style_header_center)

    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 18, 'Direct (wa_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 19, 'Indirect (wind_ac_a)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 20, 'Total (wa)', style_header_center)

    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 21, 'Total (w)', style_header_center)

    ## Total outputs
    # top level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+1, row_section_start+1, 23, 27, 'Total outputs', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 23, 24, 'Cyclic', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start+2, row_section_start+2, 25, 26, 'Acyclic', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 27, 'Total', style_header_center)

    # low level headers
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 23, 'Direct (xc_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 24, 'Indirect (xind_c+xind_ac_c)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 25, 'Direct (xa_dir)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 26, 'Indirect (xind_ac_a)', style_header_center)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+3, 27, 'Total (x)', style_header_center)

    ### Data for the whole section

    # Cycling throughput
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 1, product_based_structures['prod_based_struct_'+str(prod_struct)]['c_dir'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 2, product_based_structures['prod_based_struct_'+str(prod_struct)]['c_ind'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 3, product_based_structures['prod_based_struct_'+str(prod_struct)]['cycling_throughput'][row_index], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 1, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['c_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 2, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['c_ind'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 3, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['cycling_throughput'].flatten()), style_nbr_3dec)

    # Cyclic System inputs (primary resources)
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 5, product_based_structures['prod_based_struct_'+str(prod_struct)]['rc_dir'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 6, product_based_structures['prod_based_struct_'+str(prod_struct)]['rind_ac_c'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 7, product_based_structures['prod_based_struct_'+str(prod_struct)]['rc'][row_index], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 5, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['rc_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 6, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['rind_ac_c'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 7, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['rc'].flatten()), style_nbr_3dec)

    # Acyclic System inputs (primary resources) AND total inputs
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 8, product_based_structures['prod_based_struct_'+str(prod_struct)]['ra_dir'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 9, product_based_structures['prod_based_struct_'+str(prod_struct)]['rind_ac_a'][row_index], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 10, product_based_structures['prod_based_struct_'+str(prod_struct)]['ra'][row_index], style_nbr_3dec)
        # total input
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 11, product_based_structures['prod_based_struct_'+str(prod_struct)]['r'][row_index], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 8, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['ra_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 9, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['rind_ac_a'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 10, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['ra'].flatten()), style_nbr_3dec)
    # total input
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 11,sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['r'].flatten()), style_nbr_3dec)

    # System outputs: Final demand AND Cyclic emissions
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 13, product_based_structures['prod_based_struct_'+str(prod_struct)]['fdir'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 14, product_based_structures['prod_based_struct_'+str(prod_struct)]['find'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 15, product_based_structures['prod_based_struct_'+str(prod_struct)]['wc_dir'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 16, product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_c'][row_index][0] + product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_ac_c'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 17, product_based_structures['prod_based_struct_'+str(prod_struct)]['wc'][row_index][0], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 13, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['fdir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 14, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['find'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 15, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wc_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 16, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_c'].flatten() + product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_ac_c'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 17, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wc'].flatten()), style_nbr_3dec)

    # System outputs: Acyclic emissions AND Total Emissions
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 18,  product_based_structures['prod_based_struct_'+str(prod_struct)]['wa_dir'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 19,  product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_ac_a'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 20, product_based_structures['prod_based_struct_'+str(prod_struct)]['wa'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 21, product_based_structures['prod_based_struct_'+str(prod_struct)]['w'][row_index][0], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 18, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wa_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 19, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wind_ac_a'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 20, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['wa'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 21, sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['w'].flatten()), style_nbr_3dec)

    # Total outputs: Cyclic, Acyclic    AND Total
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 23, product_based_structures['prod_based_struct_'+str(prod_struct)]['xc_dir'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 24, product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_c'][row_index][0] + product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_ac_c'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 25, product_based_structures['prod_based_struct_'+str(prod_struct)]['xa_dir'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 26, product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_ac_a'][row_index][0], style_nbr_3dec)
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index, 27, product_based_structures['prod_based_struct_'+str(prod_struct)]['x'][row_index][0], style_nbr_3dec)
    #totals
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 23, np.sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['xc_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 24, np.sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_c'].flatten() + product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_ac_c'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 25, np.sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['xa_dir'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 26, np.sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['xind_ac_a'].flatten()), style_nbr_3dec)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+4+row_index+1, 27, np.sum(product_based_structures['prod_based_struct_'+str(prod_struct)]['x'].flatten()), style_nbr_3dec)

    # this was an old hyperlink to the corresponding sankey diagram - now the sankey is not even saved
    #sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+NBR_sectors+5, 0,  xlwt.Formula('HYPERLINK(\"./images/sankey.cycles.'+output_filename+'.all.png\";"Link to a generated sankey diagram representing the cycling structure - will be substituted by Circos diagrams")'), style_link)    ### THE PROBLEMS Is THAT LIBREOFFICE does not open the link


    ### Section: Cyclic and acyclic meta-structures
    # starting row:
    row_section_start = row_section_start + NBR_sectors + 6 

    # section header
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'The cyclic-acyclic meta-structure', style_grey_bold)
    row_section_start += 1

    # section header for the Cyclic structure
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+1, 0, 'Cyclic structure', style_header_lalign_bold)

    ## Zcyc only
    for row_index in range(NBR_sectors):
        # row headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
        # column headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
        for col_index in range(NBR_sectors):              
            # data    
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['Zcyc'][row_index][col_index], style_nbr_3dec)

    ## Primary resources
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['rc'][col_index], style_nbr_3dec)

    ## total inputs (actually = total outputs) 
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['xc'].flatten()[col_index], style_nbr_3dec)

    ## final demand
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
    # data = 0 here
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 1+NBR_sectors, 0, style_nbr_3dec)
        
    ## emissions
    for waste_index in range(NBR_disposals):
        # header
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
        # data
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['wc_'+str(waste_index)][row_index][0], style_nbr_3dec)

    ## total outputs
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 3+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['xc'].flatten()[row_index], style_nbr_3dec)


    ### Acyclic structure         
    row_section_start = row_section_start + NBR_sectors + 5        
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+1, 0, 'Acyclic structure', style_header_lalign_bold)

    ## Za only
    for row_index in range(NBR_sectors):
        # row headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
        # column headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
        for col_index in range(NBR_sectors):              
            # data    
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, product_based_structures['prod_based_struct_'+str(prod_struct)]['Za'][row_index][col_index], style_nbr_3dec)

    ## Primary resources
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['ra'][col_index], style_nbr_3dec)

    ## total inputs (actually = total outputs) 
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['xa'].flatten()[col_index], style_nbr_3dec)

    ## final demand
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 1+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['fd'].flatten()[row_index], style_nbr_3dec)
        
    ## emissions
    for waste_index in range(NBR_disposals):
        # header
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
        # data
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['wa_'+str(waste_index)][row_index][0], style_nbr_3dec)

    ## total outputs
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 3+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['xa'].flatten()[row_index], style_nbr_3dec)

    ### Section The direct-indirect meta-structure
    #section starting row:
    row_section_start = row_section_start + NBR_sectors + 6

    # subsection header
    sheets_dictionary['out_sheet_'+str(prod_struct)].row(row_section_start).set_style(style_grey_bold)
    sheets_dictionary['out_sheet_'+str(prod_struct)].write_merge(row_section_start, row_section_start, 0, 5, 'The direct-indirect meta-structure', style_grey_bold)

    ### Direct structure         
    row_section_start += 1
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+1, 0, 'Direct structure', style_header_lalign_bold)

    ## Zd only
    for row_index in range(NBR_sectors):
        # row headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
        # column headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
        for col_index in range(NBR_sectors):              
            # data    
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, 'unknown', style_nbr_3dec)

    ## Primary resources
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['rd'][col_index], style_nbr_3dec)

    ## total inputs (actually = total outputs) 
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['xd'].flatten()[col_index], style_nbr_3dec)

    ## final demand
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 1+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['fdir'].flatten()[row_index], style_nbr_3dec)
        
    ## emissions
    for waste_index in range(NBR_disposals):
        # header
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
        # data
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['wd_'+str(waste_index)][row_index][0], style_nbr_3dec)

    ## total outputs
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 3+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['xd'].flatten()[row_index], style_nbr_3dec)

    ### Indirect structure         
    row_section_start = row_section_start + NBR_sectors + 5        
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+1, 0, 'Indirect structure', style_header_lalign_bold)

    ## Zi
    for row_index in range(NBR_sectors):
        # row headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 0, label_dictionary['row_sector_labels'][row_index], style_header_lalign)       
        # column headers 
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+row_index, label_dictionary['column_sector_labels'][row_index], style_header_lalign)    
        for col_index in range(NBR_sectors):              
            # data    
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, col_index+1, 'unknown', style_nbr_3dec)

    ## Primary resources
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 0, label_dictionary['resource_labels'][0], style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+4, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['ri'][col_index], style_nbr_3dec)

    ## total inputs (actually = total outputs) 
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 0, 'Total inputs', style_header_lalign)
    # data
    for col_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+5, 1+col_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['xi'].flatten()[col_index], style_nbr_3dec)

    ## final demand
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 1+NBR_sectors, str(label_dictionary['fd_labels']), style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 1+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['find'].flatten()[row_index], style_nbr_3dec)
        
    ## emissions
    for waste_index in range(NBR_disposals):
        # header
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 2+NBR_sectors+waste_index, label_dictionary['waste_labels'][waste_index], style_header_lalign)
        # data
        for row_index in range(NBR_sectors):
            sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 2+NBR_sectors+waste_index, product_based_structures['prod_based_struct_'+str(prod_struct)]['wi_'+str(waste_index)][row_index][0], style_nbr_3dec)

    ## total outputs
    # header
    sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_section_start+2, 3+NBR_sectors, 'Total outputs', style_header_lalign)
    # data
    for row_index in range(NBR_sectors):
        sheets_dictionary['out_sheet_'+str(prod_struct)].write(row_index+row_section_start+3, 3+NBR_sectors, product_based_structures['prod_based_struct_'+str(prod_struct)]['xi'].flatten()[row_index], style_nbr_3dec)


#############################################################################
############   House keeping before ending the program      #################
#############################################################################

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