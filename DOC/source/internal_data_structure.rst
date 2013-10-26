
.. _internal_data_structure:

=============================================================
Internal structure of variables
=============================================================

IOA requires and generates large amount of data; specially in this program, where the idea is to find several indicators and sub-structures associated to an initial IOT and each of its product-based structures, so the data needs to be organised consistenly. 
This section explains how the data representing each IOT and its decompositions is organised so you can find what you need.

Data structure 
---------------------

The components and indicators related to a given structure are kept together even if they are calculated at different stages. The components and indicators related to the actual, aggregated structure are kept in the ``actual_structure_dictionary`` which belongs to the dictionary class.
Similarly, all components and indicators related to each product-based structure are kept together in a similar structure:  the dictionary ``product_based_structures`` contains the *n* product-based structures, each with almost the same data structure as for the the ``actual_structure_dictionary``.

The structure of ``actual_structure_dictionary`` and of each entry in ``product_based_structures`` is :

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
| ``w``                  | n x 1      | Total emissions                    |
+------------------------+------------+------------------------------------+
| ``w``:sub:`m`          | n x 1      | Emission vectors (one for each     |
|                        | (m arrays) | of the *m* different emissions)    |
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
| ``r_coefs``            | 1 x n      |  Input coeficients for pri res     |
+------------------------+------------+------------------------------------+
| ``E``:sub:`m`          | n x n      | Emission coef matrix,1 for each    |
|                        | (m arrays) | of the *m* different emissions     |
+------------------------+------------+------------------------------------+
| ``Etot``               | n x n      | Total emission coef matrix         |
+------------------------+------------+------------------------------------+
| **Macroscopic\  Indicators** See :ref:`macro_ind`                        |
+------------------------+------------+------------------------------------+
| ``tot_res_eff``        | 1          | Total resource efficiency          |
|                        |            | (final goods/primary inputs)       |
+------------------------+------------+------------------------------------+
| ``tot_res_int``        | 1          | Total resource intensity           |
|                        |            | (= 1/ ``tot_res_eff`` )            |
+------------------------+------------+------------------------------------+
| ``tot_em_int``         | 1          | Total emissions intensity          |
|                        |            | (emissions/primary inputs)         |
+------------------------+------------+------------------------------------+
| **Overlapped\  Cyclic-acyclic/Direct-indirect\  Structures**             |
| See :ref:`cy_ac_ind`                                                     |
+------------------------+------------+------------------------------------+
| ``Zc``                 | n x n      | Matrix containing intersectoral    |
|                        |            | cycling                            |
+------------------------+------------+------------------------------------+
| ``Zind``               | n x n      | Matrix containing the remaining    |
|                        |            | intersectoral indirect flows       |
+------------------------+------------+------------------------------------+
| ``cycling_throughput`` | 1 x n      | Amount of cycling through each     |
|                        |            | sector                             |
+------------------------+------------+------------------------------------+
| ``Zind_c``             | n x n      | Intermediate flows used to         |
|                        |            | maintain cycling                   |
+------------------------+------------+------------------------------------+
| ``Zind_ac``            | n x n      | Intermediate flows that feed the   |
|                        |            | acyclic production and carry the   |
|                        |            | resources for ``Zind_c``           |
|                        |            | (will be decompoded between        |
|                        |            | ``Zind_ac_a`` and ``Zind_ac_c``)   |
+------------------------+------------+------------------------------------+
| ``rind_ac``            | 1 x n      | Primary resources associated to    |
|                        |            | ``Zind_ac``(will be decompoded     |
|                        |            | between ``rind_ac_a`` and          |
|                        |            | ``rind_ac_c``)                     |
+------------------------+------------+------------------------------------+
| ``find``               | n x 1      | Final demand produced indirectly   |
+------------------------+------------+------------------------------------+
| ``Zind_ac_a``          | n x n      | Matrix with the indirect acyclic   |
|                        |            | flows producing final goods        |
+------------------------+------------+------------------------------------+
| ``Zind_ac_c``          | n x n      | Matrix with the indirect flows     |
|                        |            | feeding ``Zind_c``                 |
+------------------------+------------+------------------------------------+
| ``rind_ac_a``          | 1 x n      | Primary resources required to      |
|                        |            | produce ``find``                   |
+------------------------+------------+------------------------------------+
| ``rind_ac_c``          | 1 x n      | Primary resources required to      |
|                        |            | maintain cycling indirectly, i.e.  |
|                        |            | ``Zind_c`` and ``Zind_ac_c``       |
+------------------------+------------+------------------------------------+
| ``wind_ac_a``          | n x 1      | Total emissions due to indirect    |
|                        |            | acyclic flows producing final goods|
+------------------------+------------+------------------------------------+
| ``wind_ac_c``          | n x 1      | Total emissions due to indirect    |
|                        |            | flows feeding ``Zind_c``           |
+------------------------+------------+------------------------------------+
| ``wind_c``             | n x 1      | Total emissions due to indirect    |
|                        |            | cycling                            |
+------------------------+------------+------------------------------------+
| ``wind_ac_a_``:sub:`m` | n x 1      | Emission-m due to indirect acyclic |
|                        | (m arrays) | flows producing final goods        |
+------------------------+------------+------------------------------------+
| ``wind_ac_c_``:sub:`m` | n x 1      | Emission-m due to indirect flows   |
|                        | (m arrays) | feeding ``Zind_c``                 |
+------------------------+------------+------------------------------------+
| ``wind_c_``:sub:`m`    | n x 1      | Emission-m due to indirect cycling |
|                        | (m arrays) |                                    |
+------------------------+------------+------------------------------------+
| ``c_ind``              | 1 x n      | Indirect cycling through each      |
|                        |            | sector                             |
+------------------------+------------+------------------------------------+
| ``c_dir``              | 1 x n      | Direct cycling through each        |
|                        |            | sector                             |
+------------------------+------------+------------------------------------+
| ``rc_dir``             | 1 x n      | Primary resources required to      |
|                        |            | maintain cycling directly          |
+------------------------+------------+------------------------------------+
| ``wc_dir``             | n x 1      | Total emissions due to direct      |
|                        |            | cycling                            |
+------------------------+------------+------------------------------------+
| ``wc_dir_``:sub:`m`    | n x 1      | Emission-m due to direct           |
|                        | (m arrays) | cycling                            |
+------------------------+------------+------------------------------------+
| ``ra_dir``             | 1 x n      | Primary resources required to      |
|                        |            | produce final goods directly       |
+------------------------+------------+------------------------------------+
| ``fdir``               | n x 1      | Final goods produced directly      |
+------------------------+------------+------------------------------------+
| ``wa_dir``             | n x 1      | Total emissions due to direct      |
|                        |            | production of final goods          |
+------------------------+------------+------------------------------------+
| ``wa_dir_``:sub:`m`    | n x 1      | Emission-m due to direct           |
|                        | (m arrays) | production of final goods          |
+------------------------+------------+------------------------------------+
| **Cyclic-acyclic\  Structure**                                           |
| See :ref:`cy_ac_ind`                                                     |
+------------------------+------------+------------------------------------+
| ``Zc``                 | n x n      | Same as above                      |
+------------------------+------------+------------------------------------+
| ``Za``                 | n x n      | Matrix containing the intersectoral|
|                        |            | flows to produce final goods       |
+------------------------+------------+------------------------------------+
| ``rc``                 | 1 x n      | Primary resources required to      |
|                        |            | maintain cycling                   |
+------------------------+------------+------------------------------------+
| ``ra``                 | 1 x n      | Primary resources required to      |
|                        |            | produce final goods                |
+------------------------+------------+------------------------------------+
| ``fa``                 | n x 1      | Equals ``fd`` since produced by    |
|                        |            | acyclic structure only;            |
|                        |            | the cyclic produces no final goods |
+------------------------+------------+------------------------------------+
| ``wc``                 | n x 1      | Emission due to                    |
|                        |            | maintaining cycling                |
+------------------------+------------+------------------------------------+
| ``wa``                 | n x 1      | Emission due to                    |
|                        |            | producing final goods              |
+------------------------+------------+------------------------------------+
| ``wc_``:sub:`m`        | n x 1      | Emission-m due to                  |
|                        | (m arrays) | maintaining cycling                |
+------------------------+------------+------------------------------------+
| ``wa_``:sub:`m`        | n x 1      | Emission-m due to                  |
|                        | (m arrays) | producing final goods              |
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
