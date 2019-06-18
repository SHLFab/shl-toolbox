"""
SHL Architects 13-06-2019
Sean Lamb (Developer)
- edits for clarity; fixed global assignment.
sel@shl.dk
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc
from scriptcontext import sticky

import itertools
import pprint
import shl_toolbox_lib.layers as wla
reload(wla)

def setGlobals():
	#mm.
	#default vals
	global T_IBOX,T_OBOX,J_LEN,LCUT_GAP,TICK_DIST
	global SELECT_GUIDS
	
	T_IBOX = 5.5 #inner box thickness (foamcore)
	T_OBOX = 2 #outer box thickness (card)
	J_LEN = 20 #joint length
	LCUT_GAP = 5 #gap between lasercut curves
	TICK_DIST = 10 #length of the guide ticks on the lid

	#tolerances
	global TOL_INSIDE,TOL_LID_ABSOLUTE
	TOL_INSIDE = 0 #
	
	#key locations
	global ORIGIN_IB,ORIGIN_OB
	ORIGIN_IB = [0,0,0]
	ORIGIN_OB = [0,100,0]
	
	#
	global LCUT_NAMES
	lcut_inds = wla.get_lcut_layers()
	LCUT_NAMES = wla.ind_to_name(lcut_inds)
	
	SELECT_GUIDS = []


#GENERAL UTILITIES
#flatten iterables
def flatten(lst):
	result = []
	for element in lst:
		if hasattr(element, '__iter__'):
			result.extend(flatten(element))
		else:
			result.append(element)
	return result

def chunks(lst, n):
	"""Yield successive n-sized chunks from l."""
	for i in xrange(0, len(lst), n):
		yield lst[i:i + n]

#RHINO UTILITIES
def add_layer(name,color):
	myLayer = name
	layerInd = doc.Layers.Find(myLayer,False)
	if layerInd == -1:
		layerInd= doc.Layers.Add(myLayer,color)
	return layerInd


def get_num_joins(dim,J_LEN):
	n_joins = int(dim/J_LEN)
	if n_joins % 2 == 0:
		n_joins += 1
	if n_joins < 3:
		n_joins = 3
	return n_joins

#MAIN FUNCTIONS
#probably easier way to do truncate...
def make_join(edge,n_joins,dx,dy,inner,truncate):

	pts = rs.DivideCurve(edge,n_joins)
	outer_pts, inner_pts, pairs_ordered = [],[],[]
	extrapt = None

	outer_pts = rs.AddPoints(pts)
	inner_pts = rs.CopyObjects(outer_pts,[dx,dy,0])
	if inner == True:
		extrapt = outer_pts[0]
		outer_pts = outer_pts[1:]
	else:
		extrapt = inner_pts[0]
		inner_pts = inner_pts[1:]

	pairs_o = zip(outer_pts[0::2],outer_pts[1::2])
	pairs_i = zip(inner_pts[0::2],inner_pts[1::2])

	if inner is True:
		pairs_ordered = flatten(zip(pairs_i,pairs_o))
		endpts = [inner_pts[-2],inner_pts[-1]]
	else:
		pairs_ordered = flatten(zip(pairs_o,pairs_i))
		endpts = [outer_pts[-2],outer_pts[-1]]

	pairs_ordered = pairs_ordered + endpts

	if truncate is True:
		v = rs.VectorUnitize(rs.VectorCreate(pairs_ordered[0],pairs_ordered[1]))
		v = rs.VectorScale(v,T_OBOX)
		rs.MoveObject(pairs_ordered[-1],v)
		rs.MoveObject(pairs_ordered[0],rs.VectorReverse(v))
	
	#get the point pairs corresponding to the outer pts of the rabbets
	#determine if vertical or horizontal.
#	test_pt_1 = 
#	print "printing pline info"
#	for p in pairs_o:
#		print rs.coerce3dpoint(p[0]), rs.coerce3dpoint(p[1])
	
	rabbet_info = get_rabbet_info(pairs_o)
	pl = rs.AddPolyline(pairs_ordered)
	rs.DeleteObject(extrapt)
	rs.DeleteObjects(outer_pts)
	rs.DeleteObjects(inner_pts)
	return pl,rabbet_info

def get_rabbet_info(outer_pt_ids):
	'''helper function for getting rabbet info from the outer pts of the joint polyline'''
	epsilon = 0.01
	pts = [[rs.coerce3dpoint(p[0]), rs.coerce3dpoint(p[1])] for p in outer_pt_ids]
	
	#determine if vertical or horizontal join
	testpt1 = pts[0][0]
	testpt2 = pts[0][1]
	print "testpt1", testpt1
	print "testpt2", testpt2
	vertical = True if abs(testpt1.X - testpt2.X) < epsilon else False
	print vertical
	
	startpts = []
	lengths = []
	for pair in pts:
		if vertical:
			sortedpts = sorted(pair,key=lambda point:point.Y)
			startpts.append([0,sortedpts[0].Y,0])
			lengths.append(sortedpts[1].Y-sortedpts[0].Y)
		else:
			sortedpts = sorted(pair,key=lambda point:point.X)
			startpts.append([sortedpts[0].X,0,0])
			lengths.append(sortedpts[1].X-sortedpts[0].X)
	print startpts
	print lengths
	return [startpts,lengths]
	

def add_tickmarks(rect,len,offset):

	c,_ = rs.CurveAreaCentroid(rect)
	mirror_v = [c,rs.PointAdd(c,[0,10,0])]
	mirror_h = [c,rs.PointAdd(c,[10,0,0])]

	pts = rs.CurvePoints(rect)
	if not pts:
		return "ERROR"
	pts = rs.SortPoints(pts)
	# print pts
	
	t_0 = rs.CopyObject(pts[0],[offset,offset,0])
	t_1 = rs.CopyObject(t_0,[len,0,0])
	t_2 = rs.CopyObject(t_0,[0,len,0])
	
	tick = rs.AddPolyline([t_1,t_0,t_2])
	rs.DeleteObjects([t_0,t_1,t_2])
	tick_2 = rs.MirrorObject(tick,mirror_v[0],mirror_v[1],True)
	ticks_3 = rs.MirrorObjects([tick,tick_2],mirror_h[0],mirror_h[1],True)
	rs.ObjectLayer([tick,tick_2]+ticks_3,LCUT_NAMES[3])
	tick_list = [tick,tick_2]+ticks_3
	return tick_list


#make slots and return information for placing them
def make_slots(W,L):
	g_W = W
	g_L = L
	
	grip = rs.AddRectangle([0,0,0],g_W,g_L)
	c,_ = rs.CurveAreaCentroid(grip)
	return [grip,c,g_W,g_L]

def make_slotjoints(rabbet_info,basept):
	epsilon = 0.01
	"in make_slotjoints"
	
	startpts = rabbet_info[0]
	lengths = rabbet_info[1]
	#determine if vertical or horizontal join
	testpt1 = startpts[0]
	testpt2 = startpts[1]
	print "testpt1", testpt1
	print "testpt2", testpt2
	vertical = True if abs(testpt1[0] - testpt2[0]) < epsilon else False
	
	print T_OBOX
	if vertical:
		slots = []
		for sp,length in zip(startpts,lengths):
			sp = [sum(x) for x in zip(sp, basept)]
			plane = rs.WorldXYPlane()
			plane = rs.MovePlane(plane,sp)
			slots.append(rs.AddRectangle(plane,T_OBOX,length))
	else:
		slots = []
		for sp,length in zip(startpts,lengths):
			sp = [sum(x) for x in zip(sp, basept)]
			plane = rs.WorldXYPlane()
			plane = rs.MovePlane(plane,sp)
			slots.append(rs.AddRectangle(plane,length,T_OBOX))
	return slots

#add "door slots" with a specified gap between them (to re-purpose this)
def add_slots(rect,grip,gap,y_offset=0):
	#by default will be centered in Y.
	g_crv = grip[0]
	g_c = grip[1]
	g_W = grip[2]
	center,_ = rs.CurveAreaCentroid(rect)

	pr_L = rs.PointAdd(center,[gap/2,0,0])
#	pr_R = rs.PointAdd(center,[-gap/2,0,0])

	pg_L = rs.PointAdd(g_c,[-g_W/2,y_offset,0])
#	pg_R = rs.PointAdd(g_c,[g_W/2,y_offset,0])

	lgrip = rs.CopyObject(g_crv,rs.VectorCreate(pr_L,pg_L))
#	rgrip = rs.CopyObject(g_crv,rs.VectorCreate(pr_R,pg_R))
	rs.DeleteObject(g_crv)

	return lgrip

def make_slide_holder(side_thickness,length,material_thickness,notch_depth):
	pts = [[0,0],
		[0,length],
		[side_thickness,length],
		[side_thickness,notch_depth],
		[side_thickness+material_thickness,notch_depth],
		[side_thickness+material_thickness,length],
		[side_thickness*2+material_thickness,length],
		[side_thickness*2+material_thickness,0],
		[0,0]
		] 
	pl = rs.AddPolyline(rs.coerce2dpointlist(pts))
	return pl

def make_lid(height,length,material_thickness,notch_depth):
	pts = [[0,0],
		[0,height],
		[length-notch_depth,height],
		[length-notch_depth,height-material_thickness],
		[length,height-material_thickness],
		[length,material_thickness],
		[length-notch_depth,material_thickness],
		[length-notch_depth,0],
		[0,0]
		] 
	pl = rs.AddPolyline(rs.coerce2dpointlist(pts))
	return pl


#add slots with a specified gap between them
def add_slide_holders(rect,grip,gap,y_offset=0):
	#by default will be centered in Y.
	g_crv = grip[0]
	g_c = grip[1]
	g_W = grip[2]
	center,_ = rs.CurveAreaCentroid(rect)

	pr_L = rs.PointAdd(center,[gap/2,0,0])
	pr_R = rs.PointAdd(center,[-gap/2,0,0])

	pg_L = rs.PointAdd(g_c,[-g_W/2,y_offset,0])
	pg_R = rs.PointAdd(g_c,[g_W/2,y_offset,0])

	lgrip = rs.CopyObject(g_crv,rs.VectorCreate(pr_L,pg_L))
	rgrip = rs.CopyObject(g_crv,rs.VectorCreate(pr_R,pg_R))
	rs.DeleteObject(g_crv)

	return [lgrip,rgrip]

def add_logo(pt_base,W,H):

	#determine size based on the boxdim. try to do 80mm.
	hatchdims = (40,14) #WxH
	if W > hatchdims[0]*2.2 and H > hatchdims[1]*2.2:
		scale_factor = 2
	else:
		proportion = 0.5
		scale_factor = W*(proportion)/40
		if scale_factor*14*1.05 > H:
			scale_factor = H*0.5/40

	str_file = r"O:\SHL\ModelshopCopenhagen\05_scripting\Resources\logo\shl_logo_40x13_hatch_centered"
	str_pt = str(pt_base.X) + "," + str(pt_base.Y) + ",0"
	str_scale = str(scale_factor)
	rs.Command("_-Insert _File=_Yes " + str_file + " _Block " + str_pt + " " + str_scale + " _Enter " , 0)
	logo = rs.LastCreatedObjects()
	rs.ObjectLayer(logo,LCUT_NAMES[4])
	SELECT_GUIDS.extend(logo)

def add_strap_notch(curve_id,dx=10):
	"""add notch in curve for strap. assumes vertical line input."""
	
	strap_width = 27
	descent_run = 1.5
	fillet_radius = 1.2
	notch_base = 20 + strap_width
	
	edge_length = rs.CurveLength(curve_id)
	endpts = rs.SortPoints(rs.CurvePoints(curve_id),True,2) #priority to Y for sorting
	start_pt = endpts[0]
	print [start_pt.X , edge_length/2 - descent_run - strap_width/2]
	
	p0 = start_pt
	p1 = rs.coerce2dpoint([start_pt.X , start_pt.Y + edge_length/2 - descent_run - strap_width/2])
	p2 = rs.coerce2dpoint([start_pt.X + dx, start_pt.Y + edge_length/2 - strap_width/2])
	p3 = rs.coerce2dpoint([start_pt.X + dx, start_pt.Y + edge_length/2])
	
	mirror_pts = [p3, rs.coerce2dpoint([p3.X + 10,p3.Y])]
	pts = [p0,p1,p2,p3]
	lines = []
	for i in xrange(len(pts)-1):
		lines.append(rs.AddLine(pts[i],pts[i+1]))
	
	fillet_info = []
	fillet_crvs = []
	for i in xrange(len(lines)-1):
		fillet_info.append(rs.CurveFilletPoints(lines[i],lines[i+1],fillet_radius))
		fillet_crvs.append(rs.AddFilletCurve(lines[i],lines[i+1],fillet_radius))

	trimmed_lines = [rs.AddLine(p0,fillet_info[0][0]),
						rs.AddLine(fillet_info[0][1],fillet_info[1][0]),
						rs.AddLine(fillet_info[1][1],p3)]
	rs.DeleteObjects(lines)
	
	crv = rs.JoinCurves(trimmed_lines + fillet_crvs,True)
	crv.append(rs.MirrorObject(crv,mirror_pts[0],mirror_pts[1],True))
	crv = rs.JoinCurves(crv,True)
	
	return crv

def get_outer_box(bb_dims, tol, T_IBOX, T_OBOX, TOL_INSIDE, ORIGIN_OB):
	"""input:
		bbdims float(w,l,h). l is longest dimension.
		tol float: percentage "give" to have
		T_IBOX: thickness in mm
		T_OBOX: thickness in mm
		TOL_INSIDE: additional absolute tolerance added to the inner dimension of the box
		ORIGIN_OB: origin point for placing the curves
		return: 
		br: list of four points representing the bounding rectangle of the output.
		"""
	
	#TEMP CONSTANTS FOR DEBUG TO BE GLOBAL LATER:
	
	print "T_OBOX", T_OBOX
	D_LID_NOTCH = 40
	D_HOLDER_OUTER = 6
	W = (1+tol) * bb_dims[0] + T_OBOX*2 + TOL_INSIDE*2
	L = (1+tol) * bb_dims[1] + T_OBOX*2 + TOL_INSIDE*2 + D_HOLDER_OUTER*3
	H = (1+tol) * bb_dims[2] + T_OBOX*2 + TOL_INSIDE*2
	
	dy = ORIGIN_OB[1] #amount to move everything up by
	
	n_joins_W = get_num_joins(W,J_LEN)
	n_joins_L = get_num_joins(L,J_LEN)
	n_joins_H = get_num_joins(H,J_LEN)
	
	#get bounding rectangles for each geometry. placeholder; this won't all be necessary
	bottom = rs.AddRectangle(ORIGIN_OB, L ,W)
	top = rs.AddRectangle([0,W+LCUT_GAP+dy,0], L, W)
	short_a = rs.AddRectangle([L+LCUT_GAP,dy,0], W, H)
	short_b = rs.AddRectangle([L+LCUT_GAP,H+LCUT_GAP+dy,0], W, H)
	long_a = rs.AddRectangle([L+W+LCUT_GAP*2,dy,0], L, H)
	long_b = rs.AddRectangle([L+W+LCUT_GAP*2,H+LCUT_GAP+dy,0], L, H)

	#add slots
	s_W = T_OBOX #slot width is material thickness
	s_L = H - T_OBOX*2 #- D_LID_NOTCH
	slot_data = make_slots(s_W,s_L)
	desired_slot_gap = L - D_HOLDER_OUTER*2 - T_OBOX*2
	
	#make 
	slot1 = add_slots(long_a,slot_data,desired_slot_gap)
	
	make_slide_holder(D_HOLDER_OUTER,W-T_OBOX*2,T_OBOX,40)
	make_lid(H-T_OBOX*2,W-T_OBOX,T_OBOX,40)
	#may add a conditional here to manage making tiny boxes... see orig code
	rs.ObjectLayer(slot1,LCUT_NAMES[1])
#	rs.ObjectLayer(slot2,LCUT_NAMES[1])
	
	#turn sides into finger joins
	sides_b = rs.ExplodeCurves(bottom)
	jb_0, _ = make_join(sides_b[0],n_joins_L,0,T_OBOX,True,False)
	jb_2, _ = make_join(sides_b[2],n_joins_L,0,-T_OBOX,True,False)
	jb_1 = rs.ExtendCurveLength(sides_b[1],0,2,-T_OBOX)
	jb_3 = rs.ExtendCurveLength(sides_b[3],0,2,-T_OBOX)

	sides_s = rs.ExplodeCurves(short_a)
	js_0, _ = make_join(sides_s[0],n_joins_W,0,T_OBOX,True,True)
	js_2, rinfo_js2 = make_join(sides_s[2],n_joins_W,0,-T_OBOX,True,True)
	js_1, rinfo_js1 = make_join(sides_s[1],n_joins_H,-T_OBOX,0,True,True)
	js_3, _ = make_join(sides_s[3],n_joins_H,T_OBOX,0,True,True)

	sides_l = rs.ExplodeCurves(long_a)
	jl_0, _ = make_join(sides_l[0],n_joins_L,0,T_OBOX,False,True)
	j1_0 = rs.ExtendCurveLength(jl_0,0,2,T_OBOX)
	jl_2, _ = make_join(sides_l[2],n_joins_L,0,-T_OBOX,False,True)
	j1_2 = rs.ExtendCurveLength(jl_2,0,2,T_OBOX)
	jl_1 = add_strap_notch(sides_l[1],-T_OBOX)
	jl_3 = add_strap_notch(sides_l[3],T_OBOX)
	
	sb,ss,sl = rs.JoinCurves([jb_0,jb_1,jb_2,jb_3],True), rs.JoinCurves([js_0,js_1,js_2,js_3],True), rs.JoinCurves([jl_0,jl_1,jl_2,jl_3],True)
	
	final_crvs = sb+ss+sl+[top]
	rs.ObjectLayer(sb+ss+sl+[top],LCUT_NAMES[1])
	final_crvs.extend(rs.CopyObjects(ss,[0,H+LCUT_GAP,0]))
	final_crvs.extend(rs.CopyObjects(sl,[0,H+LCUT_GAP,0]))
	
	#get rect slot for short end of box
	short_end_offset = D_HOLDER_OUTER + T_OBOX
	
	slotjoint_location_long_a = [L+W+LCUT_GAP*2 + short_end_offset-T_OBOX,dy,0]
	slotjoint_location_long_b = [L+W+LCUT_GAP*2 + short_end_offset-T_OBOX,H+LCUT_GAP+dy,0]
	slotjoint_location_base = [-(L+LCUT_GAP),0,0]
	
	slots_short1 = make_slotjoints(rinfo_js1,slotjoint_location_long_a)
	slots_short2 = make_slotjoints(rinfo_js1,slotjoint_location_long_b)
	
	slots_long = make_slotjoints(rinfo_js2,slotjoint_location_base)
	slots_long = rs.MirrorObjects(slots_long,[0,0,0],[1,1,0])
	rs.MoveObjects(slots_long,[short_end_offset,0,0])
#	centerpt, _ = rs.CurveAreaCentroid(short_a)
#	add_logo(centerpt,W,H)
#
	all_geo = [bottom,top,short_a,short_b,long_a,long_b]
	br = rs.BoundingBox(all_geo)[:4]
	
	rs.DeleteObjects(sides_b+sides_s+sides_l)
	rs.DeleteObjects([bottom,short_a,short_b,long_a,long_b])
	
	SELECT_GUIDS.extend(final_crvs)
	SELECT_GUIDS.extend([slot1])
#	SELECT_GUIDS.extend(tickmarks)
#	return br

def rc_shl_box():
	#get stickies
	default_inner_thickness = sticky["defaultInThickness"] if sticky.has_key("defaultInThickness") else 5.5
	default_outer_thickness = sticky["defaultOutThickness"] if sticky.has_key("defaultOutThickness") else 2
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
	
	opt_inner = Rhino.Input.Custom.OptionDouble(default_inner_thickness,0.2,1000)
	opt_outer = Rhino.Input.Custom.OptionDouble(default_outer_thickness,0.2,1000)
	
	go.SetCommandPrompt("Select breps to be boxed or press Enter for manual dimensioning (Suggested: Inner 5.5, Outer 2)")
	go.AddOptionDouble("InnerThickness", opt_inner)
	go.AddOptionDouble("OuterThickness", opt_outer)
	
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

	MANUAL = False
	while True:
		res = go.GetMultiple(1,0)

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			# print res
			go.EnablePreSelect(False, True)
			continue
		elif res == Rhino.Input.GetResult.Nothing:
			MANUAL = True
		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel
			
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		
		break
	
	#set globals according to input
	global T_OBOX
	T_IBOX = opt_inner.CurrentValue
	T_OBOX = opt_outer.CurrentValue
	
#	rs.EnableRedraw(False)
	
	if MANUAL == False:
		#Get dimensions from geometry and object lists
		brep_obj_list = [] #not used but left in for reference
		brep_ids_list = []
		for i in xrange(go.ObjectCount):
			b_obj = go.Object(i).Object()
			brep_obj_list.append(b_obj)
			brep_ids_list.append(b_obj.Id)
		
		bb = rs.BoundingBox(brep_ids_list)
		
		bb_x = rs.Distance(bb[0],bb[1])
		bb_y = rs.Distance(bb[0],bb[3])
		bb_h = rs.Distance(bb[0],bb[4])
		
	else:
		#get stickies
		default_x = sticky["manualXDim"] if sticky.has_key("manualXDim") else 200
		default_y = sticky["manualYDim"] if sticky.has_key("manualYDim") else 250
		default_z = sticky["manualZDim"] if sticky.has_key("manualZDim") else 150
		
		#Get dimensions manually
		result, bb_x = Rhino.Input.RhinoGet.GetNumber("X dimension?",True,default_x)
		if result != Rhino.Commands.Result.Success: return result
		
		result, bb_y = Rhino.Input.RhinoGet.GetNumber("Y dimension?",True,default_y)
		if result != Rhino.Commands.Result.Success: return result
		
		result, bb_h = Rhino.Input.RhinoGet.GetNumber("Z dimension?",True,default_z)
		if result != Rhino.Commands.Result.Success: return result
	
	bb_w = min(bb_x,bb_y)
	bb_l = max(bb_x,bb_y)
	
	#br = get_inner_box((bb_w,bb_l,bb_h),0,T_IBOX,TOL_INSIDE)
	ORIGIN_OB = (0,0,0)
	get_outer_box((bb_w,bb_l,bb_h),0,T_IBOX,T_OBOX,TOL_INSIDE,ORIGIN_OB)
	
	#set stickies
	sticky["defaultInThickness"] = T_IBOX
	sticky["defaultOutThickness"] = T_OBOX
	sticky["manualXDim"] = bb_x
	sticky["manualYDim"] = bb_y
	sticky["manualZDim"] = bb_h
	
	rs.UnselectAllObjects()
	rs.SelectObjects(SELECT_GUIDS)
	rs.Redraw()
	rs.EnableRedraw(True)



if __name__ == "__main__":
	setGlobals()
	rc_shl_box()
#
#	c1 = rs.GetCurveObject("boundary1")
#	c2 = rs.GetCurveObject("boundary2")
#	c3 = rs.GetCurveObject("crv to extend")
#	c1 = c1[0]
#	c2 = c2[0]
#	c3 = c3[0]
#	rs.ExtendCurve(c3,0,2,[c1,c2])
#	line = rs.GetLine(1)
#	line = rs.AddLine(line[0],line[1])
#	add_strap_notch(line)