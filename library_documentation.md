# SHL Toolbox Library

## fab
Functions for fabrication output

### add_fab_tags(tag_points, tag_text, tag_size, text_justification=Rhino.Geometry.TextJustification.Center):
Adds fabrication labels as curves to a list of points.

Parameters:
- tag_points: list of point3ds
- tag_text: list of tag text
- tag_size: size of text
- text_justification: Rhino.Geometry.TextJustification.<option goes here>

Return Value:
text_crv_guids: list of guids of the exploded curves making up the labels.

Example:
add_fab_tags([point1,point2, point3], ['wall_1','wall_2','ceiling_1'], 5)

-------------------------------------

## geo
Functions dealing with modifying or extracting geometry information

### get_bounding_dims(brep):
	Returns bounding box x,y,z dims for a brep or many breps

Parameters:
- brep: a brep (is it guid or not?)

Return Value:
dims: a namedtuple with values X, Y, Z.

### get_brep_base_plane(brep):
Returns the xy plane at the brep BoundingBox's lower left corner

### get_brep_height(brep):
Returns the height of a brep's bounding box

### get_brep_plan_cut(brep,cut_height,tolerance):
	Cut a brep through the XY plane at a certain height and return the section curves.
  Note that this function will try to join the resulting section curves.

  Parameters:
  brep: RhinoCommon brep object
  cut_height: height relative to base of BoundingBox to section the brep
  tolerance: tolerance for joining the resulting curves. Suggested: use document tolerance.

  Returns:
  list of RhinoCommon polycurve Objects

  Example usage:
  h = get_brep_height(b)
  section_crvs = get_brep_plan_cut(b,h/2,0.01)

### def get_brep_plan_cut_use_plane(brep,plane,tolerance):
  Cut a brep through a given plane and return the section curves.
  Note that this function will try to join the resulting section curves

  Usage similar to get_plan_cut

### get_internal_angles(pts):
  Get the internal angles of a set of pts representing a counter-clockwise polyline.

  Parameters:
  pts: list of point3ds in counter-clockwise order.

  Returns:
  list of internal angles

### def make_pcurve_ccw(geo_polycurve):
	Accepts a rhino geometry.polycurve object and makes it counter-clockwise. Returns None.\

### get_interior_pt(g_curve,sample_distance,quality=10)
### MUST REVIEW
  get an interior point in the brep by brute-force

  Parameters:
  g_curve: curve geometry
  sample_distance: ???
  quality=10: number of spots to try.

  Returns: point3d."""

### get_polycurve_segment_points(g_polycurve):
### MUST REVIEW
  	gets [startpts,endpts,midpts] list for each segment in RhinoCommon curve geometry

    return [startpts,endpts,midpts]

### get_extreme_srf(brep,h_tol,top=True):
  get the surface at the top or bottom of the brep.
  Algorithm:
	1. pick n random pts on each surface, P
	2. get the 3 lowest points in P (disabled for now; just does straight averaging)
	3. determine their dot product with the unit z and their avg height
	4. throw out all surfaces that aren't within the dot product threshold.
	5. of the remaining surfaces, sort to get the lowest one. if any of them have a height within the
	height tolerance, select them as well.
	6. return these lowest srfs.

  Parameters:
  brep: RhinoCommon brep Geometry
  h_tol: height tolerance (???)
  top=True: True for top, False for bottom surface

  Returns:
  extreme_surfaces: ???

### brepClosestPoint(b1,b2,precision):
  Obtain the closest points on two breps
  Algorithm:
  - Pick a random point p1_0 on b1, and get the point p2_0 closest to it on b2.
  - Pick the point p1_1 on b1 closest to p2_0 ... repeat iteratively.

  Parameters:
  b1, b2: breps to search for closest points on
  precision: number of iterations for search Algorithm

  Returns:
  pt1,pt2 : list of Point3ds closest to one-another on b1 and b2, respectively

### multi_test_in_or_out(test_crv, vols):
### MUST REVIEW
  tests midpoint of curve for containment inside one of several volumes.
  Returns True if point is inside at least one of the volumes, otherwise False

### check_planar_curves_collision(crvs):
  curves must be planar, returns True if any two curves overlap

### trim_boundary(e_crvs,cb_crvs,tol,inside=True):
### MUST REVIEW
  trim curves by closed boundary curves.
  NOTE: assumes redraw is turned off. assumes curves are planar.
  future versions to use projection method to avoid these assumptions.

  Parameters:
	e_crvs: etch curves to be trimmed
	cb_crvs: closed boundary curves
	tol: tolerance. document tolerance recommended
	inside=True: trim the inside if true, trim outside if false
	returns the trimmed curves.



  Returns:
  curves : list of curves kept.


-------------------------------------

## layers
Functions for layer modification and assignment
-


## rhino_util
Rhino object utility functions (e.g. converting between RhinoCommon types)

-

## util
General non-geometric utilities

### equidistant_hsv_color(num,saturation):
	"""returns tuple of colours with equidistantly spaced hue"""
   Parameters:
   num: number of colours
   saturation: saturation value (0.0 - 1.0)

   returns:
   colours: list of rgb colours as tuples.

### def frange(start,stop,step):
	floating point range. output vals will not exceed the stop param.

  Parameters:
		start: start of range
		stop: end of range
		step: increment

  Returns:
		list of floats

### num_div(num,divisor):
_TODO: REMOVE_
	returns number of divisors. posibly not necessary w/ divmod"""

### number_to_letter(num,start=0,upper=True,append=True):
  	convert int to uppercase letter. ***will wrap if out of alphabet bounds***
    DEV NOTES: still a bug in here for ~26

    Parameters:
  		num: int
  		start=0: base number corresponding to 'a'
  		upper=True: convert to upper
  		append=True: append when wrapping.

    Returns:
  		letter: character corresponding to number

### dotprod(a,b):
  dot product for vectors represented as lists

### xprod(a,b)
  cross product for vectors represented as lists

### innerangle(a,b,radians=False):
  inner angle of two vector3ds. Radians or degrees.

### partition_objects_by_attr(objects,attribute,reverse_bool=False):
  split up a list of objects by the values of a certain attribute.

  Parameters:
		objects: list of objects
		attribute: str of attribute to partition by.
		reverse: reverse the sorting order for the partition

  Returns:
		object[][]: list of lists of objects partitioned by the attribute.

    Example:
    objects = [Object 1 {colour: blue}, Object 2 {colour: red}, Object 3 {colour: blue}, Object 4 {colour: blue}, Object 5 {colour: green}]
    partitioned = partition_objects_by_attr(objects)

    paritioned = [ [Object 1,Object 3,Object 4], [Object 5], [Object 2] ]

..........other stuff........

```
C:\Users\[YOUR_USER_NAME]\AppData\Roaming\McNeel\Rhinoceros\6.0\scripts
```
If you do not have a scripts directory, add one yourself to the 6.0 directory.

2. Copy shl_toolbox_lib directory to the scripts directory

3. You can now edit the commands in shl-toolbox/commands in the editor of your choice and run them directly in the Rhino Python script editor.

_TODO: determine best way to use libraries_
### Project

What things you need to install the software and how to install them

```
Give examples
```

### Compiling

The goal of compilation is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###

There are two ways to compile, manual compilations is described in case there are bugs in the process or the user is unclear on the automated method:
Automated Method:
_TO WORK ON THIS_
1. A Rhino Installer Package (.rhi) file is a package containing a Rhino Plugin .rhp file and a Rhino User Interface .rui file.
.rhp files are compiled using the RhinoScriptCompiler located in buildhelpers.
Use buildhelpers/build_shl_toolbar_installer.py to
Compilation
_TO WORK ON THIS_

_TODO: graphic and explanation of compilation process_

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Explain what these tests test and why

```
Give an example
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Releasing

The goal of releasing is a directory SHL_TOOLBAR containing everything the enduser needs:
- ```SHL_Toolbar_Installer_Part_1.rhi```: Installs the commands and toolbar
- ```SHL_Toolbar_Installer_Part_2.ps1```: Moves the required modules to the user's scripts directory ###NOTE LOCATION OF THIS###
- ```_INSTALLATION_.txt```: Installation instructions
- ```SHL_Toolbox_Guide.pdf```: Full documentation

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc
