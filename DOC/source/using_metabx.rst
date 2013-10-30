
.. _using_metabx:

=============================================================
Using MetabX
=============================================================

To decompose IOTs
--------------------

You need to install some software before it works (see :ref:`python_req`).
With that software, it should work out of the box to decompose IOTs. 

2 ways to run it: either directly from shell or through Spyder
Explain both





To draw circular diagrams
--------------------------

By default MetabX does not draw the circular diagrams.
Before following the next steps, make sure you have installed all additional software for it (see :ref:`circos_req`).

Then, you need to edit the metabx.py file. 
Specifically, find the ``circos_draw```and set it to True.
This will generate all files required by circos to create the diagrams.

You can also tell MetabX to execute circos for you so you do not need to go and execute it to create each diagram.This will slow down MetabX but save you lots of time. For that, the option ``circos_execute`` needs to be set as True.
In windows machines, you may need to set the program path manually (I did not test it for windows, so feedback will be appreciated).
To do that, open file ``circos_interface.py`` and change the ``circos_program_name`` to the absolute path.
Since windows uses backslashes instead of forward slashes, you need to add the absolute path in this format: 'C:\\path\\to\\circos'.

You can also set MetabX to open the diagrams as they are created by setting ``circos_open_images`` to true.
(note the windows version is not yet implemented, sorry!).
