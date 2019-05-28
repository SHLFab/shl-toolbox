"""help docstring"""
#workshop_lib
#rhino utilities

#SHL Architects
#Sean Lamb 2018-09-26
#TODO: define an __all__

import rhinoscriptsyntax as rs
import Rhino
from scriptcontext import doc
import scriptcontext as sc
import System

import shl_toolbox_lib.util as wut
reload(wut)

import random
from collections import namedtuple


def extrusion_to_brep(extrusion):
	"""convert a single extrusion geometry to a brep geometry"""
	if extrusion.HasBrepForm == True: brep = extrusion.ToBrep()
	return brep


def docobj_to_guid(doc_input):
	"""convert list of doc objects to guids. handles single objects as well."""
	if isinstance(doc_input, list):
		output = [obj.Id for obj in doc_input]
	else:
		output = doc_input.Id
	return output


def add_curve_to_layer(curve,layer_index):
	"""add curve to layer by layer index"""
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	crv_added = doc.Objects.AddCurve(curve,attribs)
	if crv_added != System.Guid.Empty:
		return crv_added
	return Rhino.Commands.Result.Failure


def add_brep_to_layer(brep,layer_index):
	"""add brep to layer by layer index"""
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	crv_added = doc.Objects.AddBrep(brep,attribs)
	if crv_added != System.Guid.Empty:
		return crv_added
	return Rhino.Commands.Result.Failure


def add_curves_to_layer(curves_list,layer_index):
	"""add list of curves to layer by layer index"""
	attribs = Rhino.DocObjects.ObjectAttributes()
	attribs.LayerIndex = layer_index
	crv_added = []
	for curve in curves_list:
		crv_added.append(doc.Objects.AddCurve(curve,attribs))
	return crv_added


def polycurve_to_polyline(g_polycurve,absolute_tolerance,angle_tolerance):
	"""convert a polycurve to a polyline"""
	max_len = 0
	min_len = 0

	for i in xrange(g_polycurve.SegmentCount):
		seg = g_polycurve.SegmentCurve(i)
		#print i
		seg_len = seg.GetLength()
		#get segs
		if i == 0: min_len = seg_len
		if seg_len > max_len: max_len = seg_len
		if seg_len < min_len: min_len = seg_len

	#Polyline conversion
	g_polyline = g_polycurve.ToPolyline(doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceDegrees,min_len,max_len)

	return g_polyline


def polylinecurve_to_polycurve(g_polylinecurve):
	g_polycurve = Rhino.Geometry.PolyCurve()
	ptcount = g_polylinecurve.PointCount
	for i in xrange(ptcount-1):
		pt1 = g_polylinecurve.Point(i)
		pt2 = g_polylinecurve.Point(i+1)
		line = Rhino.Geometry.Line(pt1,pt2)
		g_polycurve.Append(line)
	g_polycurve.MakeClosed(doc.ActiveDoc.ModelAbsoluteTolerance)
	return g_polycurve
