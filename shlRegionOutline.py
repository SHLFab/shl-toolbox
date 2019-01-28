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

	#Get original curves and curves to extend
	input_curves = rs.GetObjects("Select Curves", 4, False, True, True)
	rs.EnableRedraw(True)

	#Get length
	extension_length = rs.GetInteger("Enter Extension Length")
	if not extension_length:
		rs.EnableRedraw(True)
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
	# print "doc is", type(sc.doc)
	pcurve_outline = rs.LastCreatedObjects()
	# print Rhino.RhinoDoc.ActiveDoc
	# print sc.doc.ActiveDoc
	#doc = Rhino.RhinoDoc.ActiveDoc

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
	rs.UnlockObjects(preview_srf)
	rs.UnlockObjects(arr_preview_geom)
	rs.DeleteObjects(preview_srf)
	rs.DeleteObjects(arr_preview_geom)
	if isinstance(pcurve_outline,list):
		rs.SelectObjects(pcurve_outline)
	rs.EnableRedraw(True)


def RunCommand( is_interactive ):
	outline_region()
	return 0

RunCommand(True)
