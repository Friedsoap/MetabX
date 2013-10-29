

.. _calculations:

=============================================================
Calculations and checks
=============================================================


Integrity check of original data
--------------------------------

The program checks whether the IOT is balanced.
If the total outputs differ from the total inputs by a difference superior to 0.001%, it stops. You can adjust this by changing the variable called ``max_balancing_difference``.


.. _iot_comp:

IOT components (aggregate structure)
----------------------------------------------------------

The analysis starts with a given IOT provided by an external file (see :ref:`data_input`). 
All IOT components are read from it and stored into the ``actual_structure_dictionary`` array:

#. the primary resources  ``r``
#. the intersectoral flows ``Z``
#. the emissions: ``w``:sub:`m` (also aggregated as``w``)
#. the final demand ``fd``
#. the total outputs ``x``
#. the total final outputs ``tot_final_outputs`` which is ``fd`` +  ``w``


.. _ioa_comp:

IOA components (aggregate structure)
----------------------------------------------------------

Then, the IOA components are calculated from the original structure and stored into ``actual_structure_dictionary` only:

#. the technical coefficient matrix  ``A``
#. the Leontief matrix ``L``
#. the emission intensity matrices ``E``:sub:`m` and ``Etot``, and
#. the primary resource input coefficients ``r_coefs``. 

The Leontief inverse matrix is calculated using a non-conventional 
method required by PIOTs since they produce several final outputs (final goods and several (*m*) emissions) [AAM13]_.



.. _prod_based_comp:

IOT components (product based structures)
-------------------------------------------

Using the IOA components from above, the IOT components for each product based structure are calculated following [AAM13]_.
Each set of IOT components are stored in  the``product_based_structures`` array, each complete set under ``product_based_structures['prod_based_struct_n]`` where *n* is the sector for which the product-based decomposition was run. Recall NumPy starts numbering at 0, so ``product_based_structures['prod_based_struct_0]`` contains all IOT components of the product-based decomposition for the first sector. The IOT set is the same as for the aggregate structure:

#. the primary resources  ``r``
#. the intersectoral flows ``Z``
#. the emissions: ``w``:sub:`m` (also aggregated as``w``)
#. the final demand ``fd``
#. the total outputs ``x``
#. the total final outputs ``tot_final_outputs`` which is ``fd`` +  ``w``


.. _macro_ind:

Macroscopic Indicators
----------------------

Some top-level macroscopic indicators are then calculated for the aggregated structure and each product-based structure.

.. _overl_str:

Overlapped cyclic-acyclic and direct-indirect structures for the product-based and aggregate structures
-------------------------------------------------------------------------------------------------------

Then, the program run an *n*-iteration to find all cyclic-acyclic and direct-indirect structural elements of the *n* product-based structure. 
At the end of each iteration the cyclic-acyclic and direct-indirect of the aggregated structure is updated with the corresponding share of the product-based structure it has been found. So, at the end of that iteration all product-based structures and the aggregate structure are found.

TODO: explain in detail the calculations.
explain last check of data.


.. _meta_str:

Finding the cyclic-acyclic and direct-indirect meta-structures for the product-based and aggregate structures
-------------------------------------------------------------------------------------------------------------

Since finding the cyclic-acyclic and direct-indirect meta-structures is a matter of aggregating the overlapped cyclic-acyclic and direct-indirect components derived in the previous section, the meta-structures for each product-based structure are calculated at the end of the previous iteration.

However, since all overlapped cyclic-acyclic and direct-indirect components of the aggregate structure must be calculated before they they can be aggregated, finding the cyclic-acyclic and direct-indirect meta-structures for the aggregate structure is only performed after the iteration calculating the product-based structures.

.. _cyc_indic:

Calculating structural indicators of the cyclic structure for the product-based structures
------------------------------------------------------------------------------------------

See [AAM13]_


Calculating structural indicators of the cyclic structure for the aggregated structure
------------------------------------------------------------------------------------------

They are calculated as a weighted average of the former.

.. _ind_indic:

Calculating structural indicators of the indirect structure for the product-based structures
------------------------------------------------------------------------------------------

See [AAM13]_


Calculating structural indicators of the indirect structure for the aggregated structure
------------------------------------------------------------------------------------------

They are calculated as a weighted average of the former.


.. rubric:: Bibligraphy

.. [AAM13] Altimiras-Martin, Aleix (2013) PhD  thesis 