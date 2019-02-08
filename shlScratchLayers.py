"""
SHL Architects 07-02-2019
Sean Lamb (Developer)
sel@shl.dk
"""
import rhinoscriptsyntax as rs
import shl_toolbox_lib_dev.util as wut
reload(wut)

num = rs.GetInteger("Enter number of layers")
prefix = rs.GetString("Enter layer name prefix")

colors = wut.equidistant_hsv_color(num,0.4)

for i in xrange(num):
	rs.AddLayer(prefix + "-" + str(i),colors[i])