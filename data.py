import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

class Synthesis():
	"""An instance of this class conducts a systhesis task for a Target Signature"""
	def __init__(self):
	 	pass

class Signature(object):
	"""A base class for Component and Target"""
	def __init__(self, sig_dict):
		self.name = sig_dict['name']
		# (key, value) -> (arg name, arg type)
		self.paras = [(arg, atype) for (arg, atype) in zip(sig_dict['paramNames'], sig_dict['paramTypes'])] 
		if isinstance(sig_dict['tgtTypes'], list):
			self.rtypes = set(sig_dict['tgtTypes']) # return types
		else:
			self.rtypes = set([sig_dict['tgtTypes']])
		# initialize the two members
		self._in, self._out = self._count_weights(self.paras, self.rtypes)
	def _count_weights(self, paras, rtypes):
		_input = {}
		_output = {}
		for pa, t in self.paras:
			_input[t] = _input.get(t, 0) + 1
		for rt in self.rtypes:
			_output[rt] = _output.get(rt, 0) + 1
		return _input, _output
	def parse(self): 
		pass

class TargetFunc(Signature):
	def __init__(self, info):
		self.name = info['name']

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
		