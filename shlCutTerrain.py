import rhinoscriptsyntax as rs
import Rhino
from scriptcontext import doc

import itertools

import shl_toolbox_lib_dev.layers as wla
reload(wla)
import shl_toolbox_lib_dev.util as wut
reload(wut)
import shl_toolbox_lib_dev.rhino_util as wrh
reload(wrh)

def set_globals():
	global D_TOL, A_TOL
	
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees


def get_section_division(height,thickness):
	num_sections = int(height/thickness)
	remainder = height%thickness
	return [num_sections,remainder]


def get_section_planes(brep,thickness):
	bb = rs.BoundingBox(brep)
	if bb:
		for i, point in enumerate(bb):
			pass
			#rs.AddTextDot(i,point)
	
	height = rs.Distance(bb[0],bb[4])
	xy_plane = rs.WorldXYPlane()
	s_heights = wut.frange(0.1,height,thickness)
	
	planes = [rs.MovePlane(xy_plane, [0,0,x]) for x in s_heights]
	
	return planes


def get_section(brep,plane):
	g = Rhino.Geometry.Intersect.Intersection.BrepPlane(brep,plane,D_TOL)
	return g[1]


def extrude_down_srf(srf):
	bb = rs.BoundingBox(srf)
	if bb:
		for i, point in enumerate(bb):
			pass
			#rs.AddTextDot(i,point)
	
	height = rs.Distance(bb[0],bb[4])
	path_line = rs.AddLine(bb[4],bb[0])
	xy_plane = rs.WorldXYPlane()
	extruded_srf = rs.ExtrudeSurface(srf,path_line,True)
	rs.DeleteObject(path_line)
	return extruded_srf


def rc_terraincut():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	opt_thickness = Rhino.Input.Custom.OptionDouble(2,0.2,1000)
	opt_sections = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_inplace = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	
	go.SetCommandPrompt("Select breps to extract plan cuts")
	go.AddOptionDouble("Thickness", opt_thickness)
	go.AddOptionToggle("MakeSections", opt_sections)
	go.AddOptionToggle("InPlace", opt_inplace)
	
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
			print res
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

	global BOOL_SECTIONS
	BOOL_SECTIONS = opt_sections.CurrentValue
	global THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()
	bool_inplace = opt_inplace.CurrentValue
	
	#get object
	b_obj = go.Object(0).Object()
	
	if str(b_obj.ObjectType) != "Brep":
		print "make it a brep"
		b_geo = extrusion_to_brep(b_obj.Geometry)
	else:
		b_geo = b_obj.Geometry
	
	bool_merged = Rhino.Geometry.Brep.MergeCoplanarFaces(b_geo,D_TOL)
	extruded_srf_id = extrude_down_srf(wrh.docobj_to_guid(b_obj))
	extruded_srf = rs.coercebrep(extruded_srf_id)
	
	planes = get_section_planes(b_geo,THICKNESS)
	
	section_curves = [get_section(extruded_srf,p) for p in planes]
	
	for p in planes:
		get_section(extruded_srf,p) for p in planes
	
	lcut_ind = wla.get_lcut_layers()
	
	for i,curves_list in enumerate(section_curves):
		wrh.add_curves_to_layer(section_curves[i],lcut_ind[1])
	
#	rs.DeleteObject(extruded_srf_id)
	return 0
	
if __name__ == "__main__":
	set_globals()
	rc_terraincut()