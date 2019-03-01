"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
v1.1 08-10-2018: error handling
"""

import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

__commandname__ = "shlCollapseBox"


def rc_collapse_box():
	
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	default_length = sc.sticky["length"] if sc.sticky.has_key("length") else 100
	default_delete = sc.sticky["delete"] if sc.sticky.has_key("delete") else True
	
	go.SetCommandPrompt("Select Breps")

	go.GroupSelect = True
	go.SubObjectSelect = False
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)
	go.EnableClearObjectsOnEntry(False)
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.DeselectAllBeforePostSelect = False
	
	res = None
	bHavePreselectedObjects = False
	while True:
		res = go.GetMultiple(1,0)
		if res == Rhino.Input.GetResult.Option:
			#print res
			go.EnablePreSelect(False, True)
			continue
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			print "No Breps Selected!"
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break
	
	rs.EnableRedraw(False)
	
	input_breps = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		input_breps.append(b_obj.Id)
	
	for brep in input_breps:
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
		#determine which one to kill here
		pt1, _ = rs.SurfaceAreaCentroid(srfs[-1])
		pt2, _ = rs.SurfaceAreaCentroid(srfs[-2])
		vect = rs.VectorCreate(pt2,pt1)
		vect = rs.VectorDivide(vect,2)
		rs.MoveObject(srfs[-1],vect)
		rs.SelectObjects(srfs[-1])
		rs.DeleteObjects(srfs[:-1])
		
	
	rs.EnableRedraw(True)
	rs.Redraw()


def RunCommand( is_interactive ):

	rc_collapse_box()
	return 0

RunCommand(True)
