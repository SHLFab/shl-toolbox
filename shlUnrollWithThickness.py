"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
-removed interactive
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc
import itertools
from collections import namedtuple

import shl_toolbox_lib.layers as wla
reload(wla)
import shl_toolbox_lib.util as wut
reload(wut)
import shl_toolbox_lib.rhino_util as wru
reload(wru)
import shl_toolbox_lib.geo as wge
reload(wge)

# __commandname__ = "shlUnrollWithThickness"


def setGlobals():
	#mm
	global D_TOL, A_TOL
	global LCUT_INDICES
	global GAP_SIZE

	LCUT_INDICES = []
	GAP_SIZE = 5

	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees


def get_brep_labelpt(brep,multiplier):
	"""get the label point for the top of a brep.
	params
		brep(brep): the brep
		multiplier (float): label will be (multiplier * brep height) above the brep
	returns
		GUID of point for the label."""
	bb = rs.BoundingBox(brep)
	height = rs.Distance(bb[0],bb[4])
	top_crv = rs.AddPolyline(bb[4:8] + [bb[4]])
	top_label_pt, _ = rs.CurveAreaCentroid(top_crv)
	rs.MoveObject(top_label_pt,[0,0,multiplier*height])
	rs.DeleteObject(top_crv)
	return top_label_pt


def offset_pcurve(geo_pcurve,dist):
	"""offset a pcurve on the xy plane. no feedback if it fails."""
	ref_plane = rs.WorldXYPlane()
	offset_curve = geo_pcurve.Offset(ref_plane, -dist, D_TOL, Rhino.Geometry.CurveOffsetCornerStyle.Sharp)
	j = len(offset_curve)
	if len(offset_curve) == 1:
		return offset_curve[0]
	else:
		return Rhino.Commands.Result.Failure


#total mess and needs massive cleanup
def get_brep_sides_info(brep, material_thickness):
	#Dimensions as a namedtuple type.
	Dimensions = namedtuple('Dimensions','x y')

	height = wge.get_brep_height(brep)
	g_polycurves = wge.get_brep_plan_cut(brep,height/2,D_TOL) #get plan cut at mid-height
	g_polycurve = g_polycurves[0] #extract the first curve, we assume there will only be one curve.
	top_label_pt = get_brep_labelpt(brep,0.15)


	if g_polycurve.GetType() == Rhino.Geometry.PolyCurve:
		wge.make_pcurve_ccw(g_polycurve)
	else:
		g_polycurve = wru.polylinecurve_to_polycurve(g_polycurve)
		wge.make_pcurve_ccw(g_polycurve)

	startpts, endpts, divpts = wge.get_polycurve_segment_points(g_polycurve)
	g_polyline = wru.polycurve_to_polyline(g_polycurve, doc.ModelAbsoluteTolerance, doc.ModelAngleToleranceDegrees)
	seg_count = g_polycurve.SegmentCount

	angles = wge.get_internal_angles(startpts)

	for i, point in enumerate(divpts):
		k = rs.AddTextDot( i, point )
		rs.ObjectLayer(k,"XXX_LCUT_00-GUIDES")

	#get output info
	piece_dims = []
	for i in xrange(seg_count):

		corner_angles = ( angles[i],angles[(i+1)%seg_count] )
		#print corner_angles

		seg = g_polycurve.SegmentCurve(i)
		seg_len = seg.GetLength()
		if i%2 == 0:
			#print "dir 1"
			for angle in corner_angles:
				if abs((angle - 90)) < 0.1:
					seg_len -= material_thickness
		if i%2 == 1:
			#print "dir 2"
			#print corner_angles
			for angle in corner_angles:
				if abs((angle - 270)) < 0.1:
					seg_len += material_thickness
		this_piece_dims = Dimensions(seg_len,height)
		piece_dims.append(this_piece_dims)

	xdim = 0
	ydim = height

	for i,dim in enumerate(piece_dims):
		if (i != len(piece_dims) - 1):
			xdim += GAP_SIZE + dim[0]

	label_numbers = list(range(len(piece_dims)))

	bounding_dims = Dimensions(xdim,ydim)

	SidesInfo = namedtuple('SidesInfo','dims labelNums boundingDims topLabelPt')
	out_sides_info = SidesInfo(piece_dims, label_numbers, bounding_dims, top_label_pt)

	return out_sides_info


#must provide start index for the lid labels
#this code is hacky disaster and must be fixed up
def get_brep_lid_info(brep,start_index,material_thickness):
	#get bounding box
	bb = rs.BoundingBox(brep)
	if bb:
		for i, point in enumerate(bb):
			pass
			#rs.AddTextDot(i,point)

	#set height
	height = wge.get_brep_height(brep)
	top_crv = rs.AddPolyline([bb[4],bb[5],bb[6],bb[7],bb[4]])
	bottom_crv = rs.AddPolyline([bb[0],bb[1],bb[2],bb[3],bb[0]])
	top_label_pt, _ = rs.CurveAreaCentroid(top_crv)
	bottom_label_pt, _ = rs.CurveAreaCentroid(bottom_crv)
	rs.DeleteObjects([top_crv,bottom_crv])

	#add text dots
	d1 = rs.AddTextDot(str(start_index),top_label_pt)
	d2 = rs.AddTextDot(str(start_index+1),bottom_label_pt)
	rs.ObjectLayer([d1,d2],"XXX_LCUT_00-GUIDES")

	#get middle section and get polycurve

	g_polycurves = wge.get_brep_plan_cut(brep,height/2,D_TOL) #get plan cut at mid-height
	g_polycurve = g_polycurves[0] #extract the first curve, we assume there will only be one curve.

	seg_count = 0

	if g_polycurve.GetType() == Rhino.Geometry.PolyCurve:
		wge.make_pcurve_ccw(g_polycurve)
	else:
		g_polycurve = wru.polylinecurve_to_polycurve(g_polycurve)
		wge.make_pcurve_ccw(g_polycurve)

	startpts, endpts, divpts = wge.get_polycurve_segment_points(g_polycurve)
	g_polyline = wru.polycurve_to_polyline(g_polycurve, doc.ModelAbsoluteTolerance, doc.ModelAngleToleranceDegrees)
	seg_count = g_polycurve.SegmentCount

	g_polycurve_lid = offset_pcurve(g_polycurve,material_thickness)

	#convert to polyline if needed.
	if g_polycurve.GetType() == Rhino.Geometry.PolylineCurve:
		g_polyline = wru.polycurve_to_polyline(g_polycurve_lid, doc.ModelAbsoluteTolerance, doc.ModelAngleToleranceDegrees)
	else:
		g_polyline = g_polycurve_lid

	crv_bbox = g_polyline.GetBoundingBox(False);
	if not crv_bbox.IsValid:
		return Rhino.Commands.Result.Failure;

	#Print the min and max box coordinates in world coordinates
	Rhino.RhinoApp.WriteLine("World min: {0}", crv_bbox.Min);
	Rhino.RhinoApp.WriteLine("World max: {0}", crv_bbox.Max);

	pt_origin = crv_bbox.Corner(True,True,True)
	pt_x_axis = crv_bbox.Corner(False,True,True)
	pt_y_axis = crv_bbox.Corner(True,False,True)
	plane1 = rs.PlaneFromPoints(pt_origin,pt_x_axis,pt_y_axis)
	plane2 = rs.PlaneFromPoints([0,0,0],[1,0,0],[0,1,0])

	transformation = Rhino.Geometry.Transform.ChangeBasis(rs.coerceplane(plane2),rs.coerceplane(plane1))

	g_polyline.Transform(transformation)

	dims = [rs.Distance(pt_origin,pt_x_axis),rs.Distance(pt_origin,pt_y_axis)]
	#print g_polyline.PointCount
	Dimensions = namedtuple('Dimensions','x y')
	dims = Dimensions(rs.Distance(pt_origin,pt_x_axis),rs.Distance(pt_origin,pt_y_axis))

	SidesInfo = namedtuple('SidesInfo','outline dims') #dims are bounding dims for the curve
	out_sides_info = SidesInfo(g_polyline,dims)

	return out_sides_info


def rc_unroll_ortho():

	THICKNESS = 5.5

	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep

	opt_thickness = Rhino.Input.Custom.OptionDouble(THICKNESS,0.2,1000)
	opt_lid = Rhino.Input.Custom.OptionToggle(False,"No","Yes")

	go.SetCommandPrompt("Select breps to unroll. Breps must be orthogonal (faces at 90 degree angles)")
	go.AddOptionDouble("Thickness", opt_thickness)
	go.AddOptionToggle("Lids", opt_lid)

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
			#print res
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

	LID = opt_lid.CurrentValue
	THICKNESS = opt_thickness.CurrentValue
	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()

	#Get geometry and object lists
	brep_obj_list = []
	brep_geo_list = []
	brep_ids_list = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		brep_obj_list.append(b_obj)
		#For Debug and reference...
		#brep_geo_list.append(b_obj.Geometry)
		#brep_ids_list.append(b_obj.Id)

	#get information for each piece to be output.
	#future implementation should use bounding dims and curves rather than dimension-based system.
	unrolled_brep_info = []
	lid_info = []

	for i,obj in enumerate(brep_obj_list):
		#geometry prep: convert extrusions to breps
		if str(obj.ObjectType) != "Brep":
			new_brep = wru.extrusion_to_brep(obj.Geometry)
		else:
			new_brep = obj.Geometry

		#pull the brep sides info for this solid
		this_brep_side_info = get_brep_sides_info(new_brep,THICKNESS)
		unrolled_brep_info.append(this_brep_side_info)
		num_sides = len(this_brep_side_info.dims)

		#pull the lid info for this solid
		if LID == True:
			this_brep_lid_info = get_brep_lid_info(new_brep, num_sides, THICKNESS)
			lid_info.append(this_brep_lid_info)

	#get dims needed to place this solid's outline curves
	brep_output_bounding_heights = []
	for i,brep_side_info in enumerate(unrolled_brep_info):
		if LID == True:
			brep_output_bounding_heights.append(max(brep_side_info.boundingDims.y,lid_info[i].dims.y)) #lid info needs to become a named tuple as well.
		else:
			brep_output_bounding_heights.append(brep_side_info.boundingDims.y)

	ybase = 0
	#each solid
	for i, brep_side_info in enumerate(unrolled_brep_info):
		top_label_text = wut.number_to_letter(i)
		prefix = top_label_text + "-"
		xbase = 0
		#each piece
		for j,piecedims in enumerate(brep_side_info.dims):
			face_label = prefix + str(brep_side_info.labelNums[j])
			rect = rs.AddRectangle([xbase,ybase,0],piecedims.x,piecedims.y)
			dot = rs.AddTextDot(face_label, rs.CurveAreaCentroid(rect)[0])

			rs.ObjectLayer(dot,"XXX_LCUT_00-GUIDES")
			rs.ObjectLayer(rect,"XXX_LCUT_01-CUT")
			xbase += piecedims[0] + GAP_SIZE

		#add the lids
		if LID == True:

			#transform the lid curve to the basepoint
			lid_curve = lid_info[i].outline
			p1 = rs.WorldXYPlane()
			p2 = rs.PlaneFromNormal([xbase,ybase,0],[0,0,1],[1,0,0])
			orient = Rhino.Geometry.Transform.ChangeBasis(rs.coerceplane(p2),rs.coerceplane(p1))
			lid_curve.Transform(orient)

			#add the curve to the document
			crv_1 = wru.add_curve_to_layer(lid_curve,LCUT_INDICES[1])
			crv_2 = rs.CopyObject(crv_1,[lid_info[i].dims.x + GAP_SIZE, 0, 0]) #change this to use a transform; it's nasty.

			#add text dot
			face_label_1 = prefix + str(len(brep_side_info.dims))
			face_label_2 = prefix + str(len(brep_side_info.dims)+1)
			dot_1 = rs.AddTextDot(face_label_1, rs.CurveAreaCentroid(crv_1)[0])
			dot_2 = rs.AddTextDot(face_label_2, rs.CurveAreaCentroid(crv_2)[0])
			rs.ObjectLayer([dot_1,dot_2],"XXX_LCUT_00-GUIDES")

		top_label = rs.AddTextDot(top_label_text,brep_side_info.topLabelPt)
		rs.ObjectLayer(top_label,"XXX_LCUT_00-GUIDES")
		ybase += brep_output_bounding_heights[i] + GAP_SIZE*4


	rs.UnselectAllObjects()
	rs.Redraw()
	rs.EnableRedraw(True)


def RunCommand( is_interactive ):
	setGlobals()
	rc_unroll_ortho()
	return 0

RunCommand(True)
