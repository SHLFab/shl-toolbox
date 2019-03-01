"""
SHL Architects 16-10-2018
v1.0 Sean Lamb (Developer)
sel@shl.dk
-removed interactive
"""

import rhinoscriptsyntax as rs
import Rhino
from scriptcontext import sticky

import shl_toolbox_lib.layers as wla
reload(wla)

# __commandname__ = "shlLaserSheet"

def unit_convert(dimension):
	"""assumes we want to convert to mm"""
	current_system = rs.UnitSystem()
	#see rs documentation for UnitSystem. Some units not implemented.
	unit_dict = {
		1: 1.0e-6,
		2: 1.0e-3,
		3: 1.0e-2,
		4: 1.0,
		5: 1.0e+3,
		6: 2.54e-8,
		7: 2.54e-5,
		8: 0.0254,
		9: 0.3408,
		10: 1609.344,
		12: 1.0e-10,
		13: 1.0e-9,
		14: 1.0e-1,
		15: 1.0e+1,
		16: 1.0e+2,
		17: 1.0e+6,
		18: 1.0e+9,
		19: 0.9144,
		22: 1852,
		23: 1.4959787e+11,
		24: 9.46073e+15,
		25: 3.08567758e+16
	}
	conversion = 1
	if current_system != 2:
		conversion = unit_dict[2] / unit_dict[current_system]

	return dimension*conversion


def RunCommand( is_interactive ):	
	margin = 5
	L, W = 810, 455
	basept = Rhino.Geometry.Point3d(0,0,0)

	L = unit_convert(L)
	W = unit_convert(W)
	margin = unit_convert(margin)
	go = Rhino.Input.Custom.GetPoint()
	opt_L = Rhino.Input.Custom.OptionDouble(L,0.2,10000)
	opt_W = Rhino.Input.Custom.OptionDouble(W,0.2,10000)

	go.SetCommandPrompt("Pick lower left corner of lasercut area or Enter to place at origin. Default sheet size is L=%.2f, W=%.2f" % (L,W))
	go.AddOptionDouble("Length", opt_L)
	go.AddOptionDouble("Width", opt_W)
	go.AcceptNothing(True)

	while True:
		res = go.Get()
		if res == Rhino.Input.GetResult.Option:
			continue
		elif res == Rhino.Input.GetResult.Cancel:
			return
		elif res == Rhino.Input.GetResult.Nothing:
			pass
		elif res == Rhino.Input.GetResult.Point:
			basept = go.Point()
		break
	
	layer_dict = wla.get_lcut_layers()
	plane = rs.WorldXYPlane()
	plane = rs.MovePlane(plane,basept)
	inner_rect = rs.AddRectangle(plane,L-margin*2,W-margin*2)
	plane = rs.MovePlane(plane, rs.PointAdd(basept, [-margin,-margin,0]))
	outer_rect = rs.AddRectangle(plane, L, W)
	rs.ObjectLayer([inner_rect, outer_rect],"XXX_LCUT_00-GUIDES")
	rs.SelectObjects([inner_rect,outer_rect])
	return True

RunCommand(True)
