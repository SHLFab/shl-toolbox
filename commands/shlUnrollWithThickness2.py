"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
-removed interactive
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc, sticky
import scriptcontext as sc
import itertools
from collections import namedtuple

from System.Collections.Generic import List
from System.Collections.Generic import IEnumerable
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


def get_reference_vector(b_obj):
	"""pick a reference vector for deciding surface category.
	note that we can't pick [0,1,0] because the brep might be on a 45deg angle."""
	base_ref_vect = rs.VectorCreate([0,1,0],[0,0,0])
	up = rs.coerce3dvector([0,0,1])
	down = rs.coerce3dvector([0,0,-1])
	epsilon = 0.5
	
	faces = b_obj.Faces
	print faces.Count
	
	ref_faces = []
	ref_angle_rotation = 90
	for k in faces:
		v = k.NormalAt(0.5,0.5) #top and botom of extrusion have IsSurface = False (why?)
		if not (v.EpsilonEquals(up,epsilon) or v.EpsilonEquals(down,epsilon)):
			ref_faces.append(k)
			angle = rs.VectorAngle(v,base_ref_vect)
			angle = angle%90
			print angle
			ref_angle_rotation = min(ref_angle_rotation,angle)
	
	new_ref_vector = rs.VectorRotate(base_ref_vect,ref_angle_rotation,[0,0,1])
	#debug: verify this angle is good
#	for k in faces:
#		v = k.NormalAt(0.5,0.5) #top and botom of extrusion have IsSurface = False (why?)
#		if not (v.EpsilonEquals(up,epsilon) or v.EpsilonEquals(down,epsilon)):
#			ref_faces.append(k)
#			angle = rs.VectorAngle(v,new_ref_vector)
#			angle = angle%180
#			print angle
	
	return new_ref_vector

def adjust_face_edges(face,cat,adjust_dist):
	epsilon = 0.5
	normal = face.NormalAt(0.5,0.5)
	b = face.Brep
	
	adj_edge_inds = face.AdjacentEdges()
	
	brep = face.DuplicateFace(False)
	brep_edges = brep.Edges
	edge_concavity = [-1 for i in adj_edge_inds]
	
	###FUNCTION THIS OUT###
	
	#get the midpoints of the brepform's edges
	brepform_midpoints = []
	for i,brepform_edge in enumerate(brep_edges):
		brepform_mid = brepform_edge.Domain.Mid
		brepform_midpoints.append(brepform_edge.PointAt(brepform_mid))
	
	print "start thru adjacent edge list"
	#need to identify to concavity of each edge and hold it in a list that is
	#ordered the same as the brepform edge list. once this is done we can work directly with the brep.
	for i in adj_edge_inds:
		edge = b.Edges.Item[i]
		mid = edge.Domain.Mid
		conc = edge.ConcavityAt(mid,1)
		
		p = edge.PointAt(mid) #display
		rs.AddTextDot(i,p) #display
		for j,brepform_mp in enumerate(brepform_midpoints):
			print "looping through brepform midpoints"
			if p.EpsilonEquals(brepform_mp,0.5):
				print "found an edge equality"
				edge_concavity[j]=conc
				break
	
	#display convex/concave by brep midpoints
	for i,mp in enumerate(brepform_midpoints):
		rs.AddTextDot(edge_concavity[i],mp)
	
	###FUNCTION THIS OUT END###
	
	edge_vectors = get_edge_vectors(brep,adjust_dist)
	print edge_vectors
	
	
	for i,edge in enumerate(brep_edges):
		xform = Rhino.Geometry.Transform.Translation(edge_vectors[i])
		#many questions here... how to supply an enum
		testList = List[Rhino.Geometry.ComponentIndex]()
		testList.Add(Rhino.Geometry.ComponentIndex(edge,0))
		brep.TransformComponent(testList,edge_vectors[i],0.1,10,False)
	
	
	return None

def get_edge_vectors(s_brep,length):
	"""gets the direction vectors for extending the edges of the one-surface brep"""
	edges = s_brep.Edges
	normal = s_brep.Faces[0].NormalAt(0.5,0.5)
	
	midpoints = []
	for edge in edges:
		mp = edge.Domain.Mid
		midpoints.append(edge.PointAt(mp))
	
	edge_vectors = []
	for i, edge in enumerate(edges):
		#get directions to test moving midpoint
		start = edge.StartVertex.Location
		end = edge.EndVertex.Location
		v = rs.VectorCreate(end,start)
		xprod1 = Rhino.Geometry.Vector3d.CrossProduct(normal,v)
		xprod1 = rs.VectorUnitize(xprod1)
		xprod2 = rs.VectorReverse(xprod1)
		p1 = edge.PointAt(edge.Domain.Mid) + xprod1
		p2 = edge.PointAt(edge.Domain.Mid) + xprod2
		print "p1", p1
		print "p2", p2
		dist1 = distance_to_brep(s_brep,p1)
		dist2 = distance_to_brep(s_brep,p2)
		print "dist1", dist1
		print "dist2", dist2
		if dist1 > dist2:
			edge_vectors.append(rs.VectorScale(xprod1,length))
		else:
			edge_vectors.append(rs.VectorScale(xprod2,length))
	
	return edge_vectors

def distance_to_brep(brep, point):
	cp = brep.ClosestPoint(point)
	dist = cp.DistanceTo(point)
	return dist

def get_face_category(f,v):
	"""pick category:
	0: side srfs that get extended
	1: side srfs that get shortened
	2: top surfaces"""
	normal = f.NormalAt(0.5,0.5)
	epsilon = 0.5
	up = rs.coerce3dvector([0,0,1])
	down = rs.coerce3dvector([0,0,-1])
	compare_angle = min(rs.VectorAngle(normal,v),rs.VectorAngle(normal,rs.VectorReverse(v)))
	
	if normal.EpsilonEquals(up,epsilon) or normal.EpsilonEquals(down,epsilon):
		return 2
	elif 88 < compare_angle < 92:
		return 1
	else:
		return 0


#main processing here
def unroll_brep_with_thickness(b_obj):
	
	ref_vect = get_reference_vector(b_obj)
	
	for i,face in enumerate(b_obj.Faces):
		if i == 6:
			cat = get_face_category(face,ref_vect)
			extended = adjust_face_edges(face,cat,THICKNESS)
			print cat
			mp = Rhino.Geometry.AreaMassProperties.Compute(face)
			p = mp.Centroid
			rs.AddTextDot(str(cat),p)
	return None

def rc_unroll_ortho():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	default_thickness = sticky["thickness"] if sticky.has_key("thickness") else 5.5
	default_lid = sticky["lid"] if sticky.has_key("lid") else False
	
	opt_thickness = Rhino.Input.Custom.OptionDouble(default_thickness,0.2,1000)
	opt_lid = Rhino.Input.Custom.OptionToggle(default_lid,"No","Yes")

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
	global LCUT_INDICES, THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	LCUT_INDICES = wla.get_lcut_layers()

	#Get geometry and object lists
	brep_obj_list = []
	brep_geo_list = []
	brep_ids_list = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		brep_obj_list.append(b_obj)
	
	#use world cplane
	current_cplane = sc.doc.Views.ActiveView.ActiveViewport.GetConstructionPlane()
	temp_cplane = current_cplane.Plane
	current_cplane.Plane = rs.WorldXYPlane()
	
	#get information for each piece to be output.
	#future implementation should use bounding dims and curves rather than dimension-based system.
	unrolled_brep_info = []
	lid_info = []
	
	SELECT_GUIDS = []
	
	#convert to breps
	input_brep_geo = []
	for i,obj in enumerate(brep_obj_list):
		#geometry prep: convert extrusions to breps
		if str(obj.ObjectType) != "Brep":
			new_brep = wru.extrusion_to_brep(obj.Geometry)
		else:
			new_brep = obj.Geometry
		input_brep_geo.append(new_brep)
	
	for geo in input_brep_geo:
		unroll_brep_with_thickness(geo)
	
	
	sticky["thickness"] = THICKNESS
	sticky["lid"] = LID
	
	current_cplane.Plane = temp_cplane
	rs.UnselectAllObjects()
	rs.SelectObjects(SELECT_GUIDS)
	rs.Redraw()
	rs.EnableRedraw(True)


def RunCommand( is_interactive ):
	setGlobals()
	rc_unroll_ortho()
	return 0

RunCommand(True)
