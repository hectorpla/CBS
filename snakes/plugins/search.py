import snakes.plugins
import utility
import snakes.nets
from snakes.nets import *

# make the state graph suitable for using net marking as part of the transition guards
# ie., in the namespace of a net, expression of itself is also evaluable
@snakes.plugins.plugin("snakes.nets")
def extend(module):
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

		# def _edge_path(self, end_marking):
		# 	for path in self._node2node_path(end_marking): # yet another yield
		# 		sequence = [] # edges sequence up to now
		# 		edge_st = [t for t in self._succ[path[0]][path[1]]]
		# 		while len(edge_st) > 0:

		def _edge_enumerate_rec(self, sequence, path, pos):
			# print('  ' + str(sequence))
			if pos == len(path) - 1:
				yield sequence
				return
			# print('  ' + str(self._succ[path[pos-1]][path[pos]]))
			for edge in self._succ[path[pos-1]][path[pos]]:
				sequence.append((edge[0].name, edge[1]))
				yield from self._edge_enumerate_rec(sequence, path, pos+1)
				sequence.pop()


		def _node2node_path(self, end_marking):
			'''
			search from the end using backtracking, implemented iteratively
			'''
			route = [] # the current backwards route
			node_st = [] # stack for nodes
			branch_st = [] # the top stores the # braches of the current node
			end_state = self._get_state(end_marking)
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
			self.n2n_helper([end_state])
		def n2n_helper(self, route):
			# print(route)
			target = route[-1]
			if target == 0:
				path = route.copy()
				path.reverse()
				print("path: %s" % path)
				return
			pred_list = [p for p in self._pred[target] if p < target]
			for p in pred_list:
				route.append(p)
				self.n2n_helper(route)
				route.pop()
		# for test


	return StateGraph
