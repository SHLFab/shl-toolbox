"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
-repo test
"""

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
from scriptcontext import doc, sticky
import System
import System.Drawing as sd

import json

# __commandname__ = "shlBridge"

#should be able to un-global cut tol and cut_length
def setGlobals():
	#mm assumed
	global D_TOL, A_TOL #document and angle tolerance
	global CUT_TOL, CUT_LENGTH #boundary around each cut and cut length
	global ATTRIBUTE_KEY #stores the bridge params as user text associated with the curve.

	ATTRIBUTE_KEY = "lc_bridge_param"
	CUT_TOL = 10
	CUT_LENGTH = 5
	D_TOL = doc.ActiveDoc.ModelAbsoluteTolerance
	A_TOL = doc.ActiveDoc.ModelAngleToleranceDegrees


#utility methods
def arr_to_list(array):
	lst = [x for x in array]
	return lst


def add_layer(name,color):
	myLayer = name
	this_doc = Rhino.RhinoDoc.ActiveDoc
	layerInd = this_doc.Layers.Find(myLayer,False)
	if layerInd == -1:
		layerInd= this_doc.Layers.Add(myLayer,color)
	return layerInd


def get_centered_subdomains(bounds,params,size):
	"""
	turn points into centered subdomains, handle wrapping
	output: list of subdomains associated with each point. structure [point][domain][start/end]
	"""
	subdomains = [ [[x-size/2,x+size/2]] for x in params]
	new_subdomains = []
	for sdom in subdomains:
		if sdom[0][0] < bounds[0]:
			new_startpt = (sdom[0][0]-bounds[0]) + bounds[1]
			ssdom1 = [ new_startpt,bounds[1] ]
			ssdom2 = [ bounds[0],sdom[0][1] ]
			new_subdomains.append([ssdom1,ssdom2])
		elif sdom[0][1] > bounds[1]:
			new_endpt = sdom[0][1] - bounds[1] + bounds[0]
			ssdom1 = [ sdom[0][0],bounds[1] ]
			ssdom2 = [ bounds[0],new_endpt ]
			new_subdomains.append([ssdom1,ssdom2])
		else:
			new_subdomains.append(sdom)
	return new_subdomains


def get_complement_domains(centered_sdoms):
	"""get complement domains from a set of centered subdomains. note structure of subdomains: [point][domain][start/end]"""
	last_domain = [centered_sdoms[-1][-1][-1],centered_sdoms[0][0][0]]
	new_doms = [last_domain]

	for i in xrange(len(centered_sdoms[:-1])):
		new_doms.append([ centered_sdoms[i][-1][-1], centered_sdoms[i+1][0][0] ])

	return new_doms


#geometry methods
def points_from_params(curve,params,layer_index):

	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index

	if params == None:
		return None

	points = [curve.PointAt(param) for param in params]
	for point in points:
		doc.Objects.AddPoint(point, attribs)
	return points


def add_circle_to_layer(center,radius,layer_index):
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	c = Rhino.Geometry.Circle(center, radius)
	circ_added = sc.doc.Objects.AddCircle(c, attribs)
	if circ_added !=System.Guid.Empty:
		return circ_added
	return Rhino.Commands.Result.Failure


def add_curve_to_layer(curve,layer_index):
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	crv_added = doc.Objects.AddCurve(curve,attribs)
	if crv_added != System.Guid.Empty:
		return crv_added
	return Rhino.Commands.Result.Failure


def move_points_from_seam(crv_geo,crv_params):
	"""move division points along a seam to avoid starting at param = 0"""
	if len(crv_params) > 1:
		increment = (crv_params[1] - crv_params[0]) / 2
	elif len(crv_params) == 1:
		increment = crv_geo.Domain.Length/2

	moved_points = [x+increment for x in crv_params]

	for mp in moved_points:
		if (crv_geo.Domain.T1 - mp) < 0:
			mp = mp - crv_geo.Domain.T1

	return moved_points


#domain methods
def build_consecutive_domains(partition_params,wrap=True):
	"""Build consecutive domains from parameter values where the partitions are to occur.
	Parameters:
		partition_params (float[]): locations of partitions
		bounds (float[]): pair of bounds for start/end of domain (necessary??)
		wrap (bool=True): wrap the last partition to the first
	Returns:
		domains (float[][]): list of domains. domains are pairs of values."""

	num_domains = len(partition_params) if wrap==True else len(partition_params)-1

	consec_domains = []
	for i in xrange(num_domains):
		start = i
		end = (i+1)%len(partition_params)
		consec_domains.append([partition_params[start],partition_params[end]])

	return consec_domains


def get_domain_containment(param,tolerance,domains):
	"""see if a parameter is in a domain, and if so, is there "nowhere for the parameter to go,"
	i.e. is the domain too small to hold the parameter. return domain index if these are true.
	Parameters:
		param (float): param being evaluated
		tolerance (float): distance this param needs to be from domain partitions.
		domains (float[][]): list of domains. domains are pairs of values.
	Returns:
		index (int): index where the point is contained. -1 if the point is in a sufficiently sized domain
		and therefore doesn't need to move from this domain. """

	domain_indices = range(len(domains))

	for i,dom in enumerate(domains):
		if dom[0] < param < dom[1]:
			if dom[1] - dom[0] < tolerance*2:
				#print dom[1] - dom[0]
				return i

	return -1


def get_closest_viable_domain(start_branch,domains,tolerance):

	def domain_len(domain):
		return domain[1]-domain[0]

	domain_indices = range(len(domains))

	branch_L = start_branch-1
	branch_L_len = domain_len(domains[branch_L])
	branch_R = start_branch+1
	branch_R_len = domain_len(domains[branch_R])
	ctr = 0
	moveto_branch = -1
	filled = [0 for x in xrange(len(domains))]

	branch_info = zip(range(2),[branch_L,branch_R],[branch_L_len,branch_R_len])
	sorted_branches = sorted(branch_info,key=lambda x:x[2]) #sort to get smallest first.

	while ctr < len(domain_indices):
		first_branch = sorted_branches[0]
		second_branch = sorted_branches[1]

		#see if the point can travel.
		if first_branch[2] > tolerance*2:
			moveto_branch = first_branch[1]
			break
		if second_branch[2] > tolerance*2:
			moveto_branch = second_branch[1]
			break

		#handle filling. if all full, done.
		if filled[first_branch[1]%len(domains)] < 1:
			filled[first_branch[1]%len(domains)] += 1
		if filled[second_branch[1]%len(domains)] < 1:
			filled[second_branch[1]%len(domains)] += 1

		if sum(filled) >= len(domains)-1:
			return -1

		#move along the tree
		branch_L -= 1
		branch_R += 1
		branch_L_len += domain_len(domains[branch_L%len(domains)])
		branch_R_len += domain_len(domains[branch_R%len(domains)])

		#get a new info set.
		branch_info = zip(range(2),[branch_L,branch_R],[branch_L_len,branch_R_len])
		sorted_branches = sorted(branch_info,key=lambda x:x[2])

	close_segment = domains[moveto_branch]
	return close_segment


def get_domain_mid(domain):
	return domain[0] + (domain[1]-domain[0])/2


#object methods
def reparametrize(crv_obj):
	crv_obj.Geometry.Domain = Rhino.Geometry.Interval(0,1)


def get_discontinuities(crv_obj):
	"""currently uses hacky method that places a discon at the beginning and end of curve"""
	#d = rs.CurveDiscontinuity(crv_obj.Id,5)

	cont = True
	start = 0
	end = crv_obj.CurveGeometry.Domain.T1
	dc_list = [0]
	while cont == True:
		dc_out = crv_obj.CurveGeometry.GetNextDiscontinuity(Rhino.Geometry.Continuity.G1_continuous,start,end)
		if dc_out[0] == True:
			dc_list.append(dc_out[1])
			start = dc_out[1]
		else:
			break
	dc_list.append(end)
	return dc_list


def retrieve_bridge_params(crv_obj,key):
	bridge_param = crv_obj.Attributes.GetUserString(key)
	if bridge_param == None:
		return Rhino.Commands.Result.Failure

	bridge_params = json.loads(bridge_param)
	if bridge_param == None:
		return Rhino.Commands.Result.Failure

	return bridge_params


def write_bridge_params(crv_obj,key,params):

	val = json.dumps(params)

	if val:
		crv_obj.Attributes.SetUserString( key, val )
		#print( 'Written value ' + val )
	else:
		val = crv_obj.Attributes.GetUserString( key )
		#print( 'Read value ' + val )


def tag_parameters(crv_geo,params):

	layer_index = add_layer("bridgePreview",sd.Color.Aqua)

	pts = points_from_params(crv_geo,params,layer_index)
	for param, pt in zip(params,pts):
		rs.AddTextDot(param,pt)

	return 0


#command methods rebuilt...
def m_addBridges(crv_obj_list, division_parameter, by_num=True):
	crv_geo_list = [x.CurveGeometry for x in crv_obj_list]

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		divide_count = 0
		if by_num == True:
			divide_count = division_parameter + 1
		elif division_parameter > 0:
			divide_count = crv_geo.Domain.Length // division_parameter
		else:
			return Rhino.Commands.Result.Failure

		curve_params = crv_geo.DivideByCount(divide_count, False)
		l_params = arr_to_list(curve_params)
		curve_params = move_points_from_seam(crv_geo,l_params)

		write_bridge_params(crv_obj,ATTRIBUTE_KEY,curve_params)

	return Rhino.Commands.Result.Success


def m_showBridges(crv_obj_list,cut_length,cut_tol,debug_tagparams=False):
	crv_geo_list = [x.CurveGeometry for x in crv_obj_list]
	cut_layer_index = add_layer("bridgePreview-cut",sd.Color.Aqua)
	boundary_layer_index = add_layer("bridgePreview-boundary",sd.Color.Fuchsia)
	if debug_tagparams == True: param_layer_index = add_layer("bridgePreview-param",sd.Color.Fuchsia)

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		bridge_params = retrieve_bridge_params(crv_obj,ATTRIBUTE_KEY)
		br_pts = points_from_params(crv_geo,bridge_params,cut_layer_index)
		if debug_tagparams == True: tag_parameters(crv_geo,bridge_params)
		for pt in br_pts:
			circ = add_circle_to_layer(pt,cut_length,cut_layer_index)
			circ = add_circle_to_layer(pt,cut_length+cut_tol,boundary_layer_index)
		if br_pts == None:
			return Rhino.Commands.Result.Failure

	if debug_tagparams == True:
		return [cut_layer_index,boundary_layer_index,param_layer_index]
	else:
		return [cut_layer_index,boundary_layer_index]


def m_manage_discons(crv_obj_list,cut_tol):
	
	error_flag = False
	crv_geo_list = [x.CurveGeometry for x in crv_obj_list]

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		discon_list = get_discontinuities(crv_obj)
		br_pts = retrieve_bridge_params(crv_obj,"lc_bridge_param")
		new_br_pts = []

		segment_domains = build_consecutive_domains(discon_list)
		#print segment_domains
		#search can be done better... much better
		
		for br_p in br_pts:
			#print "---"
			#print "SEARCHING PT", br_p
			new_br_p=br_p

			containment_index = get_domain_containment(br_p,cut_tol,segment_domains) #see if it is contained

			if containment_index == -1:
				#bridge can fit just fine into its segment, so bump it away from corner if necessary (function this?)
				for dc_p in discon_list:
					if 0 < (br_p - dc_p) < cut_tol:
						new_br_p = dc_p + cut_tol
						break
					elif 0 < (dc_p - br_p) < cut_tol:
						new_br_p = dc_p - cut_tol
						break
			else:
				#bridge can't fit so move it to the closest viable domain
				available_domain = get_closest_viable_domain(containment_index,segment_domains,cut_tol)
				print available_domain
				if available_domain != -1:
					new_br_p = get_domain_mid(available_domain)
				else:
					error_flag = True
			new_br_pts.append(new_br_p)
		
		if error_flag:
			print "There was a problem placing these bridges. Try reducing the bridge size."
		write_bridge_params(crv_obj,"lc_bridge_param",new_br_pts)


#a bit messy right now...
def m_makeBridgeLines(crv_obj_list,cut_length):

	default_groupWithin = sticky["defaultGroupWithin"] if sticky.has_key("defaultGroupWithin") else False
	default_groupBetween = sticky["defaultGroupBetween"] if sticky.has_key("defaultGroupBetween") else False
	default_delete = sticky["defaultDelete"] if sticky.has_key("defaultDelete") else False

	go = Rhino.Input.Custom.GetOption()
	opt_groupWithin = Rhino.Input.Custom.OptionToggle(default_groupWithin,"No","Yes")
	opt_groupBetween = Rhino.Input.Custom.OptionToggle(default_groupBetween,"No","Yes")
	opt_delete = Rhino.Input.Custom.OptionToggle(default_delete,"No","Yes")

	go.SetCommandPrompt("Select Output Options")
	go.AddOptionToggle("GroupBetween", opt_groupBetween)
	go.AddOptionToggle("GroupWithin", opt_groupWithin)
	go.AddOptionToggle("DeleteOriginals", opt_delete)

	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)

	res = None
	bHavePreselectedObjects = False

	while True:
		res = go.Get()

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			#print res
			continue

		#If not correct
		elif res == Rhino.Input.GetResult.Nothing:
			break

		return Rhino.Commands.Result.Failure

		break

	#Get geometry and object lists
	crv_geo_list = [x.CurveGeometry for x in crv_obj_list]

	l_index_cut = add_layer("XXX_LCUT_01-CUT",sd.Color.Red)
	l_index_score = add_layer("XXX_LCUT_02-SCORE",sd.Color.Blue)


	#MAIN GEOMETRY HANDLING. TO FUNCTION THIS OUT.
	fragment_guids = []
	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		bridge_params = retrieve_bridge_params(crv_obj,"lc_bridge_param")

		crv_bounds = (0,crv_obj.CurveGeometry.Domain.T1)
		sdoms = get_centered_subdomains(crv_bounds,bridge_params,cut_length)

		bridge_fragments = []
		#get little pieces... to add a loop to do big pieces. this currently might leave us with split-up fragments in places; may need to add a join command if two splits are made per pt.
		for pt in sdoms:
			for dom in pt:
				subcurve = []
				splitcurves = crv_geo.Split(dom[0])
				#if looped domain
				if dom[1] < dom[0]:
					for crv in splitcurves:
						if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
							subcurve.append(crv)
						else:
							newSplit = crv.Split(dom[1])
							subcurve.append(newSplit[0])
				else:
					for crv in splitcurves:
						if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
							newSplit = crv.Split(dom[1])
							subcurve.append(newSplit[0])
			bridge_fragments.extend(subcurve)

		#similar iteration through the complement domains. one fewer layer of depth because there are no sdoms split at the seam points (see if this is robust)
		c_sdoms = get_complement_domains(sdoms)
		cut_fragments = []
		for dom in c_sdoms:
			subcurve = []
			splitcurves = crv_geo.Split(dom[0])
			#if looped domain
			if dom[1] < dom[0]:
				for crv in splitcurves:
					if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
						subcurve.append(crv)
					else:
						newSplit = crv.Split(dom[1])
						subcurve.append(newSplit[0])
			else:
				for crv in splitcurves:
					if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
						newSplit = crv.Split(dom[1])
						#print newSplit
						subcurve.append(newSplit[0])
			cut_fragments.extend(subcurve)


		thiscurve_fragments = []
		for item in cut_fragments:
			temp = item
			thiscurve_fragments.append(add_curve_to_layer(item,l_index_cut))
		for item in bridge_fragments:
			thiscurve_fragments.append(add_curve_to_layer(item,l_index_score))

		if opt_groupWithin.CurrentValue == True:
			sc.doc.Groups.Add(thiscurve_fragments)

		fragment_guids.extend(thiscurve_fragments)

	if opt_groupBetween.CurrentValue == True:
		sc.doc.Groups.Add(fragment_guids)

	rs.UnselectAllObjects()
	rs.SelectObjects(fragment_guids)
	sc.doc.Views.Redraw()

	sticky["defaultGroupWithin"] = opt_groupWithin.CurrentValue
	sticky["defaultGroupBetween"] = opt_groupBetween.CurrentValue
	sticky["defaultDelete"] = opt_delete.CurrentValue

	if opt_delete.CurrentValue == True:
		ids = [x.Id for x in crv_obj_list]
		rs.DeleteObjects(ids)




#main rc
def rc_Bridge():
	#get stickies
	default_bridge_size = sticky["defaultSize"] if sticky.has_key("defaultSize") else 2
	default_bridge_border = sticky["defaultBorder"] if sticky.has_key("defaultBorder") else 2
	default_bynum_bool = sticky["defaultByNum"] if sticky.has_key("defaultByNum") else True

	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.ClosedCurve

	opt_bridge_size = Rhino.Input.Custom.OptionDouble(default_bridge_size,0.2,1000)
	opt_bridge_border = Rhino.Input.Custom.OptionDouble(default_bridge_border,0.2,1000)
	opt_by_num = Rhino.Input.Custom.OptionToggle(default_bynum_bool,"ByLength","ByNumber")

	go.SetCommandPrompt("Select Curves for Bridging")
	go.AddOptionDouble("BridgeSize", opt_bridge_size)
	go.AddOptionDouble("BridgeBorder", opt_bridge_border)
	out_mode = go.AddOptionToggle("Mode",opt_by_num)

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
			continue

		#If not correct
		elif res != Rhino.Input.GetResult.Object:
			return Rhino.Commands.Result.Cancel

		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue

		break

	CUT_LENGTH = opt_bridge_size.CurrentValue
	CUT_TOL = opt_bridge_border.CurrentValue
	BY_NUM = opt_by_num.CurrentValue

	#get properties of objects
	crv_max_length = 0
	crv_obj_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		if i == 0:
			crv_max_length = c_obj.CurveGeometry.Domain.Mid
		else:
			crv_max_length = min(crv_max_length,c_obj.CurveGeometry.Domain.Mid)


	#add bridges by length or by number.
	if BY_NUM == True:
		default_segmentCount = sticky["defaultSegmentCount"] if sticky.has_key("defaultSegmentCount") else 2

		rc, segment_count = Rhino.Input.RhinoGet.GetInteger("Divide curves into how many segments?",True,default_segmentCount,2,500)
		if rc != Rhino.Commands.Result.Success:
			return rc
		m_addBridges(crv_obj_list,segment_count)
		sticky["defaultSegmentCount"] = segment_count
	else:
		default_segmentLength = sticky["defaultSegLength"] if (sticky.has_key("defaultSegLength") and sticky["defaultSegLength"] < crv_max_length) else crv_max_length/2
		s = "What approximate length would you like to target? The maximum for these curves is {0:.2f}".format(crv_max_length)
		rc, segment_length = Rhino.Input.RhinoGet.GetNumber(s, False, default_segmentLength, 0, crv_max_length)
		if rc != Rhino.Commands.Result.Success:
			return rc
		m_addBridges(crv_obj_list,segment_length,False)
		sticky["defaultSegLen"] = segment_length



	#display the bridges and request options.
	go = Rhino.Input.Custom.GetOption()
	opt_bridge_size = Rhino.Input.Custom.OptionDouble(CUT_LENGTH,0.2,1000)
	opt_bridge_border = Rhino.Input.Custom.OptionDouble(CUT_TOL,0.2,1000)

	go.SetCommandPrompt("Adjust Options. Enter to Continue.")
	go.AddOptionDouble("BridgeSize", opt_bridge_size)
	go.AddOptionDouble("BridgeBorder", opt_bridge_border)
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)

	#draw the preview.
	buffer_distance = CUT_LENGTH+CUT_TOL
	m_manage_discons(crv_obj_list, buffer_distance)
	preview_layers = m_showBridges(crv_obj_list,CUT_LENGTH,CUT_TOL)
	rs.Redraw()
	while True:
		res = go.Get()

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			for layer_ind in preview_layers:
				Rhino.DocObjects.Tables.LayerTable.Purge(doc.ActiveDoc.Layers,layer_ind,True)
			CUT_LENGTH = opt_bridge_size.CurrentValue
			CUT_TOL = opt_bridge_border.CurrentValue
			buffer_distance = CUT_LENGTH+CUT_TOL
			m_manage_discons(crv_obj_list, buffer_distance)
			preview_layers = m_showBridges(crv_obj_list,CUT_LENGTH,CUT_TOL)
			rs.Redraw()
			continue

		#If not correct
		elif res == Rhino.Input.GetResult.Nothing:
			for layer_ind in preview_layers:
				doc.ActiveDoc.Layers
				Rhino.DocObjects.Tables.LayerTable.Purge(doc.ActiveDoc.Layers,layer_ind,True)
			break

		for layer_ind in preview_layers:
			doc.ActiveDoc.Layers
			Rhino.DocObjects.Tables.LayerTable.Purge(doc.ActiveDoc.Layers,layer_ind,True)
		return Rhino.Commands.Result.Failure

		break

	CUT_LENGTH = opt_bridge_size.CurrentValue
	CUT_TOL = opt_bridge_border.CurrentValue

	#Request output options.
	m_makeBridgeLines(crv_obj_list,CUT_LENGTH)

	sticky["defaultSize"] = CUT_LENGTH
	sticky["defaultBorder"] = CUT_TOL
	sticky["defaultByNum"] = BY_NUM
	return Rhino.Commands.Result.Success


#run commands.
#deprecated but remain for debug.
def rc_addBridges():

	#set getobject
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.ClosedCurve
	go.SetCommandPrompt( 'Select Bridging' )
	go.GetMultiple(1,0)

	#get the list of curve objects and curve geometries
	crv_obj_list = []
	crv_geo_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		crv_geo_list.append(c_obj.CurveGeometry)

	segment_count = 0
	result, segment_count = Rhino.Input.RhinoGet.GetInteger("Divide curves into how many segments?", False, segment_count)
	if result <> Rhino.Commands.Result.Success:
		return result

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		curve_params = crv_geo.DivideByCount(segment_count, True)
		l_params = arr_to_list(curve_params)
		curve_params = move_points_from_seam(crv_geo,l_params)

		write_bridge_params(crv_obj,ATTRIBUTE_KEY,curve_params)


def rc_showBridges():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.ClosedCurve
	go.SetCommandPrompt( 'Objects ?' )
	go.GetMultiple(1,0)

	key = "lc_bridge_param"

	#get the list of curve objects and curve geometries
	crv_obj_list = []
	crv_geo_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		crv_geo_list.append(c_obj.CurveGeometry)

	layer_index = add_layer("bridgePreview",sd.Color.Aqua)

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		bridge_params = retrieve_bridge_params(crv_obj,key)
		br_pts = points_from_params(crv_geo,bridge_params,layer_index)
		tag_parameters(crv_geo,bridge_params)

		for pt in br_pts:
			circ = add_circle_to_layer(pt,CUT_LENGTH,layer_index)
			circ = add_circle_to_layer(pt,CUT_TOL,layer_index)

		if br_pts == None:
			return Rhino.Commands.Result.Failure

	sc.doc.Views.Redraw()


#placeholder script for managing proximity to discontinuities.
def rc_manageDc():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.ClosedCurve
	go.SetCommandPrompt( 'Objects ?' )
	go.GetMultiple(1,0)

	#get the list of curve objects and curve geometries
	crv_obj_list = []
	crv_geo_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		crv_geo_list.append(c_obj.CurveGeometry)

	layer_index = add_layer("bridgePreview",sd.Color.Aqua)

	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		discon_list = get_discontinuities(crv_obj)
		#dc_pts = points_from_params(crv_geo,discon_list, layer_index) #show discontinuities
		br_pts = retrieve_bridge_params(crv_obj,"lc_bridge_param")
		#print discon_list
		#print br_pts
		new_br_pts = []

		segment_domains = build_consecutive_domains(discon_list)
		#print segment_domains

		#search can be done better... much better
		for br_p in br_pts:
			#print "---"
			#print "SEARCHING PT", br_p
			new_br_p=br_p

			containment_index = get_domain_containment(br_p,CUT_TOL,segment_domains)

			if containment_index == -1:
				#point can fit just fine into its segment, so bump it away from corner if necessary (function this?)
				for dc_p in discon_list:
					"testing loop"
					if 0 < (br_p - dc_p) < CUT_TOL:
						new_br_p = dc_p + CUT_TOL
						break
					elif 0 < (dc_p - br_p) < CUT_TOL:
						new_br_p = dc_p - CUT_TOL
						break
			else:
				available_domain = get_closest_viable_domain(containment_index,segment_domains,CUT_TOL)
				new_br_p = get_domain_mid(available_domain)

			new_br_pts.append(new_br_p)

		write_bridge_params(crv_obj,"lc_bridge_param",new_br_pts)


def rc_makeBridgeLines():
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.ClosedCurve

	opt_groupWithin = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_groupBetween = Rhino.Input.Custom.OptionToggle(False,"No","Yes")
	opt_delete = Rhino.Input.Custom.OptionToggle(False,"No","Yes")

	go.SetCommandPrompt("Select Closed Polycurves")
	go.AddOptionToggle("GroupBetween", opt_groupBetween)
	go.AddOptionToggle("GroupWithin", opt_groupWithin)
	go.AddOptionToggle("DeleteOriginals", opt_delete)

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

	#Get geometry and object lists
	crv_obj_list = []
	crv_geo_list = []
	for i in xrange(go.ObjectCount):
		c_obj = go.Object(i).Object()
		crv_obj_list.append(c_obj)
		crv_geo_list.append(c_obj.CurveGeometry)

	l_index_cut = add_layer("XXX_LCUT_01-CUT",sd.Color.Red)
	l_index_score = add_layer("XXX_LCUT_02-SCORE",sd.Color.Blue)


	#MAIN GEOMETRY HANDLING. TO FUNCTION THIS OUT.
	fragment_guids = []
	for crv_obj, crv_geo in zip(crv_obj_list, crv_geo_list):
		bridge_params = retrieve_bridge_params(crv_obj,"lc_bridge_param")

		crv_bounds = (0,crv_obj.CurveGeometry.Domain.T1)
		sdoms = get_centered_subdomains(crv_bounds,bridge_params,CUT_LENGTH)

		bridge_fragments = []
		#get little pieces... to add a loop to do big pieces. this currently might leave us with split-up fragments in places; may need to add a join command if two splits are made per pt.
		for pt in sdoms:
			for dom in pt:
				subcurve = []
				splitcurves = crv_geo.Split(dom[0])
				#if looped domain
				if dom[1] < dom[0]:
					for crv in splitcurves:
						if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
							subcurve.append(crv)
						else:
							newSplit = crv.Split(dom[1])
							subcurve.append(newSplit[0])
				else:
					for crv in splitcurves:
						if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
							newSplit = crv.Split(dom[1])
							subcurve.append(newSplit[0])
			bridge_fragments.extend(subcurve)

		#similar iteration through the complement domains. one fewer layer of depth because there are no sdoms split at the seam points (see if this is robust)
		c_sdoms = get_complement_domains(sdoms)
		cut_fragments = []
		for dom in c_sdoms:
			subcurve = []
			splitcurves = crv_geo.Split(dom[0])
			#if looped domain
			if dom[1] < dom[0]:
				for crv in splitcurves:
					if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
						subcurve.append(crv)
					else:
						newSplit = crv.Split(dom[1])
						subcurve.append(newSplit[0])
			else:
				for crv in splitcurves:
					if (abs(crv.Domain.T0 - dom[0])) < D_TOL:
						newSplit = crv.Split(dom[1])
						#print newSplit
						subcurve.append(newSplit[0])
			cut_fragments.extend(subcurve)


		thiscurve_fragments = []
		for item in cut_fragments:
			temp = i
			thiscurve_fragments.append(add_curve_to_layer(item,l_index_cut))
		for item in bridge_fragments:
			thiscurve_fragments.append(add_curve_to_layer(item,l_index_score))

		if opt_groupWithin.CurrentValue == True:
			sc.doc.Groups.Add(thiscurve_fragments)

		fragment_guids.extend(thiscurve_fragments)

	if opt_groupBetween.CurrentValue == True:
		sc.doc.Groups.Add(fragment_guids)

	rs.UnselectAllObjects()
	rs.SelectObjects(fragment_guids)
	sc.doc.Views.Redraw()

	if opt_delete.CurrentValue == True:
		ids = [x.Id for x in crv_obj_list]
		rs.DeleteObjects(ids)


# RunCommand is the called when the user enters the command name in Rhino.
# The command name is defined by the filname minus "_cmd.py"
def RunCommand( is_interactive ):
	setGlobals()
	rc_Bridge()
#	rc_addBridges()
#	rc_manageDc()
#	rc_showBridges()
#	rc_makeBridgeLines()
	return 0

RunCommand(True)
