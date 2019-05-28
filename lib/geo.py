"""help docstring"""
#workshop_lib
#rhino geometry functions

#SHL Architects
#Sean Lamb 2018-11-02
#TODO: define an __all__

import rhinoscriptsyntax as rs
import Rhino
from scriptcontext import doc
import scriptcontext as sc
import System

import shl_toolbox_lib.util as wut
reload(wut)

import random as rand
from collections import namedtuple


def get_bounding_dims(brep):
	"""return bounding box x,y,z dims for a brep or many breps"""
	bb = rs.BoundingBox(brep)
	Dimensions = namedtuple('Dimensions','X Y Z')
	dims = Dimensions( rs.Distance(bb[0],bb[1]), rs.Distance(bb[0],bb[3]), rs.Distance(bb[0],bb[4]) )
	return dims


def get_brep_base_plane(brep):
	"""param: brep
	return: xy plane at bb lower left corner"""
	bb = rs.BoundingBox(brep)
	return rs.PlaneFromNormal(bb[0],[0,0,1],[1,0,0])


def get_brep_height(brep):
	"""get height of a brep's bounding box
 	param: brep
	return: height (z of bounding box)"""
	bb = rs.BoundingBox(brep)
	return rs.Distance(bb[0],bb[4])


def get_brep_plan_cut(brep,cut_height,tolerance):
	"""cut a brep at a certain height. returns list of geometry.polycurve
	tolerance should be the document tolerance.
	NOTE: attempts to join the curves."""
	bb = rs.BoundingBox(brep)
	height = rs.Distance(bb[0],bb[4])

	#get middle section and get polycurve
	midplane_pts = rs.MoveObjects(bb[0:4],[0,0,cut_height])
	plane = rs.PlaneFromPoints(bb[0],bb[1],bb[3])
	rs.DeleteObjects(midplane_pts)

	bool_merged = Rhino.Geometry.Brep.MergeCoplanarFaces(brep,tolerance)
	g = Rhino.Geometry.Intersect.Intersection.BrepPlane(brep,plane,tolerance)
	g_polycurves = g[1]
	g_polycurves = Rhino.Geometry.Curve.JoinCurves(g_polycurves,tolerance)

	return g_polycurves


def get_brep_plan_cut_use_plane(brep,plane,tolerance):
	"""cut a brep at a certain plane. returns list of geometry.polycurve
	merge_tolerance should be the document tolerance.
	NOTE: attempts to join the curves."""

	bool_merged = Rhino.Geometry.Brep.MergeCoplanarFaces(brep,tolerance)
	g = Rhino.Geometry.Intersect.Intersection.BrepPlane(brep,plane,tolerance)
	g_polycurves = g[1]
	g_polycurves = Rhino.Geometry.Curve.JoinCurves(g_polycurves,tolerance)

	return g_polycurves


def get_internal_angles(pts):
	"""get the internal angles of a set of pts representing a
	counter-clockwise polyline."""
	angle_list = []
	for i in xrange(0,len(pts)):
		start = (i-1)%len(pts)
		mid = (i)%len(pts)
		end = (i+1)%len(pts)
		line_a = [pts[mid],pts[end]]
		line_b = [pts[mid],pts[start]]

		angle = rs.Angle2(line_a, line_b) #returns [smaller,larger] angles.
		angle_index = 1

		vect_a = rs.VectorCreate(line_a[0],line_a[1])
		vect_b = rs.VectorCreate(line_b[0],line_b[1])
		if wut.xprod(vect_a,vect_b) > 0:
			angle_index = 0

		angle_list.append(angle[angle_index])
	return angle_list


def make_pcurve_ccw(geo_polycurve):
	"""accepts a rhino geometry.polycurve object and makes it counter-clockwise.
	TODO: make this general for all curve types if possible."""
	orientation = geo_polycurve.ClosedCurveOrientation()
	if str(orientation) == "Clockwise":
		geo_polycurve.Reverse()


def get_interior_pt(g_curve,sample_distance,quality=10):
	"""get an interior point in the brep.
	g_curve: curve geometry
	quality=100: number of spots to try.
	return: point3d."""
	vector_size = doc.ActiveDoc.ModelAbsoluteTolerance*5000

	planarBrep = Rhino.Geometry.Brep.CreatePlanarBreps(g_curve)[0]
	srf = planarBrep.Faces[0]
	domU = srf.Domain(0)
	domV = srf.Domain(1)

	pts = []
	outside =  Rhino.Geometry.PointContainment.Outside
	failure = Rhino.Geometry.PointContainment.Unset

	v = rs.VectorCreate([0,0,0],[0,1,0])
	extremes = g_curve.ExtremeParameters(v)

	interior_pt = None
	for param in extremes:

		for j in xrange(quality):

			pointat = g_curve.PointAt(param)
			move_vector = rs.VectorCreate([0,0,0],[rand.uniform(-1,1),rand.uniform(-1,1),0])
			move_vector = rs.VectorScale( rs.VectorUnitize(move_vector), sample_distance )
			transform = Rhino.Geometry.Transform.Translation(move_vector)
			pointat.Transform(transform)
			rs.AddPoint(pointat)
			print g_curve.Contains(pointat)
			if g_curve.Contains(pointat) != ( outside or failure ):
				print "containment"
				return pointat
	return pointat


def get_polycurve_segment_points(g_polycurve):
	"""returns [startpts,endpts,midpts] list for a polycurve"""
	startpts = []
	endpts = []
	midpts = []

	for i in xrange(g_polycurve.SegmentCount):
		seg = g_polycurve.SegmentCurve(i)
		seg_len = seg.GetLength()
		endpts.append(seg.PointAtEnd)
		startpts.append(seg.PointAtStart)
		midpts.append(seg.PointAtLength(seg_len/2))

	return [startpts,endpts,midpts]


def get_extreme_srf(brep,h_tol,top=True):

	"""
	algorithm:
	1. pick n random pts on each surface, P
	2. get the 3 lowest points in P (disabled for now; just does straight averaging)
	3. determine their dot product with the unit z and their avg height
	4. throw out all surfaces that aren't within the dot product threshold.
	5. of the remaining surfaces, sort to get the lowest one. if any of them have a height within the
	height tolerance, select them as well.
	6. return these lowest srfs.
	"""
	sample_num = 100
	s_avg_normal, s_avg_height, s_srf = [ [],[],[] ]
	dotprod_threshold = 0.9

	for s in brep.Faces:
		u, v = [s.Domain(0), s.Domain(1)]
		test_params = [(rand.uniform(u.T0,u.T1), rand.uniform(v.T0,v.T1)) for i in xrange(sample_num)]
		test_points = [s.PointAt(p[0],p[1]) for p in test_params]
		#sort params and points by z
		test_points, test_params = zip(*sorted(zip(test_points,test_params), key=lambda x: x[0].Z, reverse=False))

		test_Z = sum([t.Z for t in test_points]) / len(test_points)
		dotprods = [rs.VectorDotProduct(s.NormalAt(p[0],p[1]),[0,0,1]) for p in test_params]
		avg_dotprod = sum(dotprods) / len(dotprods)

		if top == False: avg_dotprod = -avg_dotprod #flip if searching for bottom.
		if (avg_dotprod) > dotprod_threshold:
			s_avg_normal.append(avg_dotprod)
			s_avg_height.append(test_Z)
			s_srf.append(s)
#			for i,p in enumerate(test_points):
#				docpt = rs.AddPoint(p)
#				if i<5:
#					rs.ObjectLayer(docpt,"Layer 05")

	#if top == True, search from the top...
	if top == False:
		s_avg_normal,s_avg_height,s_srf = zip(*sorted(zip(s_avg_normal,s_avg_height,s_srf), key=lambda x: x[1],reverse=False))

		height_threshold = s_avg_height[0] + h_tol
		extreme_surfaces = []

		for srf,height in zip(s_srf,s_avg_height):
			if height < height_threshold: extreme_surfaces.append(srf)
	else:
		s_avg_normal,s_avg_height,s_srf = zip(*sorted(zip(s_avg_normal,s_avg_height,s_srf), key=lambda x: x[1],reverse=True))

		height_threshold = s_avg_height[0] - h_tol
		extreme_surfaces = []

		for srf,height in zip(s_srf,s_avg_height):
			if height > height_threshold: extreme_surfaces.append(srf)

	return extreme_surfaces


def brepClosestPoint(b1,b2,precision):
	bb1 = b1.GetBoundingBox(False)
	bbPt1 = bb1.PointAt(random.random(), random.random(), random.random())

	pt1 = b1.ClosestPoint(bbPt1)
	pt2 = b2.ClosestPoint(pt1)

	for i in range(precision):
		pt1 = b1.ClosestPoint(pt2)
		pt2 = b2.ClosestPoint(pt1)

	print 'done brepclosestpoint'
	print 'pts are', pt1, pt2
	return [pt1,pt2]


def multi_test_in_or_out(test_crv, vols):
	"""tests midpoint of curve for containment inside one of several volumes
	#returns True if point is inside at least one of the volumes, otherwise False"""
	rc=False
	dom=rs.CurveDomain(test_crv)
	if dom==None:
		#debug print "bad domain"
		return rc
	c_midpt=rs.EvaluateCurve(test_crv,(dom[0]+dom[1])/2)
	if c_midpt==None:
		#debug print "bad curve"
		return rc
	for vol in vols:
		if rs.IsPointInSurface(vol,c_midpt,True,sc.doc.ModelAbsoluteTolerance):
			#curve is inside one of the volumes
			rc=True
			break
	return rc


def check_planar_curves_collision(crvs):
	#curves must be planar, returns True if any two curves overlap
	for i in range(len(crvs)-1):
		for j in range(i+1,len(crvs)):
			if rs.PlanarCurveCollision(crvs[i],crvs[j]): return True
	return False


def trim_boundary(e_crvs,cb_crvs,tol,inside=True):
	"""input:
	e_crvs: etch curves to be trimmed
	cb_crvs: closed boundary curves
	tol: tolerance. document tolerance recommended
	inside=True: trim the inside if true, trim outside if false
	returns the trimmed curves.
	NOTE: assumes redraw is turned off. assumes curves are planar.
	future versions to use projection method to avoid these assumptions."""

	#remove non-crv inputs
	e_crvs = [x for x in e_crvs if rs.ObjectType(x) == 4]
	cb_crvs = [x for x in cb_crvs if rs.ObjectType(x) == 4]

	#split curves
	split_crvs = []
	for e in e_crvs:
		intersection_list = []
		for c in cb_crvs:
			ccx_out = rs.CurveCurveIntersection(e,c,tol)
			if ccx_out is None: continue
			params = [x[5] for x in ccx_out if x[0] == 1] #if pt intersection type; get param on etch crv
			intersection_list.extend(params)
		if intersection_list: split_crvs.extend(rs.SplitCurve(e,intersection_list))

	#append non-split curves
	no_split = []
	for e in e_crvs:
		id=sc.doc.Objects.Find(e)
		if id != None: no_split.append(e)
	split_crvs.extend(no_split)
	#rs.ObjectLayer(split_crvs,"XXX_LCUT_02-SCORE")

	#build regions for boundary test
	srfs = rs.AddPlanarSrf(cb_crvs)
	line=rs.AddLine([0,0,-5],[0,0,5])
	rs.MoveObjects(srfs,[0,0,-5])
	vols = []
	for srf in srfs:
		ext=rs.ExtrudeSurface(srf,line,True)
		if ext != None: vols.append(ext)
	rs.DeleteObjects(srfs)
	rs.DeleteObject(line)

	#categorize inside/outside curves
	keep_crvs = []
	delete_crvs = []
	for c in split_crvs:
		if inside == True:
			keep_crvs.append(c) if not multi_test_in_or_out(c,vols) else delete_crvs.append(c)
		else:
			keep_crvs.append(c) if multi_test_in_or_out(c,vols) else delete_crvs.append(c)

	#rs.ObjectLayer(keep_crvs,"XXX_LCUT_04-ENGRAVE")
	rs.DeleteObjects(vols)
	rs.DeleteObjects(delete_crvs)

	return keep_crvs
