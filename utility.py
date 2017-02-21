import snakes.nets
from snakes.nets import *

# find the max outgoing weight for a place
def max_out(place):
	assert isinstance(place, Place)
	if len(place.post) == 0:
		return 0
	return max(map(weight_from_edge, place.post))

def weight_from_edge(e):
	if isinstance(e, MultiArc):
		return e.__len__() # not good
	else:
		return 1
