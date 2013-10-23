
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

+------------------------+------------+--------------------------------+
| Key                    | Dim [#1]_  | Content                        |
+========================+============+================================+
| **Structural\  Components**  The aggregate structure is              | 
| taken from :ref:`data_input`; the product-based ones calculated in   |
| :ref:`prod_based_comp`                                               | 
+------------------------+------------+--------------------------------+
| ``r``                  | 1 x n      |  Primary resources vector      |
+------------------------+------------+--------------------------------+
| ``Z``                  | n x n      | Intersectoral matrix           |
+------------------------+------------+--------------------------------+
| ``fd``                 | n x 1      |  Final demand vector [#2]_     |
+------------------------+------------+--------------------------------+
| ``w``:sub:`m`          | n x 1      | Emission vectors (one for each |
|                        |            | of the *m* different emissions)|
+------------------------+------------+--------------------------------+
| ``x``                  | n x 1      | total outputs vector           |
+------------------------+------------+--------------------------------+
| ``tot_final_outputs``  | n x 1      | total final outputs vector     |
|                        |            | (i.e. fd + sum(w\ :sub:`m`\ )) |
+------------------------+------------+--------------------------------+
| **Calculated\  Components** only in ``actual_structure_dictionary``. |
| See :ref:`agg_comp`                                                  |
+------------------------+------------+--------------------------------+
| ``L``                  | n x n      |  Leontief inverse as in [#3]_  |
+------------------------+------------+--------------------------------+
| ``A``                  | n x n      | Technical coeficient matrix    |
+------------------------+------------+--------------------------------+
| ``r_coefs``            | 1 x n      |  input coeficients for pri res |
+------------------------+------------+--------------------------------+
| ``E``:sub:`m`          | n x n      | Emission coef matrix,1 for each|
|                        |            | of the *m* different emissions |
+------------------------+------------+--------------------------------+
| **Calculated\  Indicators** See :ref:`indicators`                    |
+------------------------+------------+--------------------------------+
| ``tot_res_eff``        | 1          | total resource efficiency      |
|                        |            | (final goods/primary inputs)   |
+------------------------+------------+--------------------------------+
| ``tot_res_int``        | 1          | total resource intensity       |
|                        |            | (= 1/ ``tot_res_eff`` )        |
+------------------------+------------+--------------------------------+
| ``tot_em_int``         | 1          | total emissions intensity      |
|                        |            | (emissions/primary inputs)     |
+------------------------+------------+--------------------------------+

.. rubric:: Footnotes

.. [#1] The dimension are for 2D arrays. The IOT has n sectors and m emissions.
.. [#2] Only one column is allowed
.. [#3] The Leontief inverse is calculated by endogenising the emissions, as shown in [AAM13]_

.. rubric:: Bibligraphy

.. [AAM13] Altimiras-Martin, Aleix (2013) PhD  thesis 
