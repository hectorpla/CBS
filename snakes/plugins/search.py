import snakes.plugins
import snakes.nets
from snakes.nets import *
from collections import deque
import heapq
import time

class searchError(Exception):
	def __init__(self, stateGraph, msg=None):
		self.stateGraph = stateGraph
		self.msg = msg
	def __str__(self):
		return repr('{0} -> {1}'.format(self.stateGraph.net.name, self.msg))
class CannotReachErrorr(searchError):
	def __init__(self, stateGraph):
		super(CannotReachErrorr, self).__init__(stateGraph)
	def __str__(self):
		msg = "Marking {0} can't be reached from Marking{1} in Petri net '{2}'".\
			format(self.stateGraph.end_marking, self.stateGraph[0], self.stateGraph.net.name)
		return repr(msg)

################## Utility ##################
def weight_of_arc(e):
	assert isinstance(e, MultiArc)
	return len(e)

# make the state graph suitable for using net marking as part of the transition guards
# ie., in the namespace of a net, expression of itself is also evaluable
@snakes.plugins.plugin("snakes.nets")
def extend(module):
	class Place(module.Place):
		def max_out(self):
			''' find out the maximum outgoing weight '''
			if len(self.post) == 0:
				return 0
			return max(map(weight_of_arc, self.post.values()))

	class Transition(module.Transition):
		def is_nonincreasing(self):
			"""
			check if this transition has non-increasing property, i.e. consuming more tokens
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
			graph = self.construct_alpha_graph()
			reachables = set()
			q = deque([])
			q.append(target)
			while len(q) > 0:
				place = q.popleft()
				reachables.add(place)
				for src in graph[place]:
					if src not in reachables:
						q.append(src)
			return reachables
		def construct_alpha_graph(self):
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
		def __init__(self, net, start, end):
			''' the according Petri net will be augmented by clone transitions and fire-restrictions '''
			assert isinstance(start, Marking)
			assert end is not None
			old = net.get_marking()
			net.set_marking(start) # < tricky construct for stategraph
			module.StateGraph.__init__(self, net) # a new petri net is created inside
			net.set_marking(old) # > make net clean again
			assert self[0] == start
			self.end_marking = end
			self._add_clones()
			
			self.net.globals._env['this_net'] = self.net # let the net be evaluable in the local context itself, not safe
			self._prepare_net()
			self.steps_explored = 0 # indicate the how many times we have explore state in state graph
			# print('----state graph created----')
		def _prepare_net(self):
			''' set guards for transition and take care of the special place "unit" '''
			W = dict((place.name, place.max_out()) for place in self.net.place()) # the max outgoing weights for places
			# print('~~~ Maximum Outgoing Weight', W)
			self.useful_places = self._useful_places() # find all places that can be backwards reachable from the end marking
			print("~~~~~~~~~~~~~Useful places:", self.useful_places, "~~~~~~~~~~~~~")
			self._set_fire_restrictions(W, self.useful_places) # add guards for transition
			# preventing generating tokens in unit place: remove all the ingoing edges to unit
			# maybe not a good solution!!!
			if self.net.has_place('unit'):
				for tran in self.net.pre('unit'):
					self.net.remove_output('unit', tran)
		def _add_clones(self):
			for place in self.net.place(): # clone transition for each type
				t = place.name
				tr = 'clone_' + t
				self.net.add_transition(Transition(tr))
				self.net.add_input(t, tr, MultiArc([Variable('cl')]))
				self.net.add_output(t, tr, MultiArc([Expression('cl'), Expression('cl')]))
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

		def build_by_step(self):
			''' explore new states from the todo list(frointer) '''
			n = len(self._todo)
			for _ in range(n):
				state = self._todo.pop(0)
				self._compute(state)
			self.steps_explored += 1

		def get_state(self, marking):
			isinstance(marking, Marking)
			return self._state[marking]

		def enumerate_sketch_l(self, stmrk=None, max_depth=10, func_prio=None):
			""" yet another generator warpping another, called by synthesis to enumerate sketches incly """
			start_state = self.get_state(stmrk)
			print('enumerate_sketch_l: start state -> ', start_state)
			def enum(l):
				return self.enumerate_sketch(start_state, l) if func_prio is None else\
			 			self._edge_enum_with_prio(start_state, l, func_prio)
			# length-increasing style
			# for length in range(2, max_depth+2):
			# 	print("^^^length", length)
			# 	yield from enum(length)

			# round-robin style
			enumerators = deque([(l, enum(l)) for l in range(2, max_depth+2)]) 
			while len(enumerators) > 0:
				l, enumerator = enumerators.popleft()
				print('^^^length', l)
				for _ in range(100):
					try:
						yield next(enumerator)
					except StopIteration:
						break
				else:
					enumerators.append((l,enumerator))

		def enumerate_sketch(self, start_state, depth=float('inf')):
			""" list all possible transition paths from all state paths, given the # of steps(depth) """
			for route in self._node2node_path(start_state, depth):
				print('path: {0}'.format(route))
				# print('marking:', list(map(lambda x: self[x], route)))
				for sequence in self._edge_enumerate_rec([], route, 1):
					yield sequence

		# give up to write an iterative one
		def _edge_enumerate_rec(self, sequence, path, pos):
			"""given a node path, return cross product of all steps"""
			if pos == len(path):
				yield sequence
				return
			arc = (path[pos-1], path[pos])
			for edge in self._succ[path[pos-1]][path[pos]]:
				sequence.append(edge[0].name)
				yield from self._edge_enumerate_rec(sequence, path, pos + 1)
				sequence.pop()
		
		def _prepare_graph(self, pathlen):
			''' explore state graph until '''
			while self.steps_explored < pathlen:
				if len(self._todo) == 0:
					return
				self.build_by_step()
		def _node2node_path(self, start_state, depth=float('inf')):
			''' search from the end using backtracking, implemented iteratively '''
			self._prepare_graph(depth-1)
			end_state = self._get_state(self.end_marking)
			if end_state == None:
				raise CannotReachErrorr(self)
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
					if target == start_state: # issue: 0 -> 0 self cycle for infinite depth case
						path = route.copy()
						path.reverse()
						yield path
					route.pop()
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
				raise CannotReachErrorr(self, self.end_marking)
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

		# sketch enum by ranking
		def _all_edges_to(self, state):
			''' return all in-coming edges from the state, paired with source state '''
			ename = lambda t : t[0].name # extract edge name from a (transition, subsitution) tuple
			res =  [(ename(edge), dest) for dest, edges in self._pred[state].items() for edge in edges]
			return res
		def _edge_enum_with_prio(self, start_state, max_depth, scores):
			''' combine the node enum and edge enum phase, 
				algo improvement: for mutiple edges, reachable paths should be stored '''
			self._prepare_graph(max_depth-1)
			end_state = self._get_state(self.end_marking)
			if end_state == None:
				raise CannotReachErrorr(self)
			path = []
			edge_stack = self._all_edges_to(end_state)
			branch_stack = [len(edge_stack)]
			paths = []
			prio_stack = [1]
			def do_pop():
				path.pop()
				prio_stack.pop()
			def get_score(func_name):
				temp = [""]
				temp.extend(func_name.split('.'))
				module, name = temp[-2], temp[-1]
				try:
					ret = scores[module][name]
				except KeyError:
					ret = 0.05
				return ret
			def yield_all_existing():
				print('# PATHS:', len(paths), '|', paths)
				while len(paths) > 0: # yield sequences in by ranking
					_, path = heapq.heappop(paths)
					yield path
			timer = time.clock()
			nodes_exp = 0
			while len(edge_stack) > 0: # the core part of path enumeration
				if branch_stack[-1] <= 0:
					do_pop()
					branch_stack.pop()
					continue
				edge, target = edge_stack.pop()
				nodes_exp += 1
				branch_stack[-1] -= 1
				path.append(edge)
				fac = 1 / get_score(edge)
				prio_stack.append(prio_stack[-1] * fac)
				if len(path) == max_depth - 1:
					if target == start_state:
						heapq.heappush(paths, (prio_stack[-1], list(reversed(path))))
						print('{0}...\t\tnodes explored: {1}\t\t{2:.6g}s ellapsed'.format(len(paths), 
							nodes_exp, time.clock() - timer))
						timer = time.clock()
						nodes_exp = 0
						if len(paths) >= 100: # tentative
							yield from yield_all_existing()
					do_pop()
					continue
				edge_list = self._all_edges_to(target)
				edge_stack.extend(edge_list)
				branch_stack.append(len(edge_list))

			yield from yield_all_existing()

		def num_states_exlore(self):
			return len(self._done)

	return Place, Transition, PetriNet, StateGraph
