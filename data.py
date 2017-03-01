import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

# class Parameters():
# 	"""parse the parameters of a function into specified data structure"""
# 	pass

class Signature(object):
	"""A base class for Component and Target"""
	def __init__(self):
		raise NotImplementedError("abstract class")
	def parse(self): 
		pass
class TargetFunc(Signature):
	def __init__(self):
		self.name = ""
		self.net = PetriNet(self.name)
	def output(self):
		"""write out the function definition"""
		pass

class Component(Signature):
	"""A function in the specified library"""
	def __init__(self, signature, petri):
		self.name = signature['name']
		self.net = petri
		# (key, value) -> (arg name, arg type)
		self.paras = [(arg, atype) for (arg, atype) in zip(signature['paramNames'], signature['paramTypes'])] 
		if isinstance(signature['tgtTypes'], list):
			self.rtypes = set(signature['tgtTypes']) # return types
		else:
			self.rtypes = set([signature['tgtTypes']])
		# initialize the two members
		self._in, self._out = self._count_weights(self.paras, self.rtypes)
		self._add_func()

	def _add_func(self):
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

	def _count_weights(self, paras, rtypes):
		_input = {}
		_output = {}
		for pa, t in self.paras:
			_input[t] = _input.get(t, 0) + 1
		for rt in self.rtypes:
			_output[rt] = _output.get(rt, 0) + 1
		return _input, _output

	def sketch(self, var_gen, hole_counter):
		sk = "let " + next(var_gen) + " = " + self.name
		for pa, t in self.paras:
			sk += ' #' + str(next(hole_counter)) + '(' + t + ')'
		return sk
	