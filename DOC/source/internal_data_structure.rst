
.. _internal_data_structure:

=============================================================
Internal structure of variables
=============================================================

One of the issues with IOA is the large amount of data and specially in this program where the idea is to find several indicators and sub-structures, the data needs to be organised consistenly. 
So, this section explains how the data concerning the IOT and the decompositions is organised so you can find what you need.

Data structure 
---------------------

The components and indicators related to a given structure are kept together even if they are calculated at different stages. For example, the components and indicators related to the actual, aggregated structure are kept in the ``actual_structure_dictionary`` which belongs to the dictionary class.
Similarly, all components and indicators related to each product-based structure are kept together in a similar structure as ``actual_structure_dictionary``, which in turn are gathered under the array ``product_based_structures``.

The structure of ``actual_structure_dictionary`` is :

+------------------------+------------+------------------------------------+
| Key                    | Dim [#1]_  | Content                            |
+========================+============+====================================+
| **Structural\  Components**  The aggregate structure is                  | 
| taken from :ref:`data_input`; the product-based ones calculated in       |
| :ref:`prod_based_comp`                                                   | 
+------------------------+------------+------------------------------------+
| ``r``                  | 1 x n      |  Primary resources vector          |
+------------------------+------------+------------------------------------+
| ``Z``                  | n x n      | Intersectoral matrix               |
+------------------------+------------+------------------------------------+
| ``fd``                 | n x 1      |  Final demand vector [#2]_         |
+------------------------+------------+------------------------------------+
| ``w``:sub:`m`          | n x 1      | Emission vectors (one for each     |
|                        |            | of the *m* different emissions)    |
+------------------------+------------+------------------------------------+
| ``x``                  | n x 1      | total outputs vector               |
+------------------------+------------+------------------------------------+
| ``tot_final_outputs``  | n x 1      | total final outputs vector         |
|                        |            | (i.e. fd + sum(w\ :sub:`m`\ ))     |
+------------------------+------------+------------------------------------+
| **Calculated\  Components** only in ``actual_structure_dictionary``.     |
| See :ref:`agg_comp`                                                      |
+------------------------+------------+------------------------------------+
| ``L``                  | n x n      |  Leontief inverse as in [#3]_      |
+------------------------+------------+------------------------------------+
| ``A``                  | n x n      | Technical coeficient matrix        |
+------------------------+------------+------------------------------------+
| ``r_coefs``            | 1 x n      |  input coeficients for pri res     |
+------------------------+------------+------------------------------------+
| ``E``:sub:`m`          | n x n      | Emission coef matrix,1 for each    |
|                        |            | of the *m* different emissions     |
+------------------------+------------+------------------------------------+
| **Macroscopic\  Indicators** See :ref:`macro_ind`                        |
+------------------------+------------+------------------------------------+
| ``tot_res_eff``        | 1          | total resource efficiency          |
|                        |            | (final goods/primary inputs)       |
+------------------------+------------+------------------------------------+
| ``tot_res_int``        | 1          | total resource intensity           |
|                        |            | (= 1/ ``tot_res_eff`` )            |
+------------------------+------------+------------------------------------+
| ``tot_em_int``         | 1          | total emissions intensity          |
|                        |            | (emissions/primary inputs)         |
+------------------------+------------+------------------------------------+
| **Cyclic-acyclic/Direct-indirect\  Indicators** See :ref:`cy_ac_ind`     |
+------------------------+------------+------------------------------------+
| ``Zc``                 | n x n      | matrix containing intersectoral    |
|                        |            | cycling                            |
+------------------------+------------+------------------------------------+
| ``Zind``               | n x n      | matrix containing the remaining    |
|                        |            | intersectoral indirect flows       |
+------------------------+------------+------------------------------------+
| ``cycling_throughput`` | 1 x n      | amount of cycling through each     |
|                        |            | sector                             |
+------------------------+------------+------------------------------------+
| ``Zind_c``             | n x n      | intermediate flows used to         |
|                        |            | maintain cycling                   |
+------------------------+------------+------------------------------------+
| ``Zind_ac``            | n x n      | intermediate flows that feed the   |
|                        |            | acyclic production and carry the   |
|                        |            | resources for ``Zind_c``           |
+------------------------+------------+------------------------------------+
| ``rind_ac``            | 1 x n      | primary resources associated to    |
|                        |            | ``Zind_ac``                        |
+------------------------+------------+------------------------------------+
| ``find``               | n x 1      | final demand produced indirectly   |
+------------------------+------------+------------------------------------+



.. note::
   
    The meso-efficiencies are not included in the structural arrays because
    it this would be duplicating the data since they are the same for all
    structures. They are stored separately in the ``meso_efficiencies`` [1xn].
    In other words, for each product-based structure,  ``r`` and  ``w``:sub:`m`
    are the intensities.

    The sectoral resource and emissions intensities are not calculated 
    explicitly since the resources and emissions of the product-based 
    structures *are* the intensities themselves since they represent the 
    resources and emissions required to produce each specific final good.
    
    The sectoral resource and emissions intensities for the aggregate
    structure are not calculated because they are not structurally meaningful.

.. rubric:: Footnotes

.. [#1] The dimension are for 2D arrays: 1xn means one row, n columns.
        Here, IOTs have *n* sectors and *m* emissions. 
        1 means it is a single scalar.
.. [#2] Only one column is allowed
.. [#3] The Leontief inverse is calculated by endogenising the emissions, as shown in [AAM13]_

.. rubric:: Bibligraphy

.. [AAM13] Altimiras-Martin, Aleix (2013) PhD  thesis 
