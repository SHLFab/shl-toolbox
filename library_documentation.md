# SHL Toolbox Library

Short description of library here.

## lib.fab
Functions for fabrication output

### add_fab_tags
```
add_fab_tags(tag_points, tag_text, tag_size, text_justification=Rhino.Geometry.TextJustification.Center)
```
Adds fabrication labels as curves to a list of points.

**Parameters:**
```
tag_points ([point, ...]): list of point3ds
tag_text (str): list of tag text
tag_size (int): size of text
text_justification (Rhino.Geometry.TextJustification): text justification
```

**Returns:**
```
[guids]: list of guids of the exploded curves making up the labels.
```

**Example:**
```python
add_fab_tags([point1,point2, point3], ['wall_1','wall_2','ceiling_1'], 5)
```

-------------------------------------


## lib.geo
Functions dealing with modifying or extracting geometry information

### get_bounding_dims
```
get_bounding_dims(brep)
```
Returns bounding box x,y,z dims for a brep or many breps

**Parameters:**
```
brep: a brep (is it guid or not?)
```

**Returns:**
```
dims (X,Y,Z): namedtuple with values X, Y, Z.
```

---
#### get_brep_base_plane
```
get_brep_base_plane(brep)
```
Returns the xy plane at the brep BoundingBox's lower left corner

---
### get_brep_height
```
get_brep_height(brep)
```
Returns the height of a brep's bounding box

---
### get_brep_plan_cut
```
get_brep_plan_cut(brep,cut_height,tolerance)
```
Cut a brep through the XY plane at a certain height and return the section curves.
Note that this function will try to join the resulting section curves.

**Parameters:**
```
brep (brep): RhinoCommon brep object
cut_height (float): height relative to base of BoundingBox to section the brep
tolerance (float): tolerance for joining the resulting curves. Suggested: use document tolerance.
```

**Returns:**
```
[polycurve, ...]: list of RhinoCommon polycurve objects
```

**Example:**
```python
h = get_brep_height(b)
section_crvs = get_brep_plan_cut(b,h/2,0.01)
```
---
### get_brep_plan_cut_use_plane
```
get_brep_plan_cut_use_plane(brep,plane,tolerance)
```
Cut a brep through a given plane and return the section curves.
Note that this function will try to join the resulting section curves

Usage similar to get_plan_cut

---
### get_internal_angles
```
get_internal_angles(pts)
```
Get the internal angles of a set of pts representing a counter-clockwise polyline.

**Parameters:**
```
pts ([point, ...]: list of Point3ds in counter-clockwise order.
```

**Returns:**
```
angles ([float, ...]): list of internal angles
```

---
### make_pcurve_ccw
```
make_pcurve_ccw(geo_polycurve):
```
Accepts a rhino geometry.polycurve object and makes it counter-clockwise. Returns None.

---
### get_interior_pt
```
get_interior_pt(g_curve,sample_distance,quality=10)
```
get an interior point in the brep by brute-force. jitters interior point by distance.

**Parameters:**
```
g_curve: curve geometry
sample_distance: amount to jitter randomly placed point by
quality=10: number of spots to try.
```

**Returns:**
```
point: point3d
```

---
### get_polycurve_segment_points
```
get_polycurve_segment_points(g_polycurve)
```
gets a list of startpts,endpts,midpts for each segment in RhinoCommon curve geometry

**Parameters:**
```
g_polycurve (Rhino.Geometry.Polycurve): polycurve geometry
```

**Returns:**
```
[startpts,endpts,midpts] ([ [Point3d, ... ], [Point3d, ... ], [Point3d, ... ] ]: lists of start, end, and midpoints of each segment.
```

---
### get_extreme_srf
```
get_extreme_srf(brep,h_tol,top=True)
```
get the surface at the top or bottom of the brep.
Algorithm:
1. pick n random pts on each surface, P
2. get the 3 lowest points in P (disabled for now; just does straight averaging)
3. determine their dot product with the unit z and their avg height
4. throw out all surfaces that aren't within the dot product threshold.
5. of the remaining surfaces, sort to get the lowest one. if any of them have a height within the
height tolerance, select them as well.
6. return these lowest srfs.

**Parameters:**
```
brep: RhinoCommon brep Geometry
h_tol: height tolerance (???)
top=True: True for top, False for bottom surface
```

**Returns:**
```
extreme_surfaces: ???
```

---
### brepClosestPoint
```
brepClosestPoint(b1,b2,precision)
```
Obtain the closest points on two breps
Algorithm:
1. Pick a random point p1_0 on b1, and get the point p2_0 closest to it on b2.
2. Pick the point p1_1 on b1 closest to p2_0 ... repeat iteratively.

**Parameters:**
```
b1, b2: breps to search for closest points on
precision: number of iterations for search Algorithm
```

**Returns:**
```
[pt1,pt2]: list of Point3ds closest to one-another on b1 and b2, respectively
```
---
### multi_test_in_or_out
### MUST REVIEW
```
multi_test_in_or_out(test_crv, vols):
```
Tests midpoint of curve for containment inside one of several volumes.

**Parameters:**
```
test_crv (?): 
vols (?): 
```

**Returns:**
```
inside (bool): True if point is inside at least one of the volumes, otherwise False
```

---
### check_planar_curves_collision
### MUST REVIEW
```
check_planar_curves_collision(crvs)
```
Returns True if any two curves overlap, curves must be planar


---
### trim_boundary
### MUST REVIEW
```
trim_boundary(e_crvs,cb_crvs,tol,inside=True)
```
Trim curves by closed boundary curves.
NOTE: assumes redraw is turned off. assumes curves are planar.
future versions to use projection method to avoid these assumptions.

**Parameters:**
```
e_crvs (?): etch curves to be trimmed
cb_crvs (?): closed boundary curves
tol (?): tolerance. document tolerance recommended
inside=True (?): trim the inside if true, trim outside if false
```

**Returns:**
```
? (?): the list of curves kept.
```



## lib.layers
Functions for layer modification and assignment

### add_layer
```
add_layer(name,color)
```
add a colored layer by name

**Parameters:**
```
name (str): layer name
color (System.Drawing.Color): color for layer
```

**Returns:**
```
layerInd (int): layer index
```

---

### set_layer_color
```
set_layer_color(layerInd,color)
```
set the layer color

**Parameters:**
```
layerInd (int): layer index
color (System.Drawing.Color): color for layer
```

**Returns:**
```
None
```

---

### set_layer_plot_weight
```
set_layer_plot_weight(layerInd,weight)
```
set the layer's plotweight

**Parameters:**
```
layerInd (int): layer index
weight (float): plotweight. -1 for NoPrint.
```

**Returns:**
```
None
```

---

### change_object_layers
```
change_object_layers(guids,layName,copy=False)
```
change layer of objects

**Parameters:**
```
guids ([guid, ...]): object GUIDs
layName (str): layer name
copy=False (bool): new objects on layer (or original objects with reassigned layer if copy==False)
```

**Returns:**
```
guids ([guid, ...]): the guids of the objects on the new layer (original objects if copy=False, new objects if copy=True)
```

---

### get_layer_objects
```
get_layer_objects(*layers)
```
Get all of the objects on the layer. If layer does not exist, will get an empty list back

**Parameters:**
```
*layers (str): layer name
```

**Returns:**
```
rhobjs ([rhobj, ...]): rhinocommon geometry objects
```

---

### ind_to_name
```
ind_to_name(layer_indices)
```
convert a list of layer indices to layer names for use in rhinoscriptsyntax

**Parameters:**
```
layer_indices ([int, ... ]): layer indices
```

**Returns:**
```
layer_names ([str, ... ]): layer names
```

-------------------------------------

## lib.rhino_util
Rhino object utility functions (e.g. converting between RhinoCommon types)


### extrusion_to_brep
```
extrusion_to_brep(extrusion)
```
convert a single extrusion geometry to a brep geometry if it has a brep form

---

### docobj_to_guid
```
docobj_to_guid(doc_input)
```
convert list of doc objects to list of guids. handles single objects as well and converts them to a single guid.

---

### add_curve_to_layer
```
add_curve_to_layer(curve,layer_index)
```
add a RhinoCommon curve object to a layer by layer index.

---

### add_brep_to_layer
```
add_brep_to_layer(brep,layer_index)
```
add a RhinoCommon brep object to a layer by layer index.

---

### add_curves_to_layer
```
add_curves_to_layer(curves_list,layer_index)
```
add a list of RhinoCommon curves to layer by layer index.

---

### polycurve_to_polyline
```
polycurve_to_polyline(g_polycurve,absolute_tolerance,angle_tolerance):
```
convert a polycurve to a polyline

**Parameters:**
```
g_polycurve (RhinoCommon polycurve): curve in
absolute_tolerance (float): maximum deviation from line midpoints to the curve. When in doubt use the document's model space absolute tolerance.
absolute_tolerance (float): maximum deviation of the line directions. When in doubt use document's model space angle tolerance.
```

**Returns:**
```
g_polyline (RhinoCommon polyline): polyline object
```

### polylinecurve_to_polycurve
```
polycurve_to_polyline(g_polylinecurve):
```
convert a polylinecurve to a polycurve

**Parameters:**
```
g_polycurve (RhinoCommon polylinecurve): polylinecurve geometry
```

**Returns:**
```
g_polyline (RhinoCommon polycurve): polycurve object

-------------------------------------


## lib.util
General non-geometric utilities

### equidistant_hsv_color
```
equidistant_hsv_color(num,saturation)
```

**Parameters:**
```
num (int): number of colours
saturation (float): saturation value (0.0 - 1.0)
```

**Returns:**
```
[(r,g,b), ...]: list of rgb colours as tuples.
```

---
### frange
### NEEDS EXAMPLE
```
frange(start,stop,step)
```
Floating point range. Final number in range will not exceed the stop value.

**Parameters:**
```
start (float): start of range
stop (float): end of range
step (float): increment
```

**Returns:**
```
[float, ... ]: list of numbers
```

---
### num_div
```
num_div(num,divisor):
```
_TODO: REMOVE_
	returns number of divisors. posibly not necessary w/ divmod"""

---
### number_to_letter
```
number_to_letter(num,start=0,upper=True,append=True)
```
convert int to uppercase letter. *will wrap if out of alphabet bounds*
DEV NOTES: still possibly a bug in here for ~26

**Parameters:**
```
num (int): number to convert to letter
start=0 (int): base number corresponding to 'a'
upper=True: use uppercase letters
append=True: append when wrapping.
```

**Returns:**
```
letter (char?): character corresponding to number
```

**Example:**
```python
number_to_letter(30)
>> AE
number_to_letter(3,1)
>> C
```

---
### dotprod
```
dotprod(a,b)
```
dot product for vectors represented as lists

---
### xprod
```
xprod(a,b)
```
cross product for vectors represented as lists

---
### innerangle
```
innerangle(a,b,radians=False)
```
inner angle of two vector3ds. Radians or degrees.

---
### partition_objects_by_attr
```
partition_objects_by_attr(objects,attribute,reverse_bool=False)
```
Split up a list of objects by the values of a certain attribute.

**Parameters:**
```
objects: list of objects
attribute: str of attribute to partition by.
reverse: reverse the sorting order for the partition
```

**Returns:**
```
object[][]: list of lists of objects partitioned by the attribute.
```

**Example:**
```python
objects = [Object1(blue), Object2(red), Object3(blue), Object4(blue), Object5(green)]
partitioned = partition_objects_by_attr(objects)
>> [ [Object1,Object3,Object4], [Object5], [Object2] ]
```
