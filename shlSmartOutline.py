"""
SHL Architects 16-10-2018
v1.1 Sean Lamb (Developer)
sel@shl.dk
v1.1 08-10-2018: error handling
"""

import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

__commandname__ = "shlRegionOutline"

def get_preview_geometry(arr_curves):
	"""duplicate the geometry for extension"""
	arr_exploded = []

	arr_lines = []

	for x in arr_curves:
		if rs.IsLine(x):
			arr_exploded.append(x)

	for i in xrange(len(arr_curves)):
		if rs.IsLine(arr_curves[i]):
			arr_lines.append(arr_curves[i])

	arr_preview_exploded = rs.ExplodeCurves(arr_curves,False)
	arr_preview_lines = rs.CopyObjects(arr_lines)

	#Get locked objects
	return arr_preview_exploded + arr_preview_lines


def outline_region():
	
	default_length = sc.sticky["length"] if sc.sticky.has_key("length") else 100
	
	#Get original curves and curves to extend
	input_curves = rs.GetObjects("Select Curves", 4, False, True, True)
	if not input_curves: return
	
	#Get length
	extension_length = rs.GetInteger(message="Enter Extension Length",number=default_length)
	if not extension_length:
		rs.EnableRedraw(True)
		print "No Extension Length entered."
		return False

	arr_preview_geom = get_preview_geometry(input_curves)
	for indCrv in arr_preview_geom:
		rs.ExtendCurveLength(indCrv,0,2,extension_length)
	
	rs.EnableRedraw(False)
	#Get curveboolean and display it
	region_was_created = True
	rs.UnselectAllObjects()
	rs.SelectObjects(arr_preview_geom)
	# print Rhino.RhinoDoc.ActiveDoc
	# print sc.doc.ActiveDoc
	
	rs.Command("_-CurveBoolean _AllRegions _Enter")
	
	pcurve_outline = rs.LastCreatedObjects()
	
	if isinstance(pcurve_outline,list):
		preview_srf = rs.AddPlanarSrf(pcurve_outline)
		rs.LockObjects(arr_preview_geom)
		rs.LockObjects(preview_srf)
	else:
		region_was_created = False
		rs.LockObjects(arr_preview_geom)
		preview_srf = []

	rs.EnableRedraw(True)
	rs.Redraw()

	#Set up input object
	go = Rhino.Input.Custom.GetOption()
	optint = Rhino.Input.Custom.OptionDouble(extension_length)

	prompt = "Press Enter to accept"
	warning = "Insufficient overlap length. "
	s = prompt if region_was_created else warning+prompt
	go.SetCommandPrompt(s)
	go.AddOptionDouble("ExtensionLength", optint)
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)

	#control flow: can distinguish between inserting an option, cancelling, and pressing enter
	res = None
	while True:
		res = go.Get()
		rs.EnableRedraw(False)
		region_was_created = True

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			#Delete old preview
			rs.UnlockObjects(preview_srf)
			rs.UnlockObjects(arr_preview_geom)
			rs.DeleteObjects(preview_srf)
			rs.DeleteObjects(arr_preview_geom)
			if isinstance(pcurve_outline,list):
				rs.DeleteObjects(pcurve_outline)
			rs.SelectObjects(input_curves)

			#Draw new preview
			arr_preview_geom = get_preview_geometry(input_curves)
			if not extension_length: return False

			for indCrv in arr_preview_geom:
				rs.ExtendCurveLength(indCrv,0,2,optint.CurrentValue)

			rs.UnselectAllObjects()
			rs.SelectObjects(arr_preview_geom)
			rs.Command("_-CurveBoolean _AllRegions _Enter")
			pcurve_outline = rs.LastCreatedObjects()

			if isinstance(pcurve_outline,list):
				preview_srf = rs.AddPlanarSrf(pcurve_outline)
				rs.LockObjects(arr_preview_geom)
				rs.LockObjects(preview_srf)
			else:
				rs.LockObjects(arr_preview_geom)
				preview_srf = []
				region_was_created = False
			rs.EnableRedraw(True)

			s = prompt if region_was_created else warning+prompt
			go.SetCommandPrompt(s)

			continue

		#If accepted, leave loop
		elif res == Rhino.Input.GetResult.Nothing:
			break

		#If cancelled, delete working geometry
		elif res != Rhino.Input.GetResult.Option:
			rs.UnlockObjects(preview_srf)
			rs.UnlockObjects(arr_preview_geom)
			rs.DeleteObjects(preview_srf)
			rs.DeleteObjects(arr_preview_geom)
			rs.DeleteObjects(pcurve_outline)
			rs.EnableRedraw(True)
			return Rhino.Commands.Result.Cancel
	
	sc.sticky["length"] = optint.CurrentValue
	#Clean up if successful
	rs.UnlockObjects(preview_srf)
	rs.UnlockObjects(arr_preview_geom)
	rs.DeleteObjects(preview_srf)
	rs.DeleteObjects(arr_preview_geom)
	if isinstance(pcurve_outline,list):
		rs.SelectObjects(pcurve_outline)
	rs.EnableRedraw(True)


def outline_region2():
	
	
	go = Rhino.Input.Custom.GetObject()
	go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
	
	default_length = sc.sticky["length"] if sc.sticky.has_key("length") else 100
	default_delete = sc.sticky["delete"] if sc.sticky.has_key("delete") else True
	
	opt_delete = Rhino.Input.Custom.OptionToggle(default_delete,"No","Yes")
	go.SetCommandPrompt("Select Curves")
	go.AddOptionToggle("DeleteInput", opt_delete)

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
			print "No curves selected!"
			return Rhino.Commands.Result.Cancel
		if go.ObjectsWerePreselected:
			bHavePreselectedObjects = True
			go.EnablePreSelect(False, True)
			continue
		break
	
	input_curves = []
	for i in xrange(go.ObjectCount):
		b_obj = go.Object(i).Object()
		input_curves.append(b_obj.Id)
	
	#Get length
	extension_length = rs.GetInteger(message="Enter Extension Length",number=default_length)
	if not extension_length:
		rs.EnableRedraw(True)
		print "No Extension Length entered."
		return False

	arr_preview_geom = get_preview_geometry(input_curves)
	for indCrv in arr_preview_geom:
		rs.ExtendCurveLength(indCrv,0,2,extension_length)
	
	rs.EnableRedraw(False)
	#Get curveboolean and display it
	region_was_created = True
	rs.UnselectAllObjects()
	rs.SelectObjects(arr_preview_geom)
	# print Rhino.RhinoDoc.ActiveDoc
	# print sc.doc.ActiveDoc
	
	rs.Command("_-CurveBoolean _AllRegions _Enter")
	
	pcurve_outline = rs.LastCreatedObjects()
	
	if isinstance(pcurve_outline,list):
		preview_srf = rs.AddPlanarSrf(pcurve_outline)
		rs.LockObjects(arr_preview_geom)
		rs.LockObjects(preview_srf)
	else:
		region_was_created = False
		rs.LockObjects(arr_preview_geom)
		preview_srf = []

	rs.EnableRedraw(True)
	rs.Redraw()

	#Set up input object
	go = Rhino.Input.Custom.GetOption()
	optint = Rhino.Input.Custom.OptionDouble(extension_length)

	prompt = "Press Enter to accept"
	warning = "Insufficient overlap length. "
	s = prompt if region_was_created else warning+prompt
	go.SetCommandPrompt(s)
	go.AddOptionDouble("ExtensionLength", optint)
	go.AcceptEnterWhenDone(True)
	go.AcceptNothing(True)

	#control flow: can distinguish between inserting an option, cancelling, and pressing enter
	res = None
	while True:
		res = go.Get()
		rs.EnableRedraw(False)
		region_was_created = True

		#If new option entered, redraw a possible result
		if res == Rhino.Input.GetResult.Option:
			#Delete old preview
			rs.UnlockObjects(preview_srf)
			rs.UnlockObjects(arr_preview_geom)
			rs.DeleteObjects(preview_srf)
			rs.DeleteObjects(arr_preview_geom)
			if isinstance(pcurve_outline,list):
				rs.DeleteObjects(pcurve_outline)
			rs.SelectObjects(input_curves)

			#Draw new preview
			arr_preview_geom = get_preview_geometry(input_curves)
			if not extension_length: return False

			for indCrv in arr_preview_geom:
				rs.ExtendCurveLength(indCrv,0,2,optint.CurrentValue)

			rs.UnselectAllObjects()
			rs.SelectObjects(arr_preview_geom)
			rs.Command("_-CurveBoolean _AllRegions _Enter")
			pcurve_outline = rs.LastCreatedObjects()

			if isinstance(pcurve_outline,list):
				preview_srf = rs.AddPlanarSrf(pcurve_outline)
				rs.LockObjects(arr_preview_geom)
				rs.LockObjects(preview_srf)
			else:
				rs.LockObjects(arr_preview_geom)
				preview_srf = []
				region_was_created = False
			rs.EnableRedraw(True)

			s = prompt if region_was_created else warning+prompt
			go.SetCommandPrompt(s)

			continue

		#If accepted, leave loop
		elif res == Rhino.Input.GetResult.Nothing:
			break

		#If cancelled, delete working geometry
		elif res != Rhino.Input.GetResult.Option:
			rs.UnlockObjects(preview_srf)
			rs.UnlockObjects(arr_preview_geom)
			rs.DeleteObjects(preview_srf)
			rs.DeleteObjects(arr_preview_geom)
			rs.DeleteObjects(pcurve_outline)
			rs.EnableRedraw(True)
			return Rhino.Commands.Result.Cancel
	

	#Clean up if successful
	if opt_delete.CurrentValue == True: rs.DeleteObjects(input_curves)
	rs.UnlockObjects(preview_srf)
	rs.UnlockObjects(arr_preview_geom)
	rs.DeleteObjects(preview_srf)
	rs.DeleteObjects(arr_preview_geom)
	if isinstance(pcurve_outline,list):
		rs.SelectObjects(pcurve_outline)
	
	sc.sticky["length"] = optint.CurrentValue
	sc.sticky["delete"] = opt_delete.CurrentValue
	
	rs.EnableRedraw(True)


def RunCommand( is_interactive ):
#	outline_region()
	outline_region2()
	return 0

RunCommand(True)
