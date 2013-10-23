

.. _calculations:

=============================================================
Calculations anc checks
=============================================================


Integrity check of original data
--------------------------------

The program checks whether the IOT is balanced.
If the total outputs differ from the total inputs by a difference superior to 0.001%, it stops. You can adjust this by changing the variable called ``max_balancing_difference``.

Data structure of the program
-----------------------------
The idea is to gather all components and indicators of the actual structure together: they are kept in the actual_structure_dictionary which belongs to the dictionary class.
The structural components are:

+------------------------+------------+----------+----------+
| Header row, column 1   | Header 2   | Header 3 | Header 4 |
| (header rows optional) |            |          |          |
+========================+============+==========+==========+
| body row 1, column 1   | column 2   | column 3 | column 4 |
+------------------------+------------+----------+----------+
| body row 2             | ...        | ...      |          |
+------------------------+------------+----------+----------+


==========  ===========   =======
key         dimension     A and B
==========  ===========   =======
False       False         False
True        False         False
False       True          False
True        True          True
==========  ===========   =======
