import rhinoscriptsyntax as rs
import Rhino
from scriptcontext import doc, sticky
import System as sys

import itertools

import shl_toolbox_lib.layers as wla
reload(wla)
import shl_toolbox_lib.util as wut
reload(wut)
import shl_toolbox_lib.rhino_util as wrh
reload(wrh)
import shl_toolbox_lib.geo as wge
reload(wge)

def set_globals():
	global D_TOL, A_TOL
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees
	
	global LASER_GAP
	LASER_GAP = 4
	
	global THICKNESS, BORDER_THICKNESS, BORDER_BOOL
	global LCUT_INDICES
	global JOIN_ERROR, JOIN_DIST
	JOIN_ERROR = False
	JOIN_DIST = 0


def get_section_division(height,thickness):
	num_sections = int(height/thickness)
	remainder = height%thickness
	return [num_sections,remainder]


def get_section_planes(brep,thickness):
	bb = rs.BoundingBox(brep)
	
	start_height = bb[0].Z
	end_height = bb[4].Z
	xy_plane = rs.WorldXYPlane()
	heights = wut.frange(start_height,end_height,thickness)
	
	planes = [rs.MovePlane(xy_plane, [0,0,z]) for z in heights]
	
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


def get_frame_brep(outline_srf,border_thickness,thickness):
	edge_crvs = rs.DuplicateEdgeCurves(outline_srf)
	outline_crv = rs.JoinCurves(edge_crvs)
	pt, _ = rs.CurveAreaCentroid(outline_crv)
	inner_crv = rs.OffsetCurve(outline_crv,pt,border_thickness,[0,0,1])
	rs.MoveObjects([outline_crv,inner_crv],[0,0,thickness*2])
	
	path_line = rs.AddLine([0,0,0],[0,0,-thickness*4])
	inner_brep = rs.ExtrudeCurve(inner_crv,path_line)
	outer_brep = rs.ExtrudeCurve(outline_crv,path_line)
	rs.CapPlanarHoles(inner_brep)
	rs.CapPlanarHoles(outer_brep)
	
	frame_brep = rs.BooleanDifference([outer_brep],[inner_brep])
	rs.DeleteObjects([outline_crv,inner_crv])
	rs.DeleteObjects(edge_crvs)
	rs.DeleteObject(path_line)
	return frame_brep


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


def get_breps_on_layer(layername):
	buildings = rs.ObjectsByLayer(layername)
	breps = []
	for b in buildings:
		if rs.ObjectType(b) == 16 or rs.ObjectType(b) == 1073741824: breps.append(b)
	return breps


def get_curves_on_layer(layername):
	objs = rs.ObjectsByLayer(layername)
	crvs = []
	for o in objs:
		if rs.ObjectType(o) == 4: crvs.append(o)
	return crvs


#CURRENTLY WORKING ON THIS LAYER
def get_building_booleans(building_breps,planes):
	
	bldg_intersection_boolean_breps = []
	bldg_intersection_breps = []
	
	sections = []
	#get the sections organized by level
	for i, plane in enumerate(planes):
		sections_level = []
		for b in building_breps:
			plane_sections = get_section(rs.coercebrep(b),plane)
			if not plane_sections: continue
			else: sections_level.append(plane_sections)
		sections.append(sections_level)
	
	#extrude the sections organized by level
	boolean_breps = []
	for i,level in enumerate(sections):
		boolean_breps_level = []
		for section in level:
			pb = Rhino.Geometry.Brep.CreatePlanarBreps(section)
			pb = pb[0]
			srf_added = wrh.add_brep_to_layer(pb,LCUT_IND[4])
			b = rs.ExtrudeSurface(srf_added,SHORT_GUIDE)
			centroid, _ = rs.SurfaceAreaCentroid(b)
			b = rs.ScaleObject(b,centroid,[1.0,1.0,1.5])
#			rs.ObjectLayer(b,"s7")
			boolean_breps_level.append(b)
			rs.DeleteObject(srf_added)
			
		boolean_breps.append(boolean_breps_level)
	
	return boolean_breps


#TODO: MAKE BOOLEANS CORRESPONDING TO BUILDING FOOTPRINTS
def get_building_footprints(building_breps,planes):
	
#	rs.EnableRedraw()
	plane_sections = []
	slice_depth = []
	for b in building_breps:
		for i,p in enumerate(planes):
			s = get_section(rs.coercebrep(b),p)
			if s:
				plane_sections.append(s[0])
				slice_depth.append(i)
				break
	
	for section,d in zip(plane_sections,slice_depth):
		k = wrh.add_curve_to_layer(section,1)
#		rs.ObjectLayer(k,"Default")
#		print section
	m = zip(plane_sections,slice_depth)
	new_boolean_list = []
	for item in m:
		if item[1] > 0:
			transformation = Rhino.Geometry.Transform.Translation(rs.coerce3dvector([0,0,-THICKNESS]))
			new_crv = item[0].Transform(transformation)
			new_level = item[1] - 1
			new_boolean_list.append((new_crv,new_level))
		else:
			new_boolean_list.append(item)
	
	a,b = zip(*new_boolean_list)
#	for section,d in zip(a,b):
#		print section, d
		
#	rs.Redraw()
#	rs.EnableRedraw(False)
	return


#when method is robust, make boolean operation delete the inputs.
def cut_building_volumes(terrain_section_breps,bldg_section_breps):
	"""
	input: list of lists of extruded terrain breps and section breps.
	first level of list is section heights, second level is breps.
	output: the new terrain breps
	"""
	#boolean problem is caused by non-manifold error. need to scale the B_breps prior to booleaning.
	new_terrain_section_breps = []
	for i,brep_level in enumerate(terrain_section_breps):
		new_level_terrain_section_breps = []
		for A_brep in brep_level:
#			rs.ObjectLayer(A_brep,"s10")
			B_breps = rs.CopyObjects(bldg_section_breps[i])
#			[rs.ObjectLayer(B_brep,"s11") for B_brep in B_breps]
			boolean_result = rs.BooleanDifference([A_brep],B_breps,False)
			if boolean_result:
				c = [rs.CopyObject(x) for x in boolean_result]
				rs.DeleteObjects(boolean_result)
				new_level_terrain_section_breps.extend(c)
			else: 
				new_level_terrain_section_breps.append(rs.CopyObject(A_brep))
#			print new_level_terrain_section_breps
			rs.DeleteObjects(A_brep)
			rs.DeleteObjects(B_breps)
		rs.DeleteObjects(B_breps) #possibly not needed
		rs.DeleteObjects(boolean_result)
#		rs.ObjectLayer(new_level_terrain_section_breps,"s3")
		new_terrain_section_breps.append(new_level_terrain_section_breps)
#		print "done pass 1"
	return new_terrain_section_breps


def project_etching(etch_layer,surfaces):
	crvs = get_curves_on_layer(etch_layer)
	return rs.ProjectCurveToSurface(crvs,surfaces,[0,0,-1])


def rc_getinput():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	default_thickness = sticky["Thickness"] if sticky.has_key("Thickness") else 2
	default_borderThickness = sticky["borderThickness"] if sticky.has_key("borderThickness") else 10
	default_borderBool = sticky["borderBool"] if sticky.has_key("borderBool") else False
	
	opt_thickness = Rhino.Input.Custom.OptionDouble(default_thickness,0.2,1000)
	opt_borderthickness = Rhino.Input.Custom.OptionDouble(default_borderThickness,0.2,1000)
	opt_border = Rhino.Input.Custom.OptionToggle(default_borderBool,"No","Yes")
	
	go.SetCommandPrompt("Select terrain surface")
	go.AddOptionDouble("MaterialThickness", opt_thickness)
	go.AddOptionDouble("BorderThickness",opt_borderthickness)
	go.AddOptionToggle("Border", opt_border)
	
	go.GroupSelect = True
	go.SubObjectSelect = False
	go.AcceptEnterWhenDone(True)
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
#			print res
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
	
	#rs.EnableRedraw(False)
	global THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	global BORDER_THICKNESS
	BORDER_THICKNESS = opt_borderthickness.CurrentValue
	global BORDER_BOOL
	BORDER_BOOL = opt_border.CurrentValue
	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()
	
	#set guides
	global SHORT_GUIDE, LONG_GUIDE
	SHORT_GUIDE = rs.AddLine([0,0,0],[0,0,-THICKNESS])
	LONG_GUIDE = rs.AddLine([0,0,0],[0,0,-THICKNESS*4])
	
	#set layers
	global LCUT_IND
	LCUT_IND = wla.get_lcut_layers()
	
	#get topography object
	brep_obj = go.Object(0).Object()
	
	sticky["Thickness"] = THICKNESS
	sticky["borderThickness"] = BORDER_THICKNESS
	sticky["borderBool"] = BORDER_BOOL
	
	return brep_obj


def get_surface_outline(b_geo):
	"""get the surface outline and project to the surface's baseplane."""
	initial_boundary_guids = []
	initial_boundary_crv = []
	bb = rs.BoundingBox(b_geo)
	proj_plane = Rhino.Geometry.Plane.WorldXY
	proj_plane.Translate(rs.coerce3dvector([0,0,bb[0].Z]))
	for e in b_geo.Edges:
		initial_boundary_crv.append(Rhino.Geometry.Curve.ProjectToPlane(e.EdgeCurve,proj_plane))
	joined_boundary_crv = Rhino.Geometry.Curve.JoinCurves(initial_boundary_crv,D_TOL)
	if len(joined_boundary_crv) == 1:
		return joined_boundary_crv
	else:
		print "Script Error: more than one surface boundary outline. Please save this file and report error."
		return None


def cut_frame_from_brep(brep,frame):
	bdiff = rs.BooleanDifference(brep,frame,False)
	if bdiff:
		rs.DeleteObject(brep)
		brep = bdiff
	return brep


def rc_terraincut2(b_obj,building_layer,etching_layer):
	
	join_dist = 0
	if str(b_obj.ObjectType) != "Brep":
		b_geo = extrusion_to_brep(b_obj.Geometry)
	else:
		b_geo = b_obj.Geometry
	
	outline_crv = get_surface_outline(b_geo)
	#wrh.add_curves_to_layer(outline_crv,1)
	
	#extrude down the topography surface in order to take sections
	bool_merged = Rhino.Geometry.Brep.MergeCoplanarFaces(b_geo,D_TOL)
	extruded_srf_id = extrude_down_srf(wrh.docobj_to_guid(b_obj))
	extruded_srf = rs.coercebrep(extruded_srf_id)
	
	#get planes for sectioning.
	planes = get_section_planes(b_geo,THICKNESS)
	
	#get the section curves and the section srfs
#	rs.Redraw()
	section_srfs = []
	for i,plane in enumerate(planes):
#		print i
		#if first level, get brep outline
		if i > 0:
			plane_sections = get_section(extruded_srf,plane)
		else:
			plane_sections = outline_crv
		###DEBUG STARTS####
		current_level_srfs = []
		for crv in plane_sections:
			closed = crv.IsClosed
			if not closed:
				dist = rs.Distance(crv.PointAtStart, crv.PointAtEnd)
				res = crv.MakeClosed(dist*2)
				join_dist = dist if dist > join_dist else join_dist
				if res == False: return 0
			new_brep = Rhino.Geometry.Brep.CreatePlanarBreps(crv)[0]
			current_level_srfs.append(new_brep)
#			new_brep_added = doc.Objects.AddBrep(new_brep)
#			rs.ObjectLayer(new_brep_added,"s15")
		###DEBUG ENDS###
		section_srfs.append(current_level_srfs)
	rs.DeleteObject(extruded_srf_id)
	
	#get extrusions of section srfs
	extruded_section_breps = []
	boolean_section_breps = []
	frame_base_surface = None
	for i,brep_level in enumerate(section_srfs):
		extruded_breps = []
		for brep in brep_level:
			srf_added = wrh.add_brep_to_layer(brep,LCUT_IND[2])
			if i == 0: frame_base_surface = rs.CopyObject(srf_added)
			extruded_breps.append(rs.ExtrudeSurface(srf_added,SHORT_GUIDE))
			rs.DeleteObject(srf_added)
		extruded_section_breps.append(extruded_breps)
	
#	rs.Redraw()
	#make voids for existing buildings
	building_breps = get_breps_on_layer(building_layer)
	get_building_footprints(building_breps,planes)
	bldg_subtraction_breps = get_building_booleans(building_breps,planes)
	if bldg_subtraction_breps: extruded_section_breps = cut_building_volumes(extruded_section_breps,bldg_subtraction_breps)
	[rs.DeleteObjects(x) for x in bldg_subtraction_breps] #purge the building breps
	
	num_divisions = len(section_srfs)
	frame_brep = get_frame_brep(frame_base_surface,BORDER_THICKNESS,THICKNESS*num_divisions)
	rs.DeleteObject(frame_base_surface)
	#boolean out the features
	final_breps = []
	for i, brep_level in enumerate(extruded_section_breps):
		boolean_level_ind = i+2
		final_level_breps = []
		if boolean_level_ind < len(extruded_section_breps):
			for A_brep in brep_level:
				final_brep = None
				B_breps = []
				for B_srf in section_srfs[boolean_level_ind]:
					B_breps.append(rs.ExtrudeSurface(B_srf,LONG_GUIDE))
				#truncate the B_breps
				if BORDER_BOOL: B_breps = [cut_frame_from_brep(b,frame_brep) for b in B_breps]
				rs.ObjectLayer(B_breps,"s6")
				boolean_result = rs.BooleanDifference([A_brep],B_breps,False)
				rs.DeleteObjects(B_breps)
				if boolean_result:
					final_brep = boolean_result
				else:
					final_brep = rs.CopyObjects([A_brep])
				rs.DeleteObjects([A_brep])
				rs.ObjectLayer(final_brep,"s11")
				final_level_breps.extend(final_brep)
		else:
#			rs.ObjectLayer(A_brep,"s11")
			final_level_breps.extend(brep_level)
		final_breps.append(final_level_breps)
	
	#get the final surfaces by iterating through the final section breps and extracting the top faces.
	final_srfs = []
	for i,breplevel in enumerate(final_breps):
		final_srfs_level = []
		for brep in breplevel:
			xsrf = wge.get_extreme_srf(rs.coercebrep(brep),5)
			final_srfs_level.append(doc.Objects.Add(xsrf[0].DuplicateFace(False))) #must properly type the faces
#		rs.ObjectLayer(final_srfs_level,"s4")
		final_srfs.append(final_srfs_level)
	
	[rs.DeleteObjects(x) for x in final_breps] #DEBUG
	#project etching layers to final srfs	
	final_srfs.reverse()
	
	#get the boundary curves
	main_curves = []
	guide_curves = []
	etch_curves = []
	for i, srflevel in enumerate(final_srfs):
		main_curves_level = []
		guide_curves_level = []
		etch_curves_level = []
		
		for srf in srflevel:
#			rs.Redraw()
			sb = rs.DuplicateSurfaceBorder(srf)
			sb_outer = rs.DuplicateSurfaceBorder(srf,1)
			if sb:
				main_curves_level.extend(sb)
			if i < len(final_srfs)-1 and sb_outer:
					p = rs.ProjectCurveToSurface(sb_outer, final_srfs[i+1],[0,0,-1])
					if p: guide_curves_level.extend(p)
					rs.DeleteObject(sb_outer)
			if sb_outer: rs.DeleteObject(sb_outer) #refactor...
		etch_curves_level = project_etching("road",srflevel)
		
		etch_curves.append(etch_curves_level)
		main_curves.append(main_curves_level)
		guide_curves.append(guide_curves_level)
	
	flat_srf_list = [item for sublist in final_srfs for item in sublist]
	
	etch_curves.reverse()
	main_curves.reverse()
	guide_curves.reverse()
	
	bb=rs.BoundingBox(b_geo)
	layout_dist = rs.Distance(bb[0],bb[3]) + LASER_GAP
	preview_dist = rs.Distance(bb[0],bb[1]) + LASER_GAP
	movement_range = [(i+1)*layout_dist for i in xrange(len(main_curves))]
	for i,level_list in enumerate(main_curves):
		cp_main = rs.CurvePlane(level_list[0])
#		print movement_range[i]
		rs.MoveObjects(level_list,[0,movement_range[i],-cp_main.OriginZ])
		
		if etch_curves[i]:
			rs.MoveObjects(etch_curves[i],[0,movement_range[i],-cp_main.OriginZ])
		
		if i>0:
			cp_guide = rs.CurvePlane(guide_curves[i][0])
			rs.MoveObjects(guide_curves[i],[0,movement_range[i-1],-cp_guide.OriginZ])
	
	
#	rs.Redraw()
	main_curves = [item for sublist in main_curves for item in sublist]
	guide_curves = [item for sublist in guide_curves for item in sublist]
	etch_curves = [item for sublist in etch_curves for item in sublist]
	
	preview_geo = [item for sublist in final_srfs for item in sublist]
	rs.MoveObjects(preview_geo,[preview_dist,0,0])
	
	#close the boundary curves
	cb_crvs = []
	for c in guide_curves:
		if not rs.IsCurveClosed(c):
			if rs.IsCurveClosable(c,D_TOL):
				cb_curves.append(rs.CloseCurve(rs.CopyObject(c)))
		else:
			cb_crvs.append(rs.CopyObject(c))
	
	etch_curves = wge.trim_boundary(etch_curves,cb_crvs,D_TOL)
	rs.DeleteObjects(cb_crvs)
	rs.DeleteObject(frame_brep)
	
#	rs.DeleteObjects(extruded_section_breps)
	rs.ObjectLayer(main_curves,"XXX_LCUT_01-CUT")
	rs.ObjectLayer(guide_curves,"XXX_LCUT_03-LSCORE")
	rs.ObjectLayer(etch_curves,"XXX_LCUT_04-ENGRAVE")
	rs.ObjectLayer(preview_geo,"XXX_LCUT_00-GUIDES")
	if join_dist > 0:
		s = "Had to force-close gaps up to a distance of " + str(join_dist)
		Rhino.RhinoApp.WriteLine(s)
	return 1


if __name__ == "__main__":
	set_globals()
	surface_geometry = rc_getinput()
	if isinstance(surface_geometry, Rhino.Commands.Result):
		print "Invalid Input: no surface selected"
	else:
		if sticky.has_key("buildingLayer") and doc.Layers.Find(sticky["buildingLayer"],True) != -1:
			building_layer = rs.GetLayer(title="Select Building Layer",layer=sticky["buildingLayer"])
		else:
			building_layer = rs.GetLayer("Select Building Layer")
		
		if sticky.has_key("etchingLayer") and doc.Layers.Find(sticky["etchingLayer"],True) != -1:
			etch_layer = rs.GetLayer(title="Select Etching Layer",layer=sticky["etchingLayer"])
		else:
			etch_layer = rs.GetLayer("Select Etching Layer")
		
		sticky["buildingLayer"] = building_layer
		sticky["etchingLayer"] = etch_layer
		rs.EnableRedraw(False)
		result = rc_terraincut2(surface_geometry, building_layer, etch_layer)
		if result == 0:
			print "ERROR: topography slicing error. Try rebuilding the input surface with more control points and trying again."
		rs.EnableRedraw(True)
		rs.DeleteObject(SHORT_GUIDE)
		rs.DeleteObject(LONG_GUIDE)
		rs.Redraw()