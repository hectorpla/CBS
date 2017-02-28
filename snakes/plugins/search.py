import snakes.plugins
import snakes.nets
from snakes.nets import *
from collections import deque

class searchError(Exception):
	def __init__(self, stateGraph, msg=None):
		self.stateGraph = stateGraph
		self.msg = msg
	def __str__(self):
		return repr('{0} -> {1}'.format(self.stateGraph.net.name, self.msg))

class cannotReachError(searchError):
	def __init__(self, stateGraph, end_marking):
		super(cannotReachError, self).__init__(stateGraph)
		self.end_marking = self.end_marking
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
			for o, arc in self._output.items():
				if o.name not in counts or counts[o.name] < weight_of_arc(arc):
					return False
			return True
		def reachable_maps(self):
			'''product of input places and output places'''
			reachables = {}
			for o in self._output:
				reachables[o.name] = set([i.name for i in self._input])
			return reachables

	class PetriNet(module.PetriNet):
		def reachables_places(self, targets):
			reachables = set()
			if isinstance(targets, list):
				for t in targets:
					reachables |= self._reachable_places(t)
			else:
				reachables = _reachable_places(targets)
			return reachables

		def _reachable_places(self, target):
			'''
			In alpha(N) return all nodes that all backwards reachable from the target types
			from the target places
			'''
			graph = self._construct_alpha_graph()
			reachables = set()
			q = deque([])
			q.append(target)
			while len(q) > 0:
				place = q.popleft()
				reachables.add(place)
				for src in graph[target]:
					if src not in reachables:
						q.append(src)
			return reachables
		def _construct_alpha_graph(self):
			'''
			construct the simple reachability graph described as in the paper
			'''
			graph = {}
			for tran in self._trans.values():
				m = tran.reachable_maps()
				for out, ins in m.items():
					if out not in graph:
						graph[out] = ins
					else:
						graph[out] |= ins
			return graph

	class StateGraph(module.StateGraph):
		def __init__(self, net, end=None, start=None, aug_graph=None):
			module.StateGraph.__init__(self, net)
			W = {} # the max outgoing weights for places
			# this net will be augmented by clone transitions and fire-restrictions
			this_net = self.net
			if end is None:
				raise searchError(self, "end marking not specified")
			self.end_marking = end
			if start != None:
				this_net.set_marking(start)
			# clone transition for each type
			for place in this_net.place():
				t = place.name
				tr = 'clone_' + t
				W[t] = place.max_out() # utility.max_out(place)
				this_net.add_transition(Transition(tr))
				this_net.add_input(t, tr, Variable(t[:3]))
				this_net.add_output(t, tr, MultiArc([Expression(t[:3]), Expression(t[:3])]))
			# find all places that can be backwards reachable from the end marking
			useful_places = self._useful_places()
			print("####Useful places:", useful_places)
			# let the net be evaluable in the local context itself
			this_net.globals._env['this_net'] = this_net # not safe
			# add guards for transition
			for trans in this_net.transition():
				unuseful = (not (place in useful_places) for place in trans.post.keys())
				if all(unuseful): # prune unecessary places for tokens to go
					trans.guard = Expression("False")
					continue
				if trans.is_nonincreasing(): # special case
					continue
				# for function that has only one return value, !need! to be extended
				place_name = list(trans.post.keys())[0] 
				place = this_net.place(place_name)
				expr = Expression("len(this_net.place('%s').tokens) <= %d" 
					% (place_name, W[place_name]))
				expr.globals.attach(this_net.globals)
				trans.guard = expr
			if aug_graph != None: # gv plugin should be loaded before this module
				this_net.draw(aug_graph)
			del W

		def _useful_places(self):
			targets = []
			for place in self.end_marking:
				targets.append(place)
			return self.net.reachables_places(targets)

		def build_until(self):
			for state in self._build():
				# first time meet it OR first time explore it
				if self.net.get_marking() == self.end_marking:
				# if self._get_state(self.end_marking) in self._succ[state]:
					return

		def enumerate_sketch(self):
			for route in self._node2node_path():
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

		def _node2node_path(self):
			'''
			search from the end using backtracking, implemented iteratively
			'''
			end_state = self._get_state(self.end_marking)
			if end_state == None:
				raise cannotReachError(self, self.end_marking) # !to modify
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
				if target == 0: # issue: 0 -> 0 self cycle
					path = route.copy()
					path.reverse()
					route.pop()
					yield path
					continue
				pred_list = [p for p in self._pred[target] if p not in route] # linear search
				# print('predesessor list: %s' % str(pred_list))
				branch_st.append(len(pred_list))
				for pred in pred_list:
					node_st.append(pred)
		# for test
		def _node2node_path_rec(self):
			end_state = self._get_state(self.end_marking)
			if end_state == None:
				raise cannotReachError(self, self.end_marking)
			self.n2n_helper([end_state])
		def n2n_helper(self, route):
			target = route[-1]
			if target == 0:
				path = route.copy()
				path.reverse()
				print("path: %s" % path)
				return
			pred_list = [p for p in self._pred[target] if p < target] # unsynced with iterative
			for p in pred_list:
				route.append(p)
				self.n2n_helper(route)
				route.pop()
		# for test

		def _iter_deepening(self, max_depth):
			"""search for path with iter""" 
			pass
	return Place, Transition, PetriNet, StateGraph
