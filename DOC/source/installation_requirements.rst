
.. _install:

=============================================================
Installation requirements
=============================================================

MetabX does two separate things: decomposes an IOT between its cyclic and acyclic structure and between its direct and indirect structures, for which only the Python components are required.
Additionally, it can draw the data in a circular graph of the results parsing the IOT data in a specific format and for which Circos [MIK09]_ is required, a program originally thought to represent the human genome.
For a rationale why to use circular graphs to view IOTs, see [AAM13]_.

The program is compatible in either Linux and windows machines.

Python requirements
-------------------

First you need to install Python, version 2.7 suffices.

Then, the easiest thing to do is to install Spyder, which is a scientific Integrated Development Interface (IDE). 
Installing Spyderlib will also automatically install almost all python components you need.

In addition to Spyder, you need the module NetworkX.

Reference sites:

* `Python <http://www.python.org/>`_
* `Spyder <https://code.google.com/p/spyderlib/>`_
* `NetworkX <http://networkx.github.io/>`_

.. note::

    In major Linux distributions, you can find them all through your package manager.



Circos requirements
-------------------

This following requirements are only necessary if you wish to draw the circular diagrams of the IOTs.

Circos requires Perl (v5.14.2 suffices), a different scripting language and some of its packages.

Once you installed perl, you need the following packages:

* populate list from circos manual + the one in the book.

Then, you need to install circos. It is recommended to get the latest version their `site <http://circos.ca>`_.







.. rubric:: Bibligraphy

.. [AAM13] Altimiras-Martin, Aleix (2013) PhD  thesis 
.. [MIK09] Krzywinski, Martin I, Jacqueline E Schein, Inanc Birol, Joseph Connors, Randy Gascoyne, Doug Horsman, Steven J Jones, and Marco A Marra. 2009. “Circos: An Information Aesthetic for Comparative Genomics.” Genome Research (June 18). doi:10.1101/gr.092759.109. http://genome.cshlp.org/content/early/2009/06/15/gr.092759.109.abstract.
