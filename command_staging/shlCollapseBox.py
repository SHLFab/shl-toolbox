"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
v1.1 08-10-2018: error handling
"""

import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
from scriptcontext import sticky

__commandname__ = "shlCollapseBox"


def rc_collapse_box():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	default_KeepLayer = sc.sticky["KeepLayer"] if sc.sticky.has_key("KeepLayer") else False
	default_IgnoreOpen = sc.sticky["IgnoreOpen"] if sc.sticky.has_key("IgnoreOpen") else False
	opt_KeepLayer = Rhino.Input.Custom.OptionToggle(default_KeepLayer,"No","Yes")
	opt_IgnoreOpen = Rhino.Input.Custom.OptionToggle(default_IgnoreOpen,"No","Yes")
	
	go.SetCommandPrompt("Select Breps")
	go.AddOptionToggle("KeepLayer",opt_KeepLayer)
	go.AddOptionToggle("IgnoreOpenBreps",opt_IgnoreOpen)
	
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
	bHavePreselectedObjects = True
	
	while True:
		res = go.GetMultiple(1,0)
		if res == Rhino.Input.GetResult.Option:
			go.EnablePreSelect(False, True)
			continue
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			rs.Redraw()
			print "No breps were selected!"
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			rs.Redraw()
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break
	
	OPT_IGNORE_OPEN = opt_IgnoreOpen.CurrentValue
	OPT_KEEP_LAYER = opt_KeepLayer.CurrentValue
	sticky["IgnoreOpen"] = OPT_IGNORE_OPEN
	sticky["KeepLayer"] = OPT_KEEP_LAYER
	
	rs.EnableRedraw(False)
	
	input_breps = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		input_breps.append(b_obj.Id)
	
	current_cplane = sc.doc.Views.ActiveView.ActiveViewport.GetConstructionPlane()
	temp_cplane = current_cplane.Plane
	current_cplane.Plane = rs.WorldXYPlane()
	
	solid_brep_count = 0
	for brep in input_breps:
		
		if not rs.IsObjectSolid(brep):
			solid_brep_count += 1
			if OPT_IGNORE_OPEN: continue
			
		if OPT_KEEP_LAYER: brep_layer = rs.ObjectLayer(rs.coerceguid(brep))
		
		exploded = rs.ExplodePolysurfaces(brep,True)
		remaining_srfs = []
		for srf in exploded:
			norm  = rs.SurfaceNormal(srf,[0.5,0.5])
			if 10 > rs.VectorAngle(norm,[0,0,1]) or 10 > rs.VectorAngle(norm,[0,0,-1]):
				rs.DeleteObject(srf)
			else:
				remaining_srfs.append(srf)
		areas = [rs.SurfaceArea(s) for s in remaining_srfs]
		areas = [x[0] for x in areas]
		srfs, areas = zip(*sorted(zip(remaining_srfs,areas),key=lambda x:x[1]))
		pt1, _ = rs.SurfaceAreaCentroid(srfs[-1])
		pt2, _ = rs.SurfaceAreaCentroid(srfs[-2])
		vect = rs.VectorCreate(pt2,pt1)
		vect = rs.VectorDivide(vect,2)
		rs.MoveObject(srfs[-1],vect)
		
		if OPT_KEEP_LAYER: rs.ObjectLayer(srfs[-1],brep_layer)
		rs.SelectObjects(srfs[-1])
		rs.DeleteObjects(srfs[:-1])
		
	
	rs.EnableRedraw(True)
	rs.Redraw()
	
	current_cplane.Plane = temp_cplane
	if solid_brep_count > 0:
		outcome = " and were not collapsed." if OPT_IGNORE_OPEN else " and may have been flattened incorrectly. Check input geometry."
		report = str(solid_brep_count) + " brep(s) were not closed" + outcome
		print report


def RunCommand( is_interactive ):
	rc_collapse_box()
	return 0

RunCommand(True)
