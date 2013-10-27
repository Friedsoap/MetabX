
.. _data_input:

=============================================================
Data input format and its parsing
=============================================================

IOT format (xls)
-------------------

The program has been built to read the IOT from an excel 2003 spreadsheet, which requires a special formating.

.. note::

    Other formats such as newer Excel formats (.xlsx) and from other programs such as Libre Office (.ods) are not accepted; 
    not even text-based formats such as cvs or others. 

The spreadsheet can have any file name but must entail the following 4 spreadsheets **with\  identical\  names**, in any order:

* ``title and comments``, in which only three values from the first column are read:
    
    * the first cell entails the title of the IOT
    * the second cell entails the units
    * the thirs cell entail any comments you wish to add.

* ``Z``, in which the intersectoral matrix and sectoral labels of the IOT is contained:

    * the first row contains all sectoral labels
    * the first column also contains the sectoral labels
    * the intersectoral matrix is aligned with its corresponding row and column labels

* ``r``, in which the primary resources are contained

    * the first cell of the first row contains the title of the primary inputs
    * the rest of the first row contains the primary inputs for all sectors

.. note::
    
    Only one row for primary resources is allowed.

* ``f``, in which the final outputs are contained (i.e. final goods and emissions):

    * the first row contains the labels for the final goods and emissions. 
        
        * the final goods must be in the first column
        * the emissions must all start with the w character (e.g. w0, w_MSW, ...).
        * No limited number of emissions.

    * The column below each label contains the data, in the same order as in the intersectoral matrix.
.. note::
    
    Only one column for final goods is allowed.

Parsing of the xls and storing the different components
-------------------------------------------------------

Storing the labels
------------------

When MetabX is run, it prompts for the input file to read from (formated as above).
It then reads it an stored the information as follows:

All labels are stored in the ``label_dictionary``, as follows

* ``label_dictionary['title']``: stores the title
* ``label_dictionary['units']``: stores the units
* ``label_dictionary['comments']``: stores the comment
* ``label_dictionary['resource_labels']``: stores the label of the primary resources
* ``label_dictionary['row_sector_labels']``: stores the row labels of all sectors
* ``label_dictionary['column_sector_labels']``: stores the column labels of all sectors
* ``label_dictionary['waste_labels']``:  stores the labels of all wastes 
* ``label_dictionary['fd_labels']``: stores the label for the final demand
* ``label_dictionary['final_outputs_labels']``: stores the labels for the final demand and wastes together

Storing the data
------------------

The data is stored in the ``actual_structure_dictionary``, as follows (for more details see next sections :ref:`internal_data_structure` and :ref:`calculations` ):

* ``actual_structure_dictionary['r']``: stores the primary resources
* ``actual_structure_dictionary['Z']``: stores the intersectoral matrix
* ``actual_structure_dictionary['fd']``: stores the final goods
* ``actual_structure_dictionary['w'm]``: stores each waste type where *m* is the type of waste, ordered according to the order provided in the ``f`` spreadsheet.
* ``actual_structure_dictionary['w']``: all emissions aggregated
* ``actual_structure_dictionary['tot_final_outputs']``: all emissions aggregated plus the final goods
* ``actual_structure_dictionary['x']``: total outputs (which are calculated from the above)
