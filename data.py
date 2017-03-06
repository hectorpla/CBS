from utility import *
import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

class parseError(Exception):
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return repr(msg)

class Synthesis(object):
	"""An instance of this class conducts a systhesis task for a Target Signature"""
	def __init__(self, sigtr_file):
		sigtr = parse_json(sigtr_file)
		self.targetfunc = TargetFunc(sigtr)
		if self.targetfunc is None:
			raise parseError('format for the target function is incorrect')
		self.net = PetriNet('NET for ' + sigtr['name'])
		dir = sigtr['libdir']
		self.comps = dict(((comp['name'], Component(comp, self.net)) for comp in parse_dir(dir)))
		self.stategraph = None

	def setup(self):
		start_marking = self.targetfunc.get_start_marking()
		end_marking = self.targetfunc.get_end_marking()
		self.stategraph = StateGraph(self.net, 
			start=start_marking, end=end_marking, aug_graph='draws/clone_added.eps')
		self.stategraph.build()

	def inc_len_sketch_enum(self, max_len):
		for seq in self.stategraph.enumerate_sketch_l(max_len):
			print(seq)
			for line in gen_sketch(self.comps, seq):
				print(line)
		print()

	def non_rep_sketch_enum(self):
		"""
		for seq in s.enumerate_sketch():
		print(seq)
		for line in gen_sketch(comps, seq):
			print(line)
		print()
		"""
		raise NotImplementedError()
class Signature(object):
	"""A base class for Component and Target"""
	def __init__(self, sigtr_dict):
		self.name = sigtr_dict['name']
		# (key, value) -> (arg name, arg type)
		self.paras = [(arg, atype) for (arg, atype) in zip(sigtr_dict['paramNames'], sigtr_dict['paramTypes'])] 
		if isinstance(sigtr_dict['tgtTypes'], list):
			self.rtypes = set(sigtr_dict['tgtTypes']) # return types
		else:
			self.rtypes = set([sigtr_dict['tgtTypes']])
		self._in, self._out = self._count_weights(self.paras, self.rtypes)
	def _count_weights(self, paras, rtypes):
		_input = {}
		_output = {}
		for pa, t in self.paras:
			_input[t] = _input.get(t, 0) + 1
		for rt in self.rtypes:
			_output[rt] = _output.get(rt, 0) + 1
		return _input, _output

class TargetFunc(Signature):
	def __init__(self, info):
		super(TargetFunc, self).__init__(info)

	def get_start_marking(self):
		ws = {}
		for i, weight in self._in.items():
			ws[i] = MultiSet(['t'] * weight)
		return Marking(ws)
	def get_end_marking(self):
		ws = {}
		for i, weight in self._out.items():
			ws[i] = MultiSet(['t'] * weight)
		return Marking(ws)
	def output(self):
		"""write out the function definition"""
		raise NotImplementedError("abstract class")
		pass

class Component(Signature):
	"""A function in the specified library"""
	def __init__(self, signature, petri):
		super(Component, self).__init__(signature)
		self.net = petri
		self._add_func()

	def _add_func(self):
		"""add transition to the Petri Net"""
		for place in self._in:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		for place in self._out:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		assert not self.net.has_transition(self.name)
		self.net.add_transition(Transition(self.name))
		for place, weight in self._in.items():
			self.net.add_input(place, self.name, MultiArc([Variable('var')] * weight))
		for place, weight in self._out.items():
			self.net.add_output(place, self.name, MultiArc([Variable('var')] * weight))

	def sketch(self, var_gen, hole_counter):
		sk = "let " + next(var_gen) + " = "
		if self.name in ['^']:
			assert len(self.paras) == 2
			sk += '(' + self.name + ')'
			# sk += '#' + str(next(hole_counter)) + ' ^ #' + str(next(hole_counter))
		else:
			sk += self.name
		for pa, t in self.paras:
			sk += ' #' + str(next(hole_counter)) + '(' + t + ')'
		return sk		

class Sketch(object):
	"""data structure for a code sketch in purpose to solve in SAT solver"""
	def __init__(self, arg):
		self.arg = arg
		