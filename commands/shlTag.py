"""
SHL Architects 26-10-2018
v1.0 Sean Lamb (Developer)
sel@shl.dk
-basic
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
from scriptcontext import doc
import Rhino, System

import shl_toolbox_lib.layers as wla
reload(wla)

import shl_toolbox_lib.rhino_util as wru
reload(wru)

import shl_toolbox_lib.fab as wfa
reload(wfa)

import shl_toolbox_lib.geo as wge
reload(wge)

def setGlobals():
	#mm
	global TEXTSIZE, LOCATION, MODE
	global D_TOL, A_TOL
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees


def get_input():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve #Force this to take closed curves

	opt_size = Rhino.Input.Custom.OptionDouble(2,0.2,1000)
	mode_list = ["Curves","TextDots","Both"]
	mode_index = 0

	go.SetCommandPrompt("Select curves to place tags")
	go.AddOptionDouble("TextSize", opt_size)
	go.AddOption
	opt_mode_list = go.AddOptionList("TagMode",mode_list,mode_index)

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
			if go.OptionIndex() == opt_mode_list:
				mode_index = go.Option().CurrentListOptionIndex
			continue
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break

	global TEXTSIZE
	TEXTSIZE = opt_size.CurrentValue
	global MODE
	MODE = mode_list[mode_index]
	global PREFIX
	PREFIX = rs.GetString("Enter a prefix for the tag (Like 'A' or 'floor_'), press Enter for none")
	global DIRPT1, DIRPT2
	DIRPT1 = rs.GetPoint("Base point for sort direction")
	if not DIRPT1: return
	DIRPT2 = rs.GetPoint("End point for sort direction", DIRPT1)
	if not DIRPT2: return

	global SORTDIR
	SORTDIR = DIRPT2 - DIRPT1

	rs.EnableRedraw(False)

	crv_obj_list = []
	crv_geo_list = []
	crv_id_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		crv_geo_list.append(c_obj.Geometry)
		crv_id_list.append(c_obj.Id)
	return crv_geo_list


def offset_pcurve(geo_pcurve,dist):
	"""offset a pcurve on the xy plane. no feedback if it fails."""
	ref_plane = rs.WorldXYPlane()
	offset_curve = geo_pcurve.Offset(ref_plane, -dist, D_TOL, Rhino.Geometry.CurveOffsetCornerStyle.Sharp)
	j = len(offset_curve)
	if len(offset_curve) == 1:
		return offset_curve[0]
	else:
		return Rhino.Commands.Result.Failure


def add_curve_to_layer(curve,layer_index):
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	crv_added = doc.Objects.AddCurve(curve,attribs)
	if crv_added != System.Guid.Empty:
		return crv_added
	return Rhino.Commands.Result.Failure


# compare function for sorting
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


def rc_get_tags(curves):

	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()

	text_buffer = 0
	if PREFIX != None:
		text_buffer = 0.2*len(PREFIX)*TEXTSIZE

	fi = sc.doc.Fonts.FindOrCreate("MecSoft_Font-1", True, False)
	[wge.make_pcurve_ccw(c) for c in curves]
	offset_curves = [offset_pcurve(c,1.4*TEXTSIZE + text_buffer) for c in curves]
	centroids = [c.GetBoundingBox(rs.WorldXYPlane()).Center for c in offset_curves]

	curve_collection = zip(centroids,offset_curves)
	curve_collection = sorted(curve_collection, sortcompare)
	_, offset_curves = zip(*curve_collection)

	tt_locations = []
	td_locations = []
	for c in offset_curves:
		#j = add_curve_to_layer(c,LCUT_INDICES[1]) #uncomment for preview
		bb = c.GetBoundingBox(rs.WorldXYPlane())
		ll_corner = bb.Corner(True,True,True)
		v = rs.VectorCreate([0,0,0],[1,1,0])
		extremes = c.ExtremeParameters(v)

		thept = None
		for i,pt in enumerate(extremes):
			pointat = c.PointAt(extremes[i])
			if thept is not None:
				if pointat.Y < thept.Y: thept = pointat
			else:
				thept = pointat
		tt_locations.append(thept)

		td_locations.append(bb.Center)

	text_guids = []
	dot_guids = []

	tt_text = []
	for i in xrange(len(tt_locations)):
		text = PREFIX + str(i) if PREFIX != None else str(i)
		tt_text.append(text)

	if MODE != "TextDots":
		text_guids = wfa.add_fab_tags(tt_locations,tt_text,TEXTSIZE,Rhino.Geometry.TextJustification.MiddleLeft)
	if MODE != "Curves":
		dot_guids = [ rs.AddTextDot(tt_text[i],td_locations[i]) for i in xrange(len(tt_text))]

	for id in text_guids:
		rs.ObjectLayer(id,"XXX_LCUT_03-LSCORE")
	for id in dot_guids:
		rs.ObjectLayer(id,"XXX_LCUT_00-GUIDES")
	
	if len(text_guids) > 0: [rs.SelectObjects(x) for x in text_guids]
	if len(dot_guids) > 0: [rs.SelectObjects(x) for x in dot_guids]
	sc.doc.Views.Redraw()


def RunCommand( is_interactive ):
	setGlobals()
	crvs = get_input()
	if isinstance(crvs,list):
		rc_get_tags(crvs)
	rs.EnableRedraw(True)
	rs.Redraw()
	return 0

RunCommand(True)
