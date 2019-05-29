"""help docstring"""
#workshop_lib
#rhino utilities

#SHL Architects
#Sean Lamb 2018-09-26
#TODO: define an __all__

import math
from itertools import count, takewhile
import colorsys
import rhinoscriptsyntax as rs


def equidistant_hsv_color(num,saturation):
	"""returns tuple of colours with equidistantly spaced hue"""
	colors = []
	for k in xrange(num):
		color = colorsys.hsv_to_rgb((1/float(num))*k,saturation,1.0)
		colors.append(tuple([int(255*i) for i in color]))
	return colors

def frange(start,stop,step):
	"""floating point range. output vals will not exceed the stop param.
		params:
		start: start of range
		stop: end of range
		step: increment
	returns:
		list of floats"""
	return list( takewhile(lambda x: x <= stop, (start + i * step for i in count())) )


def num_div(num,divisor):
	"""number of divisors. posibly not necessary w/ divmod"""
	divs = -1
	if num < divisor:
		return -1
	if num == divisor:
		return 0
	while num>0:
		divs += 1
		num = num - divisor
	return divs-1


def number_to_letter(num,start=0,upper=True,append=True):
	"""convert int to uppercase letter. ***will wrap if out of alphabet bounds***
	params:
		num: int
		start=0: base number corresponding to 'a'
		upper=True: convert to upper
		append=True: append when wrapping.
	returns:
		letter: character corresponding to number
	DEV NOTES: still a bug in here"""

	divs = num_div(num,26)
	num = num % 26
	#print divs
	shifted = num + 97 - start
	letters = chr(shifted)

	if divs > -1:
		letters = str( chr(divs + 97) ) + str(letters)
	#print letters
	if upper==True: letters=letters.upper()

	return letters


def dotprod(a,b):
	dprod = 0
	for i,j in zip(a,b):
		#print i,j
		dprod += i*j
	return dprod


def xprod(a,b):
	xprod = a[0]*b[1] - a[1]*b[0]
	return xprod


def innerangle(a,b,radians=False):
	dp = dotprod(a,b)
	len_1 = rs.VectorLength(a)
	len_2 = rs.VectorLength(b)
	#print len_1
	#print len_2
	innerangle = math.acos(dp/(len_1*len_2))
	if radians == False:
		innerangle = math.degrees(innerangle)

	return innerangle


def partition_objects_by_attr(objects,attribute,reverse_bool=False):
	"""params:
		objects: list of objects
		attribute: str of attribute to partition by.
		reverse: reverse the sorting order for the partition
	returns:
		object[][]: list of lists of objects partitioned by the attribute.
	"""
	objects.sort(key=lambda x:getattr(x,attribute), reverse=reverse_bool)

	set_sorter = sorted(set([getattr(x,attribute) for x in objects])) #sorted set of possible heights
	print set_sorter

	partitioned_list = []
	for i,item in enumerate(set_sorter):
		partitioned_list.append(filter(lambda x: getattr(x,attribute) == item, objects))

	return partitioned_list
