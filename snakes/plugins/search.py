import snakes.plugins
import snakes.nets
from snakes.nets import *

class searchError(Exception):
	def __init__(self, stateGraph):
		self.stateGraph = stateGraph
	def __str__(self):
		return repr('{0}'.format(self.stateGraph.net.name))

class cannotReachError(searchError):
	def __init__(self, stateGraph, end_marking):
		super(cannotReachError, self).__init__(stateGraph)
		self.end_marking = end_marking
	def __str__(self):
		msg = "Marking {0} can't be reached from Marking{1} in Petri net '{2}'".\
			format(self.end_marking, self.stateGraph[0], self.stateGraph.net.name)
		return repr(msg)
		
################## Utility ##################
def weight_of_arc(e):
			if isinstance(e, MultiArc):
				return len(e)
			else:
				return 1

# make the state graph suitable for using net marking as part of the transition guards
# ie., in the namespace of a net, expression of itself is also evaluable
@snakes.plugins.plugin("snakes.nets")
def extend(module):
	class Place(module.Place):
		def max_out(self):
			'''
			find out the maximum outgoing weight
			'''
			if len(self.post) == 0:
				return 0
			return max(map(weight_of_arc, self.post))

	class Transition(module.Transition):
		def is_nonincreasing(self):
			"""check if this transition has non-increasing property, i.e. consuming more tokens
			   than producing, no tokens with new types produced 
			"""
			counts = {}
			for i, arc in self._input.items():
				counts[i.name] = weight_of_arc(arc)
			print(self.name, counts)
			for o, arc in self._output.items():
				if o.name not in counts or counts[o.name] < weight_of_arc(arc):
					return False
			print('hi here')
			return True

	class StateGraph(module.StateGraph):
		def __init__(self, net, aug_graph=None):
			module.StateGraph.__init__(self, net)
			W = {} # the max outgoing weights for places
			# this net will be augmented by clone transitions and fire-restrictions
			this_net = self.net
			# clone transition for each type
			for place in this_net.place():
				t = place.name
				tr = 'clone_' + t
				W[t] = place.max_out() # utility.max_out(place)
				this_net.add_transition(Transition(tr))
				this_net.add_input(t, tr, Variable(t[:3]))
				this_net.add_output(t, tr, MultiArc([Expression(t[:3]), Expression(t[:3])]))
			# let the net be evaluable in the local context itself
			this_net.globals._env['this_net'] = this_net # not safe
			# add guards for transition
			for trans in this_net.transition():
				if trans.is_nonincreasing(): # special case
					continue
				place_name = list(trans.post.keys())[0] # for function that has only one return value
				place = this_net.place(place_name)
				expr = Expression("len(this_net.place('%s').tokens) <= %d" 
					% (place_name, W[place_name]))
				expr.globals.attach(this_net.globals)
				trans.guard = expr
			if aug_graph != None: # gv plugin should be loaded before this module
				# print(aug_graph, type(aug_graph))
				this_net.draw(aug_graph)
			del W

		def build_until(self, end_marking):
			for state in self._build():
				# first time meet it OR first time explore it
				if self.net.get_marking() == end_marking:
				# if self._get_state(end_marking) in self._succ[state]:
					return

		def enumerate_sketch(self, end_marking):
			for route in self._node2node_path(end_marking):
				print('path: {0}'.format(route))
				for sequence in self._edge_enumerate_rec([], route, 1):
					yield sequence

		# give up to write an iterative one
		def _edge_enumerate_rec(self, sequence, path, pos):
			if pos == len(path):
				yield sequence
				return
			for edge in self._succ[path[pos-1]][path[pos]]:
				sequence.append(edge[0].name)
				yield from self._edge_enumerate_rec(sequence, path, pos+1)
				sequence.pop()

		def _node2node_path(self, end_marking):
			'''
			search from the end using backtracking, implemented iteratively
			'''
			end_state = self._get_state(end_marking)
			if end_state == None:
				raise cannotReachError(self, end_marking)
			route = [] # the current backwards route
			node_st = [] # stack for nodes
			branch_st = [] # the top stores the # braches of the current node
			node_st.append(end_state)
			branch_st.append(1)
			while len(node_st) > 0:
				# print('node stack %s' % str(node_st))
				if branch_st[-1] <= 0:
					branch_st.pop()
					route.pop()
					continue
				target = node_st.pop()
				branch_st[-1] -= 1
				# print("pop -> %s" % str(target))
				route.append(target)
				if target == 0:
					path = route.copy()
					path.reverse()
					route.pop()
					yield path
					continue
				pred_list = [p for p in self._pred[target] if p < target]
				# print('predesessor list: %s' % str(pred_list))
				branch_st.append(len(pred_list))
				for pred in pred_list:
					node_st.append(pred)
		# for test
		def _node2node_path_rec(self, end_marking):
			end_state = self._get_state(end_marking)
			if end_state == None:
				raise cannotReachError(self, end_marking)
			self.n2n_helper([end_state])
		def n2n_helper(self, route):
			# print(route)
			target = route[-1]
			if target == 0:
				path = route.copy()
				path.reverse()
				print("path: %s" % path)
				return
			print(target)
			pred_list = [p for p in self._pred[target] if p < target]
			for p in pred_list:
				route.append(p)
				self.n2n_helper(route)
				route.pop()
		# for test

		def construct_a_graph(self):
			'''
			construct a simple reachability graph described as in the paper
			'''
			raise NotImplementedError("to implement")
	return Place, Transition, StateGraph
