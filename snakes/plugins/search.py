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

		def dists_in_alpha(self, n, target):
			raise  NotImplementedError("Not yet implemented")

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
			assert start is not None
			assert end is not None
			old = net.get_marking()
			net.set_marking(start) # < tricky construct for stategraph
			module.StateGraph.__init__(self, net) # a new petri net is created here
			# this net will be augmented by clone transitions and fire-restrictions
			net.set_marking(old) # > make net clean again
			self.end_marking = end
			self._add_clones()
			# the max outgoing weights for places
			W = dict((place.name, place.max_out()) for place in self.net.place())
			# find all places that can be backwards reachable from the end marking
			useful_places = self._useful_places()
			print("~~~~~~~~~~~~~Useful places:", useful_places, "~~~~~~~~~~~~~")
			# let the net be evaluable in the local context itself, not safe
			self.net.globals._env['this_net'] = self.net
			# add guards for transition
			self._set_fire_restrictions(W, useful_places)
			# preventing generating tokens in unit place: remove all the ingoing edges to unit
			# maybe not a good solution!!!
			if self.net.has_place('unit'):
				for tran in self.net.pre('unit'):
					self.net.remove_output('unit', tran)
			if aug_graph != None: # gv plugin should be loaded before this module
				self.net.draw(aug_graph)
			del W
		def _add_clones(self):
			for place in self.net.place(): # clone transition for each type
				t = place.name
				tr = 'clone_' + t
				self.net.add_transition(Transition(tr))
				self.net.add_input(t, tr, Variable(t[:3]))
				self.net.add_output(t, tr, MultiArc([Expression(t[:3]), Expression(t[:3])]))
		def _useful_places(self):
			targets = []
			for place in self.end_marking:
				targets.append(place)
			# functions with unit return type allowed, logic hidden to user
			# this modification, along with ruling out ingoings to place "unit" causes
			# non-determination of drawing the state graph
			if self.net.has_place('unit'): 
				targets.append('unit')
			return self.net.reachables_places(targets)
		def _set_fire_restrictions(self, W, useful_places):
			for trans in self.net.transition():
				unuseful = (not (place in useful_places) for place in trans.post.keys())
				if all(unuseful): # prune unecessary places for tokens to go
					trans.guard = Expression("False")
					continue
				if trans.is_nonincreasing(): # special case
					continue
				# for function that has only one return value, !need! to be extended
				place_name = list(trans.post.keys())[0] 
				place = self.net.place(place_name)
				expr = Expression("len(this_net.place('%s').tokens) <= %d" 
					% (place_name, W[place_name]))
				expr.globals.attach(self.net.globals)
				trans.guard = expr

		def build_until(self):
			for state in self._build():
				# first time meet it OR first time explore it
				if self.net.get_marking() == self.end_marking:
				# if self._get_state(self.end_marking) in self._succ[state]:
					return

		def enumerate_sketch_l(self, max_depth=10):
			"""yet another generator warpping another"""
			for length in range(2, max_depth+2):
				print("^^^length", length)
				yield from self.enumerate_sketch(length)

		def enumerate_sketch(self, depth=float('inf')): # bad pattern?: used internally and externally
			"""list all possible transition paths from all state paths"""
			for route in self._node2node_path(depth):
				print('path: {0}'.format(route))
				for sequence in self._edge_enumerate_rec([], route, 1):
					yield sequence

		# give up to write an iterative one
		def _edge_enumerate_rec(self, sequence, path, pos):
			"""given a node path, return cross product of all steps"""
			if pos == len(path):
				yield sequence
				return
			arc = (path[pos-1], path[pos])
			try:
				next_diff = next(i for i in range(pos + 1, len(path)) if (path[i-1], path[i]) != arc)
			except StopIteration:
				next_diff = len(path)
			candidate = self._succ[path[pos-1]][path[pos]].copy() # dynamically changing set
			pool = list(candidate)
			yield from self._edge_enum_helper(sequence, path, pos, pos, next_diff, candidate)

		def _edge_enum_helper(self, sequence, path, rep_start, pos, next_diff, candidate):
			"""helper for _edge_enumerate_rec to prevent listing replicate paths"""
			if pos == next_diff:
				yield from self._edge_enumerate_rec(sequence, path, next_diff)
				return
			if len(candidate) == 0:
				return
			pool = list(candidate)
			repeat = next_diff - pos
			# print(sequence)
			for edge in pool:
				candidate.remove(edge)
				sequence.extend([edge[0].name] * repeat) # tuple in entries: (transition, substitution)
				for d in range(0, repeat):
					yield from self._edge_enum_helper(sequence, path, rep_start, next_diff-d, next_diff, candidate)
					sequence.pop()
				if pos > rep_start: candidate.add(edge)
			
		def _node2node_path(self, depth=float('inf')):
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
				if len(route) == depth or depth == float('inf'): # ugly: logic fallable
					if target == 0: # issue: 0 -> 0 self cycle for infinite depth case
						path = route.copy()
						path.reverse()
						route.pop()
						yield path
						continue
					if len(route) == depth:
						# print('specified depth reached: {0}'.format(depth))
						route.pop() #
						continue
				if depth == float('inf'):
					pred_list = [p for p in self._pred[target] if p not in route] # linear search
				else:
					pred_list = [p for p in self._pred[target]]
				branch_st.append(len(pred_list))
				node_st.extend(pred_list)
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

	return Place, Transition, PetriNet, StateGraph
