"""
SHL Architects 16-10-2018
v1.2 Sean Lamb (Developer)
sel@shl.dk
-better handling of different brep types
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc
import System

import shl_toolbox_lib_dev.layers as wla
reload(wla)
import shl_toolbox_lib_dev.util as wut
reload(wut)
import shl_toolbox_lib_dev.rhino_util as wru
reload(wru)
import shl_toolbox_lib_dev.geo as wge
reload(wge)
import shl_toolbox_lib_dev.fab as wfa
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
	global LCUT_INDICES
	
	LCUT_INDICES = wla.get_lcut_layers()
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
	num_sections = int(height/thickness)
	remainder = height%thickness
	relative_heights = wut.frange(0,height,thickness)
	return [num_sections,remainder,relative_heights]


def get_array_translation(xdim,gap):
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
	Rhino.Geometry.Brep.MergeCoplanarFaces(brep,D_TOL)
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


def brep_or_crv(guids):
	#probably want to add extrusions, type 1073741824, as if they are breps
	c = [x for x in guids if rs.ObjectType(x) == 4]
	b = [x for x in guids if rs.ObjectType(x) == 16]
	return c,b


#process an individual floor
def process_floor(in_objects,floor_outline):
	"""function used to process an individual floor.
	input:
		in_objects: the internal curves and breps selected for this floor
		floor_outline: the outline curve for this floor.
	output: (crv,[crv])
		crv: the offset boundary curve for the floor
		[crv]: the internal curves for the floor
		pt: lower-left reference point
		bdims = bounding dims of this floor
	"""
	#classify the inputs
	in_crvs, in_breps = brep_or_crv(in_objects)
	
	#get list of crvs to project
	brep_sections = []
	for b in in_breps:
		cut_height = wge.get_brep_height(b)
		pcurves = wge.get_brep_plan_cut(rs.coercebrep(b),cut_height/2,D_TOL)
		brep_sections.extend(pcurves)
	
	k = wru.add_curves_to_layer(brep_sections,LCUT_INDICES[0])
	in_crvs.extend(k)
	
	#get the outline brep curve
	cut_height = wge.get_brep_height(floor_outline)
	floor_outline_crvs = wge.get_brep_plan_cut(floor_outline,cut_height/2,D_TOL)
	floor_outline_crvs = wru.add_curves_to_layer(floor_outline_crvs,LCUT_INDICES[1])
	
	#get bounding info for the floor outline
	bb = rs.BoundingBox(floor_outline)
	corner = bb[0]
	bdims = wge.get_bounding_dims(floor_outline)
	proj_srf = rs.AddSrfPt([bb[0],bb[1],bb[2],bb[3]])
	
	internal_crvs = rs.ProjectCurveToSurface(in_crvs,proj_srf,[0,0,-1]) if in_crvs else []
	offset_floor_crv = rs.ProjectCurveToSurface(floor_outline_crvs,proj_srf,[0,0,-1])
	
	rs.DeleteObjects(in_crvs)
	rs.DeleteObjects(floor_outline_crvs)
	rs.DeleteObject(proj_srf)
	
	out_floor_crvs = rs.coercecurve(offset_floor_crv)
	out_internal_crvs = [rs.coercecurve(x) for x in internal_crvs]
	rs.DeleteObject(offset_floor_crv)
	rs.DeleteObjects(internal_crvs)
	#TODO: make sure objects are being deleted
	return out_floor_crvs,out_internal_crvs,corner,bdims


def rc_get_inputs():
	
	#1. Get plan surface
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	opt_thickness = Rhino.Input.Custom.OptionDouble(5.5,0.2,1000)
	opt_sections = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_inplace = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_heights = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	
	go.SetCommandPrompt("Select floorplate outline surface to extract plan cuts")
	go.AddOptionDouble("FacadeThickness", opt_thickness)
	
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
		res = go.Get()
		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
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
	
	#set globals
	global THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	
	#Get brep representations of objects
	if go.ObjectCount != 1:
		return
	boundary_brep = go.Object(0).Object()
	boundary_brep = boundary_brep.Geometry
	if boundary_brep.GetType() != Rhino.Geometry.Brep: boundary_brep = wru.extrusion_to_brep(boundary_brep)
	
	envelope_guid = go.Object(0).Object().Id
	rs.LockObject(envelope_guid)
	#2. Get projection curves
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep | Rhino.DocObjects.ObjectType.Curve
	
	floor_guids = []
	floor_num = 1
	objects_selected = True
	
	go.SetCommandPrompt("Floor %d: Select breps and curves to project. Breps are assumed to be vertical extrusion-type" % floor_num)
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
	
	#Get geometry
	obj_guids = []
	obj_geos = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		obj_geos.append(b_obj.Geometry)
		obj_guids.append(b_obj.Id)
	rs.UnselectObjects(obj_guids)
	floor_guids.append(obj_guids)
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep | Rhino.DocObjects.ObjectType.Curve
	floor_num = 2
	go.SetCommandPrompt("Floor %d: Select breps and curves to project. Breps are assumed to be vertical extrusion-type" % floor_num)
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
	
	#Get geometry
	obj_guids = []
	obj_geos = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		obj_geos.append(b_obj.Geometry)
		obj_guids.append(b_obj.Id)
	rs.UnselectObjects(obj_guids)
	floor_guids.append(obj_guids)
	
	rs.UnlockObject(envelope_guid)
	return boundary_brep,floor_guids


def rc_cut_plan(boundary_brep, floor_guids, use_epsilon):
	
	outline_crv, internals, refpt, bdims = process_floor(floor_guids,boundary_brep)
	
	#...brep conversion may be necessary
	
	#set base for output.
	xbase = 0
	ybase = 0
	#set the amount to move up from the bottom of the brep for cutting the lower outline.
	#this should be replaced by a projection of the bottom face of the brep.
	epsilon = D_TOL*2
	
	select_items = []
	
	crv_list = [ [[outline_crv],internals] ]
	layer_list = [[LCUT_INDICES[1],LCUT_INDICES[2]]] #TODO: this needs to be the correct layer indices!!!!
	refpt_list = [refpt]
	bdims_list = [bdims]
	
	increment = max(d.X for d in bdims_list) + GAP_SIZE*1
	dplane_list = get_drawing_planes(bdims_list,rs.WorldXYPlane(),GAP_SIZE)
	refplane_list = [rs.MovePlane(rs.WorldXYPlane(),pt) for pt in refpt_list]
	
	for i,floor in enumerate(crv_list):
		t = Rhino.Geometry.Transform.ChangeBasis(dplane_list[i],refplane_list[i])
		
		for j,layer_crvs in enumerate(floor):
			for c in layer_crvs:
				c.Transform(t)
			wru.add_curves_to_layer(layer_crvs,layer_list[i][j])
		
		labelpt = (bdims_list[i].X/2 + dplane_list[i].Origin.X, bdims_list[i].Y/2 + dplane_list[i].OriginY, 0)
		td = rs.AddTextDot(str(i),labelpt)
		rs.ObjectLayer(td,"XXX_LCUT_00-GUIDES")
	
	rs.UnselectAllObjects()
	rs.SelectObjects(select_items)
	rs.Redraw()
	rs.EnableRedraw(True)

def rc_cut_plan2(boundary_brep, floor_guids, use_epsilon):
	
	crv_list,layer_list,refpt_list,bdims_list = [[],[],[],[]]
	for guids in floor_guids:
		outline_crv, internals, refpt, bdims = process_floor(guids,boundary_brep)
		crv_list.append( [[outline_crv],internals])
		layer_list.append([LCUT_INDICES[1],LCUT_INDICES[2]]) #TODO: this needs to be the correct layer indices!!!!
		refpt_list.append(refpt)
		bdims_list.append(bdims)
	#...brep conversion may be necessary
	
	#set base for output.
	xbase = 0
	ybase = 0
	#set the amount to move up from the bottom of the brep for cutting the lower outline.
	#this should be replaced by a projection of the bottom face of the brep.
	epsilon = D_TOL*2
	
	select_items = []
	
#	crv_list = [ [[outline_crv],internals] ]
#	layer_list = [[LCUT_INDICES[1],LCUT_INDICES[2]]] #TODO: this needs to be the correct layer indices!!!!
#	refpt_list = [refpt]
#	bdims_list = [bdims]
	
	increment = max(d.X for d in bdims_list) + GAP_SIZE*1
	dplane_list = get_drawing_planes(bdims_list,rs.WorldXYPlane(),GAP_SIZE)
	refplane_list = [rs.MovePlane(rs.WorldXYPlane(),pt) for pt in refpt_list]
	
	for i,floor in enumerate(crv_list):
		t = Rhino.Geometry.Transform.ChangeBasis(dplane_list[i],refplane_list[i])
		
		for j,layer_crvs in enumerate(floor):
			for c in layer_crvs:
				c.Transform(t)
			wru.add_curves_to_layer(layer_crvs,layer_list[i][j])
		
		labelpt = (bdims_list[i].X/2 + dplane_list[i].Origin.X, bdims_list[i].Y/2 + dplane_list[i].OriginY, 0)
		td = rs.AddTextDot(str(i+1),labelpt)
		rs.ObjectLayer(td,"XXX_LCUT_00-GUIDES")
	
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


# RunCommand is the called when the user enters the command name in Rhino.
# The command name is defined by the filname minus "_cmd.py"
def RunCommand( is_interactive ):
	setGlobals()
	
	boundary_brep, obj_guids = rc_get_inputs()
	
#	rc_cut_plan(boundary_brep,obj_guids,True)
	rc_cut_plan2(boundary_brep,obj_guids,True)
	return 0

RunCommand(False)
