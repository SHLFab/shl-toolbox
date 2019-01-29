"""
SHL Architects 20-12-2018
v1.2 Sean Lamb (Developer)
- edits for clarity; fixed global assignment.
sel@shl.dk
"""

import rhinoscriptsyntax as rs
import Rhino
import System.Drawing as sd
from scriptcontext import doc

import itertools

import shl_toolbox_lib_dev.layers as wla
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
	TOL_INSIDE = 2.5 #
	TOL_LID_ABSOLUTE = 0.7 #mm to shave off each dimension in the lid
	
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


	pl = rs.AddPolyline(pairs_ordered)
	rs.DeleteObject(extrapt)
	rs.DeleteObjects(outer_pts)
	rs.DeleteObjects(inner_pts)
	return pl


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


#make grips and return information for placing them
def make_grips(W,L):
	g_W = 6	#20/L or 14/L
	g_L = min(W/3,35)	#3dis

	grip = rs.AddRectangle([0,0,0],g_W,g_L)
	c,_ = rs.CurveAreaCentroid(grip)
	return [grip,c,g_W,g_L]


#add grips with a specified gap between them
def add_grips(rect,grip,gap):
	g_crv = grip[0]
	g_c = grip[1]
	g_W = grip[2]
	center,_ = rs.CurveAreaCentroid(rect)

	pr_L = rs.PointAdd(center,[gap/2,0,0])
	pr_R = rs.PointAdd(center,[-gap/2,0,0])

	pg_L = rs.PointAdd(g_c,[-g_W/2,0,0])
	pg_R = rs.PointAdd(g_c,[g_W/2,0,0])

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


#deprecated
def add_logo_offcenter(pt_base,W,H):
	"""deprecated"""
	proportion = 0.25
	scale_factor = W*(proportion)/40
	if scale_factor*14*1.05 > H:
		scale_factor = H*0.5/40

	margin = max(W,H)*0.05+T_OBOX

	str_file = r"O:\SHL\ModelshopCopenhagen\05_scripting\Resources\logo\shl_logo_40x13_hatch_block_centered"
	str_pt = str(pt_base.X+margin) + "," + str(pt_base.Y+margin) + ",0"
	str_scale = str(scale_factor)
	#rs.Command("_-Insert _File=_Yes " + str_file + " _Block " + str_pt + " _Enter _Enter", 0)
	rs.Command("_-Insert _File=_Yes " + str_file + " _Block " + str_pt + " " + str_scale + " _Enter " , 0)
	logo = rs.LastCreatedObjects()
	rs.ObjectLayer(logo,LCUT_NAMES[4])


#box functions
def get_inner_box(bb_dims, tol, T_IBOX, TOL_INSIDE):
	"""input:
	bbdims float(w,l,h). l is longest dimension.
	tol float: percentage "give" to have
	T_IBOX: thickness in mm
	T_OBOX: thickness in mm
	TOL_INSIDE: additional absolute tolerance added to the inner dimension of the box
	return: 
	br: list of four points representing the bounding rectangle of the output.
	"""
	W = (1+tol) * bb_dims[0] + T_IBOX*2 + TOL_INSIDE*2
	L = (1+tol) * bb_dims[1] + T_IBOX*2 + TOL_INSIDE*2
	H = (1+tol) * bb_dims[2] + T_IBOX*2 + TOL_INSIDE*1 - 0.1*T_IBOX
	
	bottom = rs.AddRectangle(ORIGIN_IB,L-2,W-2)
	
	# top: overall dim - material + rabet - lid tolerance
	# print L - T_IBOX*2 - TOL_LID_ABSOLUTE*2
	# print L - T_IBOX*2 - TOL_LID_ABSOLUTE*2
	top = rs.AddRectangle( [0,W+LCUT_GAP,0], L - T_IBOX*2 - TOL_LID_ABSOLUTE*2, W - T_IBOX*2 - TOL_LID_ABSOLUTE*2)
	
	short_a = rs.AddRectangle([L+LCUT_GAP, 0, 0], W - 2*T_IBOX, H - T_IBOX)
	short_b = rs.AddRectangle([L+LCUT_GAP, H+LCUT_GAP - T_IBOX ,0], W - 2*T_IBOX, H - T_IBOX)
	long_a = rs.AddRectangle([L+W+LCUT_GAP*2 - 2*T_IBOX, 0, 0], L, H - T_IBOX)
	long_b = rs.AddRectangle([L+W+LCUT_GAP*2 - 2*T_IBOX, H + LCUT_GAP - T_IBOX,0], L, H - T_IBOX)
	
	grip_data = make_grips(bb_dims[0],bb_dims[1])
	desired_grip_gap = 130
	if bb_dims[1] > desired_grip_gap*1.4:
		grips = add_grips(top,grip_data,desired_grip_gap)
	else:
		grips = add_grips(top,grip_data,bb_dims[1]/20)
	rs.ObjectLayer(grips,LCUT_NAMES[1])
	
	all_geo = [bottom,top,short_a,short_b,long_a,long_b]
	rs.ObjectLayer(all_geo,LCUT_NAMES[1])
	
	br = rs.BoundingBox(all_geo)[:4]
	
	SELECT_GUIDS.extend(all_geo)
	SELECT_GUIDS.extend(grips)
	return br


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

	W = (1+tol) * bb_dims[0] + T_IBOX*2 + T_OBOX*2 + TOL_INSIDE*2
	L = (1+tol) * bb_dims[1] + T_IBOX*2 + T_OBOX*2 + TOL_INSIDE*2
	H = (1+tol) * bb_dims[2] + T_IBOX*2 + T_OBOX*1 + TOL_INSIDE*1

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

	tickmarks = add_tickmarks(top,TICK_DIST,T_OBOX+T_IBOX+TOL_LID_ABSOLUTE)
	grip_data = make_grips(bb_dims[0],bb_dims[1])

	desired_grip_gap = 130
	if bb_dims[1] > desired_grip_gap*1.4:
		grips = add_grips(top,grip_data,desired_grip_gap)
	else:
		grips = add_grips(top,grip_data,bb_dims[1]/20)

	rs.ObjectLayer(grips,LCUT_NAMES[1])

	#turn sides into finger joins
	sides_b = rs.ExplodeCurves(bottom)
	jb_0 = make_join(sides_b[0],n_joins_L,0,T_OBOX,True,True)
	jb_2 = make_join(sides_b[2],n_joins_L,0,-T_OBOX,True,True)
	jb_1 = make_join(sides_b[1],n_joins_W,-T_OBOX,0,True,True)
	jb_3 = make_join(sides_b[3],n_joins_W,T_OBOX,0,True,True)

	sides_s = rs.ExplodeCurves(short_a)
	js_0 = make_join(sides_s[0],n_joins_W,0,T_OBOX,False,False)
	js_2 = rs.CopyObject(sides_s[2])
	js_1 = make_join(sides_s[1],n_joins_H,-T_OBOX,0,False,False)
	js_3 = make_join(sides_s[3],n_joins_H,T_OBOX,0,False,False)

	sides_l = rs.ExplodeCurves(long_a)
	jl_0 = make_join(sides_l[0],n_joins_L,0,T_OBOX,False,True)
	jl_2 = rs.ExtendCurveLength(rs.CopyObject(sides_l[2]),0,2,-T_OBOX)
	jl_1 = make_join(sides_l[1],n_joins_H,-T_OBOX,0,True,False)
	jl_3 = make_join(sides_l[3],n_joins_H,T_OBOX,0,True,False)

	sb,ss,sl = rs.JoinCurves([jb_0,jb_1,jb_2,jb_3],True), rs.JoinCurves([js_0,js_1,js_2,js_3],True), rs.JoinCurves([jl_0,jl_1,jl_2,jl_3],True)
	
	final_crvs = sb+ss+sl+[top]
	rs.ObjectLayer(sb+ss+sl+[top],LCUT_NAMES[1])
	final_crvs.extend(rs.CopyObjects(ss,[0,H+LCUT_GAP,0]))
	final_crvs.extend(rs.CopyObjects(sl,[0,H+LCUT_GAP,0]))

	centerpt, _ = rs.CurveAreaCentroid(short_a)
	add_logo(centerpt,W,H)

	all_geo = [bottom,top,short_a,short_b,long_a,long_b]
	br = rs.BoundingBox(all_geo)[:4]
	
	rs.DeleteObjects(sides_b+sides_s+sides_l)
	rs.DeleteObjects([bottom,short_a,short_b,long_a,long_b])
	
	SELECT_GUIDS.extend(final_crvs)
	SELECT_GUIDS.extend(grips)
	SELECT_GUIDS.extend(tickmarks)
	return br


def rc_shl_box():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep

	opt_inner = Rhino.Input.Custom.OptionDouble(5.5,0.2,1000)
	opt_outer = Rhino.Input.Custom.OptionDouble(2,0.2,1000)

	go.SetCommandPrompt("Select breps to be boxed or press Enter for manual dimensioning")
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
	T_IBOX = opt_inner.CurrentValue
	T_OBOX = opt_outer.CurrentValue
	
	rs.EnableRedraw(False)
	
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
		#Get dimensions manually
		result, dim = Rhino.Input.RhinoGet.GetNumber("X dimension?",True,200)
		if result <> Rhino.Commands.Result.Success:
			return result
		else:
			bb_x = dim
		
		result, dim = Rhino.Input.RhinoGet.GetNumber("Y dimension?",True,250)
		if result <> Rhino.Commands.Result.Success:
			return result
		else:
			bb_y = dim
		
		result, dim = Rhino.Input.RhinoGet.GetNumber("Z dimension?",True,200)
		if result <> Rhino.Commands.Result.Success:
			return result
		else:
			bb_h = dim
	
	bb_w = min(bb_x,bb_y)
	bb_l = max(bb_x,bb_y)
	
	br = get_inner_box((bb_w,bb_l,bb_h),0,T_IBOX,TOL_INSIDE)
	ORIGIN_OB = (0,rs.Distance(br[0],br[3]) + LCUT_GAP,0)
	get_outer_box((bb_w,bb_l,bb_h),0,T_IBOX,T_OBOX,TOL_INSIDE,ORIGIN_OB)
	
	rs.UnselectAllObjects()
	rs.SelectObjects(SELECT_GUIDS)
	rs.Redraw()
	rs.EnableRedraw(True)


if __name__ == "__main__":
	setGlobals()
	rc_shl_box()