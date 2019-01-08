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


"""
KNOWN ISSUES TO FIX:
1. Use of a small epsilon to get the first section through the terrain.
instead, use a projection of the surface to get the outline
2. Use of a downward extrusion for the building sections.
Two possible consequences:
	- This might be fine for all sections except for the bottom one, which should be a projection of the footprint
	- This might not be fine at all... verify with different geometry.
3. (FORESEEN): overkill for "next terrain outline"...
"""

def set_globals():
	global D_TOL, A_TOL
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees
	
	global LASER_GAP
	LASER_GAP = 4


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


def get_frame_brep(outline_srf,border_thickness,thickness):
	outline_crv = rs.JoinCurves(rs.DuplicateEdgeCurves(outline_srf))
	pt, _ = rs.CurveAreaCentroid(outline_crv)
	inner_crv = rs.OffsetCurve(outline_crv,pt,border_thickness,[0,0,1])
	rs.MoveObjects([outline_crv,inner_crv],[0,0,thickness*2])
	
	path = rs.AddLine([0,0,0],[0,0,-thickness*4])
	inner_brep = rs.ExtrudeCurve(inner_crv,path)
	outer_brep = rs.ExtrudeCurve(outline_crv,path)
	rs.CapPlanarHoles(inner_brep)
	rs.CapPlanarHoles(outer_brep)
	
	frame_brep = rs.BooleanDifference([outer_brep],[inner_brep])
	rs.DeleteObjects([outline_crv,inner_crv])
	return frame_brep


def get_lowest_curve_info(brep, h_tol):
	#right now hardcoded to not deal with multiple breps at the final step. to revise if needed.
	bdims = wge.get_bounding_dims(brep)
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
	for i,plane in enumerate(planes):
		bldg_intersection_breps_level = []
		boolean_breps_level = []
		for b in building_breps:
			plane_sections = get_section(rs.coercebrep(b),plane)
			if not plane_sections: continue
			
			for s in plane_sections:
				pb = Rhino.Geometry.Brep.CreatePlanarBreps(plane_sections) #creates a list of breps
				pb = pb[0]
				bldg_intersection_breps_level.append(pb)
			for s in bldg_intersection_breps_level:
				srf_added = wrh.add_brep_to_layer(s,LCUT_IND[4])
				k = SHORT_GUIDE
				b = rs.ExtrudeSurface(srf_added,SHORT_GUIDE)
				rs.ObjectLayer(b,"s7")
				rs.DeleteObject(srf_added)
				boolean_breps_level.append(b)
				
		bldg_intersection_breps.append(bldg_intersection_breps_level) #don't even need this...
		bldg_intersection_boolean_breps.append(boolean_breps_level)
	#debug preview: change layer of the boolean breps.
	return bldg_intersection_boolean_breps


def cut_building_volumes(terrain_section_breps,bldg_section_breps):
	"""
	input: list of lists of extruded terrain breps and section breps.
	first level of list is section heights, second level is breps.
	output: the new terrain breps
	"""
	new_terrain_section_breps = []
	for i,brep_level in enumerate(terrain_section_breps):
		new_level_terrain_section_breps = []
		for host_brep in brep_level:
			sub_breps = bldg_section_breps[i]
			boolean_result = rs.BooleanDifference([host_brep],sub_breps,False)
			if boolean_result:
				c = [rs.CopyObject(x) for x in boolean_result]
				new_level_terrain_section_breps.extend(c)
			else: new_level_terrain_section_breps.append(host_brep)
		rs.DeleteObjects(sub_breps)
		rs.DeleteObjects(boolean_result)
		rs.ObjectLayer(new_level_terrain_section_breps,"s3")
		new_terrain_section_breps.append(new_level_terrain_section_breps)
	
	return new_terrain_section_breps


def project_etching(etch_layer,surfaces):
	crvs = get_curves_on_layer(etch_layer)
	return rs.ProjectCurveToSurface(crvs,surfaces,[0,0,-1])


def rc_getinput():
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	opt_thickness = Rhino.Input.Custom.OptionDouble(2,0.2,1000)
	opt_borderthickness = Rhino.Input.Custom.OptionDouble(2,0.2,1000)
	opt_sections = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_inplace = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	
	go.SetCommandPrompt("Select terrain surface")
	go.AddOptionDouble("MaterialThickness", opt_thickness)
	go.AddOptionDouble("BorderThickness",opt_borderthickness)
	
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
	
	#rs.EnableRedraw(False)
	
	global THICKNESS
	THICKNESS = opt_thickness.CurrentValue
	global BORDER_THICKNESS
	BORDER_THICKNESS = opt_borderthickness.CurrentValue
	global LCUT_INDICES
	LCUT_INDICES = wla.get_lcut_layers()
	bool_inplace = opt_inplace.CurrentValue
	
	
	#set guides
	global SHORT_GUIDE, LONG_GUIDE
	SHORT_GUIDE = rs.AddLine([0,0,0],[0,0,-THICKNESS])
	LONG_GUIDE = rs.AddLine([0,0,0],[0,0,-THICKNESS*4])
	
	#set layers
	global LCUT_IND
	LCUT_IND = wla.get_lcut_layers()
	
	#get topography object
	brep_obj = go.Object(0).Object()
	
	return brep_obj


def rc_terraincut(b_obj):
	
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
		#debug
		for brep in current_level_srfs:
			srf_added = wrh.add_brep_to_layer(brep,LCUT_IND[1])
		section_srfs.append(current_level_srfs)
	rs.DeleteObject(extruded_srf_id)
	
	extruded_section_breps = []
	boolean_section_breps = []
	frame_base_surface = None
	
	#get extrusions of section srfs
	for i,brep_level in enumerate(section_srfs):
		extruded_breps = []
		for brep in brep_level:
			srf_added = wrh.add_brep_to_layer(brep,LCUT_IND[1])
			if i == 0: frame_base_surface = rs.CopyObject(srf_added)
			extruded_breps.append(rs.ExtrudeSurface(srf_added,SHORT_GUIDE))
			rs.DeleteObject(srf_added)
		extruded_section_breps.append(extruded_breps)
	
	#make voids for existing buildings
	building_breps = get_breps_on_layer("BUILDINGS") #TODO: replace with user-selections
	building_sections = []
	bldg_subtraction_breps = get_building_booleans(building_breps,planes)	
	#TODO: build the bottom building brep from a projection or something... current method grabs whatever's at the requisite depth and extrudes...
	#see note 2 at top of script... maybe this is okay.
	
	#do booleaning of building breps.
	extruded_section_breps = cut_building_volumes(extruded_section_breps,bldg_subtraction_breps)
	
#	make the frame brep
	num_divisions = len(section_srfs)
	frame_brep = get_frame_brep(frame_base_surface,BORDER_THICKNESS,THICKNESS*num_divisions)
	section_final_breps = []
	
	
	#brep construction
	#brep construction
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
					boolbreps.append(rs.ExtrudeSurface(child_brep,LONG_GUIDE))
				rs.ObjectLayer(boolbreps,"s6")
				
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
					type = rs.ObjectType(boolean_result)
					if len(frame_intersection) !=0:
						frame_union_items = [boolean_result]
						frame_union_items.extend(frame_intersection)
						framed_brep = rs.BooleanUnion(frame_union_items,True) #Watch this
						framed_brep = framed_brep[0]
					else:
						framed_brep = boolean_result
					
					#merge faces.
					rc_b = rs.coercebrep(framed_brep)
					rc_b.MergeCoplanarFaces(D_TOL) # This fails occasionally. why? (seems to have something to do with frame size... overlap?
					merged_brep = doc.Objects.Add(rc_b)
					rs.DeleteObject(framed_brep)
					rs.ObjectLayer(merged_brep,"s5")
					
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
		rs.ObjectLayer(final_srfs_level,"s4")
		final_srfs.append(final_srfs_level)
	rs.DeleteObject(frame_brep)
	
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
			sb = rs.DuplicateSurfaceBorder(srf)
			sb_outer = rs.DuplicateSurfaceBorder(srf,1)
			if sb:
				main_curves_level.extend(sb)
			if i< len(final_srfs)-1 and sb_outer:
					p = rs.ProjectCurveToSurface(sb_outer, final_srfs[i+1],[0,0,-1])
					if p: guide_curves_level.extend(p)
		etch_curves_level = project_etching("road",srflevel)
		
		etch_curves.append(etch_curves_level)
		main_curves.append(main_curves_level)
		guide_curves.append(guide_curves_level)
	
	flat_srf_list = [item for sublist in final_srfs for item in sublist]
	etches = project_etching("road",flat_srf_list)
	
	etch_curves.reverse()
	main_curves.reverse()
	guide_curves.reverse()
	
	bb=rs.BoundingBox(main_curves[0])
	
	layout_dist = rs.Distance(bb[0],bb[3]) + LASER_GAP
	preview_dist = rs.Distance(bb[0],bb[1]) + LASER_GAP
	movement_range = wut.frange(layout_dist,(len(main_curves))*layout_dist,layout_dist)
	
	for i,level_list in enumerate(main_curves):
		cp_main = rs.CurvePlane(level_list[0])
		rs.MoveObjects(level_list,[0,movement_range[i],-cp_main.OriginZ])
		
		if etch_curves[i]:
			rs.MoveObjects(etch_curves[i],[0,movement_range[i],-cp_main.OriginZ])
		
		if i>0:
			cp_guide = rs.CurvePlane(guide_curves[i][0])
			rs.MoveObjects(guide_curves[i],[0,movement_range[i-1],-cp_guide.OriginZ])
		
	
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
	
	rs.ObjectLayer(main_curves,"XXX_LCUT_01-CUT")
	rs.ObjectLayer(guide_curves,"XXX_LCUT_03-LSCORE")
	rs.ObjectLayer(etch_curves,"XXX_LCUT_04-ENGRAVE")
	rs.ObjectLayer(preview_geo,"XXX_LCUT_00-GUIDES")
	return 0
	
	
if __name__ == "__main__":
	set_globals()
	surface_geometry = rc_getinput()
	rc_terraincut(surface_geometry)