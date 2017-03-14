# MDL Node Editor

#### Overview
Explore the power of the MDL language and create your own shaders with the world's first free and open source *MDL Node Editor*. It was developed using Python, Qt's Graphics View Framework and PySide.

#### What is MDL?
Material Definition Language (MDL) is a renderer-agnostic shading language from Nvidia. It's developed for defining physically based materials. MDL defines *what* to compute, not *how* to compute it. It makes possible to get a consistent look between different rendering technologies like ray-tracing, path-tracing or even rasterisation. <br>As a user take a look at the <a href="http://www.mdlhandbook.com/mdl_handbook/index.html">MDL Handbook</a>, as a programmer at the <a href="http://www.mdlhandbook.com/mdl_introduction/index.html">MDL Technical introduction</a>.

#### Features
* Creation and saving of MDL node graphs
* MDL code generation
* Parameter publishing
* Function overloads (one node can have different representations)

#### Binaries
You can find the binary executable inside of the 'bin' folder (Windows only).

#### Usage
* Create Node - right mouse button click
* Create Connection - drag'n'drop between source and destination slots
* Delete existing connection - left mouse button double click
* Switch Overload - middle mouse button click on green square

#### Meaning of input slot appearance
* green - non-editable input
* dark green - editable input
* bright green - published parameter
* dashed circle - input without default value (needs input connection)

#### Limitations
* Nodes with array inputs are not supported
* Only nodes with file system conform names are acceptable
* Every exported MDL-file contains one material with the name identical to the MDL-file name.

