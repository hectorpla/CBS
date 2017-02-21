import snakes.plugins
import utility
import snakes.nets
from snakes.nets import *

# make the state graph suitable for using net marking in guards for transitions
@snakes.plugins.plugin("snakes.nets")
def extend(module):
	class StateGraph(module.StateGraph):
		def __init__(self, net):
			module.StateGraph.__init__(self, net)
			W = {} # the max outgoing weights for places
			this_net = self.net
			# clone transition for each type
			for place in this_net.place():
				t = place.name
				tr = 'clone_' + t
				W[t] = utility.max_out(place)
				this_net.add_transition(Transition(tr))
				this_net.add_input(t, tr, Variable(t[:3]))
				this_net.add_output(t, tr, MultiArc([Expression(t[:3]), Expression(t[:3])]))

			this_net.globals._env['this_net'] = this_net # not safe

			for trans in this_net.transition():
				place_name = list(trans.post.keys())[0] # for function that has only one return value
				place = this_net.place(place_name)
				expr = Expression("this_net.place('%s').tokens.__len__() <= %d" % (place_name, W[place_name]))
				expr.globals.attach(this_net.globals)
				trans.guard = expr
	return StateGraph
