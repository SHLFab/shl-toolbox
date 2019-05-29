"""help docstring"""
#workshop_lib
#rhino fabrication functions

#SHL Architects
#Sean Lamb 2018-11-02
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


def add_fab_tags(tag_points, tag_text, tag_size, text_justification=Rhino.Geometry.TextJustification.Center):
	"""in:
	tag_points: list of point3ds
	tag_text: list of tag text
	tage_size: size of text
	text_justification: Rhino.Geometry.TextJustification.<option goes here>
	returns:
	guids of exploded curves representing the text
	"""
	text_guids = []
	fi = sc.doc.Fonts.FindOrCreate("MecSoft_Font-1", True, False)
	plane = Rhino.Geometry.Plane.WorldXY
	#rs.EnableRedraw(True)
	for i, (pt,tag) in enumerate(zip(tag_points,tag_text)):
			plane=Rhino.Geometry.Plane.WorldXY
			plane.Origin = pt
			te = Rhino.Geometry.TextEntity()
			te.Text = tag
			te.TextHeight = tag_size
			te.Plane = plane
			te.FontIndex = fi
			te.Justification = text_justification
			text_guids.append(sc.doc.Objects.AddText(te))

	text_crv_guids = [rs.ExplodeText(text) for text in text_guids]
	rs.DeleteObjects(text_guids) #remove the text objects
	rs.EnableRedraw(False)
	return text_crv_guids
