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
import shl_toolbox_lib_dev.geo as wge
reload(wge)

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
	s_heights = wut.frange(-0.001,height,thickness)
	
	planes = [rs.MovePlane(xy_plane, [0,0,x]) for x in s_heights]
	
	return planes


def get_section(brep,plane):
	g = Rhino.Geometry.Intersect.Intersection.BrepPlane(brep,plane,D_TOL)
	return g[1]


def extrude_down_srf(srf,height=None):
	"""if no height input, extrude down by the bounding box height*2."""
	if height == None:
		bb = rs.BoundingBox(srf)	
		height = rs.Distance(bb[0],bb[4])*2
	if height < D_TOL:
		return None
	
	path_line = rs.AddLine([0,0,0],[0,0,-height])
	xy_plane = rs.WorldXYPlane()
	extruded_srf = rs.ExtrudeSurface(srf,path_line,True)
	rs.DeleteObject(path_line)
	return extruded_srf


def get_frame_brep(outline_srf,thickness):
	outline_crv = rs.JoinCurves(rs.DuplicateEdgeCurves(outline_srf))
	pt, _ = rs.CurveAreaCentroid(outline_crv)
	inner_crv = rs.OffsetCurve(outline_crv,pt,2,[0,0,1])
	rs.MoveObjects([outline_crv,inner_crv],[0,0,thickness*2])
	
	path = rs.AddLine([0,0,0],[0,0,-thickness*4])
	inner_brep = rs.ExtrudeCurve(inner_crv,path)
	outer_brep = rs.ExtrudeCurve(outline_crv,path)
	rs.CapPlanarHoles(inner_brep)
	rs.CapPlanarHoles(outer_brep)
	
	frame_brep = rs.BooleanDifference([outer_brep],[inner_brep])
	rs.DeleteObjects([outline_crv,inner_crv])
	return frame_brep

#def get_top_curve_info(brep):
#	#right now hardcoded to not deal with multiple breps at the final step. to revise if needed.
#	h_tol = 3
#	bdims = wge.get_bounding_dims(brep)
#	brep_faces = wge.get_extreme_srf(brep, h_tol)
#
#	crvs_by_brep = []
#
#	for f in brep_faces:
#		crvs = []
#		inds = f.AdjacentEdges()
#		for i in inds:
#			k = brep.Edges
#			crvs.append(brep.Edges[i])
#		crvs = Rhino.Geometry.Curve.JoinCurves(crvs,D_TOL)
#	crvs_by_brep.append(crvs)
#
#	crvs_by_brep = crvs_by_brep[0] #to fix this later. only deals w one brep for now
#	list_curves = []
#	for pc in crvs_by_brep:
#		if pc.GetType() != Rhino.Geometry.PolyCurve:
#			pc = wru.polylinecurve_to_polycurve(pc)
#
#		wge.make_pcurve_ccw(pc)
#		list_curves.append(pc)
#
#	return list_curves


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

#	rs.EnableRedraw(False)

	global BOOL_SECTIONS
	BOOL_SECTIONS = opt_sections.CurrentValue
	global THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()
	bool_inplace = opt_inplace.CurrentValue
	
	#set layers
	lcut_ind = wla.get_lcut_layers()
	
	#get topography object
	b_obj = go.Object(0).Object()
	
	if str(b_obj.ObjectType) != "Brep":
		print "make it a brep"
		b_geo = extrusion_to_brep(b_obj.Geometry)
	else:
		b_geo = b_obj.Geometry
	
	#extrude down the topography surface in order to take sections
	bool_merged = Rhino.Geometry.Brep.MergeCoplanarFaces(b_geo,D_TOL)
	extruded_srf_id = extrude_down_srf(wrh.docobj_to_guid(b_obj))
	extruded_srf = rs.coercebrep(extruded_srf_id)
	
	#get planes for sectioning.
	planes = get_section_planes(b_geo,THICKNESS)
	
	#get the section curves and the section srfs
	section_srfs = []
	for i,plane in enumerate(planes):
		plane_sections = get_section(extruded_srf,plane)
		current_level_srfs = [Rhino.Geometry.Brep.CreatePlanarBreps(crv)[0] for crv in plane_sections]
		section_srfs.append(current_level_srfs)
	rs.DeleteObject(extruded_srf_id)
	
	
	extruded_section_breps = []
	boolean_section_breps = []
	
	short_guide = rs.AddLine([0,0,0],[0,0,-THICKNESS])
	long_guide = rs.AddLine([0,0,0],[0,0,-THICKNESS*4])
	
	frame_base_surface = None
	
	for i,brep_level in enumerate(section_srfs):
		extruded_breps = []
		for brep in brep_level:
			srf_added = wrh.add_brep_to_layer(brep,lcut_ind[1])
			if i == 0: frame_base_surface = rs.CopyObject(srf_added)
			guide_crv = rs.AddLine([0,0,0],[0,0,-THICKNESS])
			extruded_breps.append(rs.ExtrudeSurface(srf_added,short_guide))
			rs.DeleteObject(srf_added)
		extruded_section_breps.append(extruded_breps)
	
#	make the frame brep
	num_divisions = len(section_srfs)
	frame_brep = get_frame_brep(frame_base_surface,THICKNESS*num_divisions)
	
	section_final_breps = []
	for i,brep_level in enumerate(extruded_section_breps):
		boolean_level_ind = i+2
		
		#if we are at a level that should be hollowed-out, do so.
		if boolean_level_ind < len(extruded_section_breps):
			final_level_breps = []
			#iterate through the "host breps": breps that receive boolean operations.
			for host_brep in brep_level:
				
				#prepare: extrude the breps two levels above the current level.
				final_brep = None
				boolbreps = []
				for child_brep in section_srfs[boolean_level_ind]:
					boolbreps.append(rs.ExtrudeSurface(child_brep,long_guide))
				rs.ObjectLayer(boolbreps,"XXX_LCUT_03-LSCORE")
				
				#prepare: get a frame brep for filling in edges of the brep.
				frame_instance = rs.CopyObject(frame_brep,[0,0,i*THICKNESS])
				
				#boolean: crop out the portion that will be used for filling in.
				frame_intersection = rs.BooleanIntersection(frame_instance,host_brep,False)
				if len(frame_intersection) != 0:
					preview_intersection = rs.CopyObject(frame_intersection)
					rs.ObjectLayer(preview_intersection,"XXX_LCUT_04-ENGRAVE")
				
				#boolean: hollow out the host.
				boolean_result = rs.BooleanDifference([host_brep],boolbreps,False)
				rs.DeleteObject(frame_instance)
				rs.DeleteObjects(boolbreps)
				
				#if there was a boolean result, union it with the frame.
				if len(boolean_result) == 1:
					
					boolean_result = boolean_result[0]
					if len(frame_intersection) !=0:
						framed_brep = rs.BooleanUnion([boolean_result,frame_intersection],True)
						framed_brep = framed_brep[0]
					else:
						framed_brep = boolean_result
					
					#merge faces.
					rc_b = rs.coercebrep(framed_brep)
					rc_b.MergeCoplanarFaces(D_TOL)
					merged_brep = doc.Objects.Add(rc_b)
					rs.DeleteObject(framed_brep)
					rs.ObjectLayer(merged_brep,"XXX_LCUT_02-SCORE")
					
					#if the result of the boolean operations is different from the original slice brep,
					#use it as the final brep. otherwise use the host brep.
					if framed_brep is not None: boolean_result = [merged_brep]
					a = rs.coercebrep(boolean_result)
					b = rs.coercebrep(host_brep)
					if abs( a.GetVolume() - b.GetVolume() ) > 0.01:
						rs.DeleteObject(host_brep)
						final_brep = boolean_result
					else:
						final_brep = host_brep
				else:
					final_brep = host_brep
				
				final_level_breps.append(final_brep)
			section_final_breps.append(final_level_breps)
		else:
			section_final_breps.append(extruded_section_breps[i])
	
	#get the final surfaces by iterating through the final section breps and extracting the top faces.
	final_srfs = []
	for i,breplevel in enumerate(section_final_breps):
		final_srfs_level = []
		for brep in breplevel:
			xsrf = wge.get_extreme_srf(rs.coercebrep(brep),5)
			final_srfs_level.append(doc.Objects.Add(xsrf[0].DuplicateFace(False))) #must properly type the faces
		rs.ObjectLayer(final_srfs_level,"XXX_LCUT_03-LSCORE")
		final_srfs.append(final_srfs_level)
	
	rs.DeleteObject(frame_brep)
	
	return 0
	
if __name__ == "__main__":
	set_globals()
	rc_terraincut()