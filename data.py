import snakes.nets
from snakes.nets import *

class Parameters():
	"""parse the parameters of a function into specified data structure"""
	pass

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
	def __init__(self, signature, petri): # data structure to pass in: file handler or a python object?
		self.name = signature['name']
		self.net = petri
		# (key, value) -> (arg name, arg type)
		self.paras = [(arg, atype) in zip(signature['paramNames'], signature['parasTypes'])] 
		self.rtypes = set(signature['tgtTypes']) # return types
		# initialize the two members
		self._in, self._out = self._count_weights(paras, rtypes)
		self._add_func()

	def _add_func(self):
		for place in self._in:
			if not self.net.has_place(place):
				self.net.add_node(place)
		for place in rtypes:
			if not self.net.has_place(place):
				self.net.add_node(place)
		assert not self.net.has_transition(self.name)
		_trans = Transition(self.name)
		self.net.add_transition(_trans)
		for place, weight in self._in.items():
			self.net.add_input(place, _trans, MultiArc([Variable('t')] * weight))
		for place, weight in self._out.items():
			self.net.add_output(place, _trans, MultiArc([Variable('t')] * weight))

	def _count_weights(self, paras, rtypes):
		_input = {}
		_output = {}
		for pa, t in self.paras:
			_input[t] = _input.get(t, 0) + 1
		for rt in self.rtypes.items():
			_output[t] = _output[t] + 1
		return _input, _output

	def sketch(self):
		sk = self.name
		for pa, t in self.paras:
			sk += ' #' + t
		return sk
	