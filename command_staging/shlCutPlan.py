"""
SHL Architects 16-10-2018
Sean Lamb (Developer)
sel@shl.dk
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc
from scriptcontext import sticky
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


def setGlobals():
	#mm
	global D_TOL, A_TOL
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees

	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()
	
	global GAP_SIZE
	GAP_SIZE = 5


def setup_GetObject(g):
	g.AcceptNothing(True)
	g.EnableClearObjectsOnEntry(False)
	return


def brep_or_crv(guids):
	#probably want to add extrusions, type 1073741824, as if they are breps
	c = [x for x in guids if rs.ObjectType(x) == 4 ]
	b = [x for x in guids if (rs.ObjectType(x) == 16 or rs.ObjectType(x) == 1073741824)]
	return c,b


def get_drawing_planes(section_dims, baseplane, increment):
	"""generate planes for placing the bottom-left corner of output curves."""
	drawing_planes = [baseplane]
	p = baseplane #temp plane
	for dim in section_dims[:-1]:
		o = [p.OriginX + dim.X + increment, p.OriginY, p.OriginZ]
		p = rs.MovePlane(p,o)
		drawing_planes.append(p)
	return drawing_planes


def process_floor(in_objects,floor_outline,outline_cut_height=None):
	"""function used to process an individual floor.
	input:
		in_objects: the internal curves and breps selected for this floor
		floor_outline: the outline brep for the envelope
		outline_cut_height: height to cut at.
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
		cut_height = wge.get_brep_height(b)/2
		pcurves = wge.get_brep_plan_cut(rs.coercebrep(b),cut_height,D_TOL)
		brep_sections.extend(pcurves)

	b_section_guids = wru.add_curves_to_layer(brep_sections,LCUT_INDICES[0])
	in_crvs.extend(b_section_guids)


	#get the outline brep curve
	if not outline_cut_height: outline_cut_height = wge.get_brep_height(floor_outline)
	floor_outline_crvs = wge.get_brep_plan_cut(rs.coercebrep(floor_outline),outline_cut_height,D_TOL)
	floor_outline_crvs = wru.add_curves_to_layer(floor_outline_crvs,LCUT_INDICES[1])

	#get bounding info for the floor outline
	bb = rs.BoundingBox(floor_outline)
	corner = bb[0]
	bdims = wge.get_bounding_dims(floor_outline)
	proj_srf = rs.AddSrfPt([bb[0],bb[1],bb[2],bb[3]])

	internal_crvs = rs.ProjectCurveToSurface(in_crvs,proj_srf,[0,0,-1]) if in_crvs else []
	offset_floor_crv = rs.ProjectCurveToSurface(floor_outline_crvs,proj_srf,[0,0,-1])

	#rs.DeleteObjects(in_crvs)
	rs.DeleteObjects(floor_outline_crvs)
	rs.DeleteObject(proj_srf)

	out_floor_crvs = rs.coercecurve(offset_floor_crv)
	out_internal_crvs = [rs.coercecurve(x) for x in internal_crvs]
	rs.DeleteObject(offset_floor_crv)
	rs.DeleteObjects(internal_crvs)
	rs.DeleteObjects(b_section_guids)
	#TODO: make sure objects are being deleted
	return out_floor_crvs,out_internal_crvs,corner,bdims


def get_plan_brep():
	#1. Get plan surface
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	default_thickness = sticky["defaultThickness"] if sticky.has_key("defaultThickness") else 5.5
	opt_thickness = Rhino.Input.Custom.OptionDouble(default_thickness,0.2,1000)
	
	go.SetCommandPrompt("Select floorplate outline surface to extract plan cuts")
	go.AddOptionDouble("FacadeThickness", opt_thickness)

	setup_GetObject(go)

	bHavePreselectedObjects = False

	while True:
		res = go.Get()
		if res == Rhino.Input.GetResult.Option:
			go.EnablePreSelect(False, True)
			continue
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
	sticky["defaultThickness"] = THICKNESS
	
	#Get brep representations of objects
	if go.ObjectCount != 1:
		return
	envelope_guid = go.Object(0).Object().Id
	
	return envelope_guid


def get_plane_and_projection_crvs(plane_num):

	plan_cut_heights = []
	rs.UnselectAllObjects()
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep

	go.SetCommandPrompt("Floor %d: Select plane for floorplate cut. Command will use top surface. Press Enter if done" % plane_num)
	setup_GetObject(go)

	res = go.Get()
	if res != Rhino.Input.GetResult.Object:
		return None
	else:
		pass

	#Get brep representations of objects
	if go.ObjectCount != 1: return None
	floorplate_brep_obj = go.Object(0).Object()
	floorplate_brep = floorplate_brep_obj.Geometry

	bb = rs.BoundingBox(floorplate_brep)
	plan_cut_height = bb[4].Z

	#C. get breps and curves to project
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep | Rhino.DocObjects.ObjectType.Curve
	go.SetCommandPrompt("Floor %d: Select breps and curves to project. Breps are assumed to be vertical extrusion-type" % plane_num)
	rs.UnselectObject(floorplate_brep_obj.Id)
	
	projection_guids = []
	objects_selected = True
	
	res = go.GetMultiple(1,0)
	if res != Rhino.Input.GetResult.Object:
		print "nothing"
		return plan_cut_height, []
	
	#Get geometry
	for i in xrange(go.ObjectCount):
		projection_guids.append(go.Object(i).Object().Id)
	
	return plan_cut_height, projection_guids


def rc_get_inputs():
	envelope_brep_guid = get_plan_brep()
	rs.LockObject(envelope_brep_guid)
	
	more_floors = True
	count = 0
	plan_heights = []
	projection_guids = []
	
	while more_floors and count < 100:
		try:
			h, p = get_plane_and_projection_crvs(count+1)
			plan_heights.append(h)
			projection_guids.append(p)
		except:
			break
		count += 1
	
	if plan_heights:
		return envelope_brep_guid, plan_heights, projection_guids, envelope_brep_guid
	else:
		return None


def rc_cut_plan(boundary_brep, cut_heights, floor_guids, use_epsilon):

	bb = rs.BoundingBox(boundary_brep)
	max_z = bb[4].Z
	min_z = bb[0].Z
	crv_list,layer_list,refpt_list,bdims_list = [[],[],[],[]]

	for i,guids in enumerate(floor_guids):
		if not (min_z < cut_heights[i] < max_z): continue
		outline_crv, internals, refpt, bdims = process_floor(guids,boundary_brep,cut_heights[i])
		
		mp = Rhino.Geometry.AreaMassProperties.Compute(outline_crv)
		outline_crv_centroid = mp.Centroid
		corner_style = Rhino.Geometry.CurveOffsetCornerStyle.Sharp
		offset_crv = outline_crv.Offset(outline_crv_centroid,rs.coerce3dvector([0,0,1]),THICKNESS,D_TOL,corner_style)
		offset_crv_geometry = offset_crv[0]
		
		crv_list.append([[offset_crv_geometry],internals])
		layer_list.append([LCUT_INDICES[1],LCUT_INDICES[2]])
		refpt_list.append(refpt)
		bdims_list.append(bdims)
	#...brep conversion may be necessary

	if len(crv_list) == 0:
		print "Error: Cut planes do not intersect the envelope brep"
		return None
	
	#set base for output.
	xbase = 0
	ybase = 0
	#set the amount to move up from the bottom of the brep for cutting the lower outline.
	#this should be replaced by a projection of the bottom face of the brep.
	epsilon = D_TOL*2
	
	select_items = []
	
	increment = max(d.X for d in bdims_list) + GAP_SIZE*1
	dplane_list = get_drawing_planes(bdims_list,rs.WorldXYPlane(),GAP_SIZE)
	refplane_list = [rs.MovePlane(rs.WorldXYPlane(),pt) for pt in refpt_list]

	for i,floor in enumerate(crv_list):
		t = Rhino.Geometry.Transform.ChangeBasis(dplane_list[i],refplane_list[i])

		for j,layer_crvs in enumerate(floor):
			for c in layer_crvs:
				c.Transform(t)
			select_items.extend(wru.add_curves_to_layer(layer_crvs,layer_list[i][j]))
 		
		labelpt = (bdims_list[i].X/2 + dplane_list[i].Origin.X, bdims_list[i].Y/2 + dplane_list[i].OriginY, 0)
		td = rs.AddTextDot(str(i+1),labelpt)
		rs.ObjectLayer(td,"XXX_LCUT_00-GUIDES")
		select_items.append(td)

	rs.UnselectAllObjects()
	rs.SelectObjects(select_items)
	rs.Redraw()
	rs.EnableRedraw(True)


# RunCommand is the called when the user enters the command name in Rhino.
def RunCommand( is_interactive ):
	setGlobals()
	
	try:
		brep, plan_heights, projection_guids, envelope_brep = rc_get_inputs()
	except:
		print "Error in input!"
	
	try:
		rc_cut_plan(brep,plan_heights,projection_guids,True)
	except:
		print "Error cutting plans!"
	
	if envelope_brep: rs.UnlockObject(envelope_brep)
	return None


RunCommand(False)
