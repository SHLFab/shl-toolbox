"""
SHL Architects 16-10-2018
v1.2 Sean Lamb (Developer)
sel@shl.dk
-better handling of different brep types
-only plots volumes now
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc
import System

import shl_toolbox_lib.layers as wla
reload(wla)
import shl_toolbox_lib.util as wut
reload(wut)
import shl_toolbox_lib.rhino_util as wru
reload(wru)
import shl_toolbox_lib.geo as wge
reload(wge)
import shl_toolbox_lib.fab as wfa
reload(wfa)

import itertools
import random as rand

# __commandname__ = "shlPlotVolumes"

#necessary?
def setGlobals():
	#mm
	global D_TOL, A_TOL
	global LCUT_INDICES
	global THICKNESS
	global GAP_SIZE
	global TEXTSIZE
	global SORTDIR

	LCUT_INDICES = []
	THICKNESS = 5.5
	GAP_SIZE = 5

	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees

	TEXTSIZE = 3
	SORTDIR = rs.VectorCreate([0,0,0],[1,0.1,0])


def get_brep_label_pt(brep,percent_height_distance=0.15):
	#get bounding box
	bb = rs.BoundingBox(brep)
	top_crv = rs.AddPolyline([bb[4], bb[5], bb[6], bb[7], bb[4]])
	top_label_pt, _ = rs.CurveAreaCentroid(top_crv)
	top_label_pt = rs.VectorAdd(top_label_pt, [0,0,rs.Distance(bb[0],bb[1]) * percent_height_distance])
	rs.DeleteObject(top_crv)

	return top_label_pt


def get_section_curve_info(brep,plane):
	"""returns the curve outline, the bounding dims, and the plane where the curve was cut"""
	#set height
	bdims = wge.get_bounding_dims(brep)
	g_polycurves = wge.get_brep_plan_cut_use_plane(brep, plane, D_TOL)
	g_polycurve = g_polycurves[0]

	if g_polycurve.GetType() != Rhino.Geometry.PolyCurve:
		g_polycurve = wru.polylinecurve_to_polycurve(g_polycurve)

	wru.make_pcurve_ccw(g_polycurve)

	if g_polycurve.GetType() == Rhino.Geometry.PolylineCurve:
		g_polyline = wru.polycurve_to_polyline(g_polycurve, doc.ModelAbsoluteTolerance, doc.ModelAngleToleranceDegrees)
	else:
		g_polyline = g_polycurve

	#plane1 is where the section curve gets built. will be at the midheight.
	return [g_polyline,bdims]


def get_section_curve_info_multi_no_ortho(brep,plane):
	"""returns the curve outline, the bounding dims, and the plane where the curve was cut"""
	#set height
	bdims = wge.get_bounding_dims(brep)
	g_polycurves = wge.get_brep_plan_cut_use_plane(brep, plane, D_TOL)
	#g_polycurve = g_polycurves[0]

	list_curves = []
	for pc in g_polycurves:
		if pc.GetType() != Rhino.Geometry.PolyCurve:
			pc = wru.polylinecurve_to_polycurve(pc)

		wge.make_pcurve_ccw(pc)
		list_curves.append(pc)

	#plane1 is where the section curve gets built. will be at the midheight.
	return [list_curves,bdims]


def get_section_division(height,thickness):
	"""get section information given a thickness
	params:
	height (float): the height of the object
	thickness (float): the material thickness
	returns: [num_sections, remainder, relativeheights]
	where	num_sections = number of sections
			remainder = leftover height
			relative_heights[float]: the heights for the cuts"""
	num_sections = int(height/thickness)
	remainder = height%thickness
	relative_heights = wut.frange(0,height,thickness)
	return [num_sections,remainder,relative_heights]


def get_array_translation(xdim,gap):
	"""get the Rhino.Geometry.Transform object for translating an output along a vector.
	params:
		 xdim (float): the minimum x-dim for the given object
		 gap (float): gap to put between objects"""
	vect = Rhino.Geometry.Vector3d(xdim+gap,0,0)
	translation = Rhino.Geometry.Transform.Translation(vect)
	return translation


def get_brep_section_planes(brep,section_heights):
	base_plane = wge.get_brep_base_plane(brep)
	section_planes = []
	for height in section_heights:
		new_plane = rs.MovePlane(base_plane, [base_plane.OriginX, base_plane.OriginY, base_plane.OriginZ + height])
		section_planes.append(new_plane)
	return section_planes


def get_drawing_planes(section_dims, baseplane, increment):
	"""generate planes for placing the bottom-left corner of output curves."""
	drawing_planes = [baseplane]
	p = baseplane #temp plane
	for dim in section_dims[:-1]:
		o = [p.OriginX + dim.X + increment, p.OriginY, p.OriginZ]
		p = rs.MovePlane(p,o)
		drawing_planes.append(p)
	return drawing_planes


def get_lowest_curve_info(brep, h_tol):
	#right now hardcoded to not deal with multiple breps at the final step. to revise if needed.
	bdims = wge.get_bounding_dims(brep)
	brep_faces = wge.get_extreme_srf(brep, h_tol,False)

	crvs_by_brep = []

	for f in brep_faces:
		crvs = []
		inds = f.AdjacentEdges()
		for i in inds:
			k = brep.Edges
			crvs.append(brep.Edges[i])
		crvs = Rhino.Geometry.Curve.JoinCurves(crvs,D_TOL)
	crvs_by_brep.append(crvs)

	crvs_by_brep = crvs_by_brep[0] #to fix this later. only deals w one brep for now
	list_curves = []
	for pc in crvs_by_brep:
		if pc.GetType() != Rhino.Geometry.PolyCurve:
			pc = wru.polylinecurve_to_polycurve(pc)

		wge.make_pcurve_ccw(pc)
		list_curves.append(pc)

	return [list_curves,bdims]


def rc_plot_volumes(use_epsilon):

	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep

	opt_inplace = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_heights = Rhino.Input.Custom.OptionToggle(False,"No","Yes")

	go.SetCommandPrompt("Select breps to extract plan cuts")
	go.AddOptionToggle("InPlace", opt_inplace)
	go.AddOptionToggle("PrintPieceHeights", opt_heights)

	go.GroupSelect = True
	go.SubObjectSelect = False
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)
	go.EnableClearObjectsOnEntry(False)
	go.EnableUnselectObjectsOnExit(False)
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.DeselectAllBeforePostSelect = False

	res = None
	bHavePreselectedObjects = False

	while True:
		res = go.GetMultiple(1,0)
		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			# print res
			go.EnablePreSelect(False, True)
			continue
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break

	rs.EnableRedraw(False)

	DIRPT1 = rs.coerce3dpoint([0,0,0])
	DIRPT2 = rs.coerce3dpoint([1,0.001,0])
	global BOOL_HEIGHTS
	global LCUT_INDICES
	global SORTDIR
	BOOL_HEIGHTS = opt_heights.CurrentValue
	LCUT_INDICES = wla.get_lcut_layers()
	SORTDIR = DIRPT2 - DIRPT1

	#Get boolean for "inplace"
	INPLACE = opt_inplace.CurrentValue

	#Get brep representations of objects
	brep_geo_list = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		brep_geo_list.append(b_obj.Geometry)

	#...brep conversion may be necessary
	new_brep_list = []
	for i, geo in enumerate(brep_geo_list):
		if geo.GetType() != Rhino.Geometry.Brep:
			new_brep_list.append(wru.extrusion_to_brep(geo))
		else:
			new_brep_list.append(geo)

	#set base for output.
	xbase = 0
	ybase = 0
	#set the amount to move up from the bottom of the brep for cutting the lower outline.
	#this should be replaced by a projection of the bottom face of the brep.
	epsilon = D_TOL*2

	select_items = []

	centroids = [c.GetBoundingBox(rs.WorldXYPlane()).Center for c in new_brep_list]
	brep_collection = zip(centroids,new_brep_list)
	brep_collection = sorted(brep_collection, sortcompare)
	_, new_brep_list = zip(*brep_collection)

	for i,brep in enumerate(new_brep_list):
		#get lowest curve info

		#get label prefix and bounding dims for this brep
		bdims = wge.get_bounding_dims(brep)
		baseplane = rs.MovePlane(rs.WorldXYPlane(),[xbase,ybase,0])
		label_letter = wut.number_to_letter(i)

		#prepare heights and labels for each section cut
		num_sections = 1
		remaining_thickness = 0
		cuts_at = [epsilon] if use_epsilon else [0]
		brep_label = label_letter
		section_labels = [label_letter]

		if BOOL_HEIGHTS == True:
			section_labels = [label + "\n" + str(round(bdims.Z,1)) for label in section_labels]

		#get section information for each cut
		section_planes = get_brep_section_planes(brep, cuts_at)

		section_curves, section_dims = [[],[]]
		for i,plane in enumerate(section_planes):
			curve,dims = [0,0]
			if (not use_epsilon) and (i == 0):
				curve, dims = get_lowest_curve_info(brep,D_TOL*2)
			else:
				curve, dims = get_section_curve_info_multi_no_ortho(brep,plane)
			section_curves.append(curve)
			section_dims.append(dims)

		##DO WORK HERE##
		drawing_planes = get_drawing_planes(section_dims,baseplane,GAP_SIZE)

		#place curves in drawing location
		for sp, dp, sc in zip(section_planes, drawing_planes, section_curves):
			if INPLACE == True:
				t = Rhino.Geometry.Transform.Translation(0,0,0)
			else:
				t = Rhino.Geometry.Transform.ChangeBasis(dp,sp)
			for c in sc:
				c.Transform(t)

		#THIS IS STILL A MESS: LABEL ADDING
		#draw curves and add text dots
		top_label_pt = get_brep_label_pt(brep)
		brep_textdot = rs.AddTextDot(brep_label,top_label_pt)
		rs.ObjectLayer(brep_textdot,"XXX_LCUT_00-GUIDES")

		label_pts = []
		for sc,label in zip(section_curves,section_labels):
			for i,c in enumerate(sc):
				crv = wru.add_curve_to_layer(c,LCUT_INDICES[1])
				select_items.append(crv)
				if i == 0:
					label_pts.append(rs.CurveAreaCentroid(crv)[0])

		fab_tags = wfa.add_fab_tags(label_pts,section_labels,TEXTSIZE)
		for tag in fab_tags:
			rs.ObjectLayer(tag,"XXX_LCUT_02-SCORE")
			group_name = rs.AddGroup()
			rs.AddObjectsToGroup(tag,group_name)
		ybase += max([s.Y for s in section_dims]) + GAP_SIZE*1

		for tag in fab_tags: select_items.extend(tag)
		#THIS IS STILL A MESS: LABEL ADDING
	rs.UnselectAllObjects()
	rs.SelectObjects(select_items)
	rs.Redraw()
	rs.EnableRedraw(True)


#sort function for comparing collection along a vector.
def sortcompare(a, b):
	pointa, pointb = a[0], b[0]
	rc = cmp(pointa.X, pointb.X)
	if SORTDIR.X<0: rc = -1*rc
	if rc==0:
		rc = cmp(pointa.Y, pointb.Y)
		if SORTDIR.Y<0: rc = -1*rc
	if rc==0:
		rc = cmp(pointa.Z, pointb.Z)
		if SORTDIR.Z<0: rc = -1*rc
	return rc


# RunCommand is called when the user enters the command name in Rhino.
# The command name is defined by the filname minus "_cmd.py"
def RunCommand( is_interactive ):
	setGlobals()
	rc_plot_volumes(False)
	return 0

RunCommand(False)
