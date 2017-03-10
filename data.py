from utility import *
import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *
import z3

DEBUG = True

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

	def _gen_sketch(self, sequence):
		counter = itertools.count(0)
		var_gen = var_generator()
		sketch = []
		sketch_ads = Sketch()
		sketch.append(self.targetfunc.sigtr_sketch())
		sketch_ads.add_signature(self.targetfunc)
		for f in sequence:
			if f.startswith('clone_'): # watchout: mind the name confilction 
				continue
			toprint, skline = self.comps[f].sketch(var_gen, counter) # sketch() return a tuple
			sketch.append('\t' + (toprint) + ' in')
			sketch_ads.add_line(skline)
			print('    ' + str(skline))
		return_holes = [next(counter) for _ in range(self.targetfunc.output_len())]
		sketch.append('in #' + ', '.join(map(str, return_holes)))
		sketch_ads.add_return_line(self.targetfunc, return_holes)
		sketch_ads.enum_subst()
		return sketch

	def inc_len_sketch_enum(self, max_len):
		for seq in self.stategraph.enumerate_sketch_l(max_len):
			print(seq)
			for line in self._gen_sketch(seq):
				print(line)
			print()
		print()

	def non_rep_sketch_enum(self):
		"""
		for seq in s.enumerate_sketch():
		print(seq)
		for line in gen_sketch(comps, seq):
			print(line)
		print()
		"""
		raise NotImplementedError('not yet implemented')

	def sketch_completion(self, sketch):
		assert isinstance(sketch, Sketch)
		sketch.enum_subst()
	def stat(self):
		"""show statistics after synthesis"""
		raise NotImplementedError('not yet implemented')
class Signature(object):
	"""A base class for Component and Target"""
	def __init__(self, sigtr_dict):
		self.name = sigtr_dict['name']
		assert len(sigtr_dict['paramNames']) == len(sigtr_dict['paramTypes'])
		# (key, value) -> (arg name, arg type)
		self.paras = [(arg, atype) for (arg, atype) in zip(sigtr_dict['paramNames'], sigtr_dict['paramTypes'])] 
		if isinstance(sigtr_dict['tgtTypes'], list):
			self.rtypes = sigtr_dict['tgtTypes'] # return types
		else:
			self.rtypes = [sigtr_dict['tgtTypes']]
		self._in, self._out = self._count_weights(self.paras, self.rtypes)
	def _count_weights(self, paras, rtypes):
		_input = {}
		_output = {}
		for pa, t in self.paras:
			_input[t] = _input.get(t, 0) + 1
		for rt in self.rtypes:
			_output[rt] = _output.get(rt, 0) + 1
		return _input, _output
	def input_len(self):
		return len(self.paras)
	def output_len(self):
		return len(self.rtypes)

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
	def sigtr_sketch(self):
		"""write out the function definition"""
		return 'let ' + self.name + ' ' + comma_join(self.paras) + ' ='

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
		'''
		outline the component function, in string form as well as abstract form(holes, variables)
		'''
		holes = []
		variables = [(next(var_gen), self.rtypes[i]) for i in range(len(self.rtypes))]
		sk = "let "
		sk += comma_join(variables)
		sk +=" = "
		if self.name in ['^']:
			assert len(self.paras) == 2
			self.name = '(' + self.name + ')'
		sk += self.name
		for pa, t in self.paras:
			hole_num = next(hole_counter)
			holes.append((hole_num, t))
			sk += ' #' + str(hole_num) + '(' + t + ')'
		return sk, SketchLine(holes, variables)

class SketchLine(object):
	'''An abstract data structure for a line of sketch(semantic of a line)'''
	def __init__(self, holes, variables):
		self._holes = holes # list of (hole#, type)
		self._vars = variables # list of (var_name, type)
	def __str__(self):
		return '(holes: ' + str(self._holes) + ', vars: ' + str(self._vars) + ')'
	def holes(self):
		return (hole for hole in self._holes)
	def variables(self):
		return (var for var in self._vars)

class Sketch(object):
	"""data structure for a code sketch in purpose to complete in SAT solver"""
	def __init__(self):
		self.type_vars = {} # each bucket stores the variables having the same type
		self.type_holes = {} # each bucket contains places
		self.var_holes = {} # each bucket(keyed with variable) contains candidate places
		self.hole_vars = {} # each bucket contains variables
		self.s = z3.Solver()
		self.hypos = {}
	def _vars(self):
		for typing in self.type_vars:
			for var in self.type_vars[typing]:
				yield (var, typing)
	def _hypos(self):
		for hole_cands in self.hypos.values():
			for hyp in hole_cands.values():
				yield hyp
	def add_signature(self, sigtr):
		'''Simply add parameters(variables) into types, and set up variable constraints frame'''
		assert isinstance(sigtr, Signature)
		for name, typing in sigtr.paras:
			if typing not in self.type_holes:
				self.type_vars[typing] = set()
			self.type_vars[typing].add(name)
			self.var_holes[name] = set()
		# print('Sketch.add_signature: ')
		# print('type_holes ' + str(self.type_holes))

	def add_line(self, line):
		'''
		A Synthesis instance use it: when encountering every hole, find all candidate variables
		that will be filled here; at the same time, append holes to type-buckets
		'''
		assert isinstance(line, SketchLine)
		for hole, typing in line.holes():
			self.hole_vars[hole] = self.type_vars[typing].copy() # shallow copy
			if typing not in self.type_holes:
				self.type_holes[typing] = set()
			self.type_holes[typing].add(hole)
		for var, typing in line.variables():
			if typing not in self.type_vars:
				self.type_vars[typing] = set()
			self.type_vars[typing].add(var)

	def add_return_line(self, sigtr, holes):
		"""add the returning holes"""
		assert isinstance(sigtr, Signature)
		for hole, typing in zip(holes, sigtr.rtypes):
			self.hole_vars[hole] = self.type_vars[typing].copy()
			if typing not in self.type_holes:
				self.type_holes[typing] = set()
			self.type_holes[typing].add(hole)

	def _add_var_cands(self):
		''' 
		After adding all lines(including signature and return statement), 
		only hole constraints are set; variable constraints are added here
		'''
		for var, typing in self._vars():
			self.var_holes[var] = set()
			candiate_holes = (hole for hole in self.type_holes[typing] if var in self.hole_vars[hole])
			self.var_holes[var].update(candiate_holes)

	def _set_up_constraints(self):
		'''set up constraint for each hole and variable respectively'''
		for hole in self.hole_vars:
			self.hypos[hole] = {}
			for var in self.hole_vars[hole]:
				self.hypos[hole][var] = z3.Bool(hypo_var_gen(hole, var))
			vcandlist = list(self.hypos[hole].values())
			print('HOLE CONSTRAINTS LIST: ' + str(vcandlist))
			self.s.add(z3.AtMost(vcandlist + [1])) # all add up to 0 or 1
			self.s.add(z3.Or(vcandlist))

		for var in self.var_holes:
			hcandlist = list(self.hypos[hole][var] for hole in self.var_holes[var])
			print('VAR CONSTRAINTS LIST ' + str(hcandlist))
			self.s.add(z3.AtLeast(hcandlist + [1]))
	
	def _process_model(self):
		m = self.s.model()
		block = []
		for hyp in self._hypos():
			if z3.is_true(m.eval(hyp)):
				block.append(hyp)
		self.s.add(z3.Not(z3.And(block)))
		return m

	def enum_subst(self):
		'''enumerate possible completions of the code sketch'''
		self._add_var_cands()
		self._set_up_constraints()
		if DEBUG:
			print('Sketch.enum_subst: ')
			print('type_vars: ' + str(self.type_vars))
			print('type_holes: ' + str(self.type_holes))
			print('hole_vars: ' + str(self.hole_vars))
			print('var_holes: ' + str(self.var_holes))
			print()
		while z3.sat == self.s.check():
			print('  -----',end='')
			print(self._process_model())

	def gen_hypothesis(self):
		pass
