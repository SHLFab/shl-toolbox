"""
SHL Architects 30-01-2019
Sean Lamb (Developer)
sel@shl.dk
-better handling of different brep types
"""

import rhinoscriptsyntax as rs
layers=rs.LayerNames()
num_layers = 0
for layer in layers:
	if rs.IsLayerEmpty(layer):
		if rs.IsLayerCurrent(layer):
			print "Current layer is empty but will not be removed."
		else:
			rs.DeleteLayer(layer)
			num_layers += 1
print "%d empty layers removed." % num_layers