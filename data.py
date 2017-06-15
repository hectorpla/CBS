from utility import *
import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

import copy
import z3
import subprocess
import time

class ConstraintError(Exception):
	def __init__(self, msg=None):
		self.msg = msg
	def __str__(self):
		return repr(msg)

PRIMITIVE_TYPES = ['bool', 'int', 'char', 'string']

DEBUG = False
PAUSE = False

class parseError(Exception):
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return repr(msg)

class IOWeightObject(object):
	def __init__(self):
		raise NotImplementedError('abstract class IOWeightObject')
		self.paras = None # supposed to be [(arg0, type0) ...]
		self.rtypes = None # [type0, type1]
		self._in, self._out = None, None # both {type0:weight0, type1:weight1 ...}
	def _in_weights(self):
		return self._count_weights(map(second_elem_of_tuple, self.paras))
	def _out_weight(self):
		return self._count_weights(self.rtypes)
	def _count_weights(self, typelist):
		w = {}
		for t in typelist:
			w[t] = w.get(t, 0) + 1
		return w
	def paras_list(self):
		return list(map(first_elem_of_tuple, self.paras))
	def params_of_type(self, t):
		return list(para for para, typing in self.paras if typing == t)

brch_counter = itertools.count(1) # temperialy use it
class Branch(IOWeightObject):
	def __init__(self, sigtr, brchbef, brchargs, brchtype='list'):
		''' class for a branch of pattern matching
			brch arg example: 
			in |hd::tl -> ..., hd and tl are branch argument for this branch
		'''
		assert isinstance(sigtr, Signature) # a branch is derived from a function signature
		assert isinstance(brchbef, tuple) and len(brchbef) == 2 # example (arg0, int list)
		if brchtype != 'list':
			raise NotImplementedError('data structure other than list pattern matching not considered') 
		
		self._brchbef = brchbef
		self.brchtype = brchtype
		self.brch_id = next(brch_counter)

		self.sigtr = sigtr
		self.paras = brchargs
		self._allvars = self._all_variables()
		self._in = self._count_weights(self._symbol_types(self.paras)) # params in the branch line
		# self._out = sigtr._out # bad pattern? member access between siblings
		self._allin = self._count_weights(map(second_elem_of_tuple, self._allvars)) # params in sigtr line and in brch line

		self.matchline = 'match ' + self._brchbef[0] + ' with'
		self.start_marking = self.original_marking()
		self._variables = self._allvars # variables list that changes along with enumeration
	def get_start_marking(self):
		return self.start_marking
	def _branch_marking(self, sigtr, ctype):
		''' bad. copy & paste, should change  (now for verification)'''
		ws = {}
		for i, weight in self._in.items():
			ws[i] = MultiSet(['t'] * weight)
		return Marking(ws) + (sigtr.get_start_marking() - Marking({ctype:MultiSet(['t'])}))
	def original_marking(self):
		ws = {}
		for i, weight in self._allin.items():
			ws[i] = MultiSet(['t'] * weight)
		orgmrk = Marking(ws)
		assert orgmrk == self._branch_marking(self.sigtr, self._brchbef[1])
		return orgmrk
	def sketch(self):
		if self.brchtype == 'list':
			if len(self.paras) == 0:
				return '|[] ->'
			return '|' + '::'.join(self.paras_list()) + ' ->'
		raise NotImplementedError('other cases')
	def __str__(self):
		'''for debug'''
		return self.sketch()
	def _all_variables(self):
		'''all variables: arguments in the signature - decomposed variable + new variables generated'''
		compound = self.sigtr.paras + self._symbol_args_types(self.paras)
		compound.remove(self._brchbef)
		return compound
	def brch_variables(self):
		'''return the non-wildcard arguments in pattern line, called by Sketch'''
		return self._symbol_args_types(self.paras)
	def variables(self):
		'''make Branch act as a SketchLine'''
		return iter(self._variables)
	def holes(self):
		''' like a signature, a branch line doesn't have any hole to fill in  '''
		return []
	def _symbol_args_types(self, rawparam, func=lambda x : x):
		''' return the list of vars of types (can be repeated) not having _ as variable name'''
		return [func(p) for p in rawparam if p[0] != '_']
	def _symbol_args(self, rawparam):
		return self._symbol_args_types(rawparam, first_elem_of_tuple)
	def _symbol_types(self, rawparam):
		return self._symbol_args_types(rawparam, second_elem_of_tuple)
	def id_func_variables(self):
		''' picking from _all_variables '''
		tgttype = self.sigtr.rtypes[0]
		targetArgs = self.params_of_type(tgttype)
		return self.sigtr.id_func_variables() + list(filter(lambda x: x != '_', targetArgs))
	def _single_tok_marking(self, typelist):
		''' idempotent in terms of binding values to a single key '''
		return Marking(dict(zip(typelist, itertools.repeat(MultiSet(['t'])))))
	def sub_start_marking(self):
		''' yield the subset of the branch's start marking, each place only having one token
			taking one type away at at time
		'''
		places = list(self.start_marking.keys())
		full_marking = self._single_tok_marking(places)
		removables = list(set(places) - set(map(second_elem_of_tuple, self.paras)))
		print(removables)
		for l in range(1, len(removables) + 1):
			print('removing', l, 'types')
			for rmtypes in itertools.combinations(removables, l):
				rm_marking = self._single_tok_marking(rmtypes)
				print('removed', rm_marking)
				yield full_marking - rm_marking
	def enum_sub_start(self):
		''' rule out params in function signature one by one 
			and return corresponding starting marking '''
		removables = self.sigtr.paras.copy()
		removables.remove(self._brchbef)
		for l in range(1, len(removables) + 1):
			for rmargs in itertools.combinations(removables, l):
				# BECAREFUL: change the internal state of the class
				self._variables = list(set(self._allvars) - set(rmargs))
				# print(set(self._allvars), set(rmargs))
				mrk = self._single_tok_marking(map(second_elem_of_tuple, self._variables))
				yield mrk
	def restore_variables(self):
		self._variables = self._allvars

class Signature(IOWeightObject):
	"""A base class for Component and Target"""
	def __init__(self, sigtr_dict):
		assert len(sigtr_dict['paramNames']) == len(sigtr_dict['paramTypes'])
		self.name = sigtr_dict['name']
		self.paras = list(zip(sigtr_dict['paramNames'], sigtr_dict['paramTypes'])) # to (arg name, arg type) list
		self.rtypes = sigtr_dict['tgtTypes'] if isinstance(sigtr_dict['tgtTypes'], list) else [sigtr_dict['tgtTypes']]
		self._in, self._out = self._in_weights(), self._out_weight()
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
	def paras_of_list_type(self):
		'''very similar to params_of_type'''
		return [para for para in self.paras if 'list' in para[1]]
	def sketch(self, dummy=None, rec=True):
		"""write out the function definition"""
		return 'let ' + ('rec ' if rec else '') + self.name + ' ' + ' '.join(self.paras_list()) + ' ='
	def variables(self):
		'''make TargetFunc act as a SketchLine'''
		return iter(self.paras)
	def holes(self):
		return []
	def id_func_variables(self):
		'''only for function signature that returns one value'''
		return self.params_of_type(self.rtypes[0])
	def __str__(self):
		return repr('TargetFunc({0}): {1}'.format(self.name, self.paras))

class SubFunc(TargetFunc):
	""" The instance of this class might have both different input and output than 
		the TargetFunc it originated from """
	def __init__(self, sub_dict):
		super(SubFunc, self).__init__(sub_dict)
	def id_func_variables(self):
		return []
	def __str__(self):
		return repr('SubFunc({0}): {1} -> {2}'.format(self.name, self.paras, self.rtypes))

class Component(Signature):
	"""A function in the specified library"""
	def __init__(self, signature, petri):
		super(Component, self).__init__(signature)
		self.net = petri
		self.name = func_id(signature['name'], signature.get('module', ''))
		self._add_funcs()
	def __str__(self):
		return self.name + ' : ' + ' -> '.join(self.io_types())
	def id(self):
		return self.name
	def param_types(self):
		'''return the function's parameter types '''
		return list(map(lambda x: x[1], self.paras))
	def io_types(self):
		'''return the concated list of in and out (distinct)types, in types first'''
		return list(itertools.chain(self._in.keys(), self._out.keys())) 
	def _add_funcs(self):
		inlen = len(self._in)
		for instance, subst in instantiate_generics(self.io_types(), PRIMITIVE_TYPES):
			i, o = {}, {} # unpack the input and output
			for t, w in zip(instance[:inlen], self._in.values()): # {"'a":2} -> [(ground("'a"), 2)]
				i[t] = i.get(t, 0) + w
			for t, w in zip(instance[inlen:], self._out.values()):
				o[t] = o.get(t, 0) + w
			self._add_func(i, o, func_id_in_petri(self.id(), subst))
	def _add_func(self, _in, _out, funcname):
		"""add transition to the Petri Net"""
		if isinstance(_in, dict):
			_in = _in.items()
		if isinstance(_out, dict):
			_out = _out.items()
		assert not self.net.has_transition(funcname)
		self.net.add_transition(Transition(funcname))
		for place, weight in _in:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
			self.net.add_input(place, funcname, MultiArc([Variable('var')] * weight))
		for place, weight in _out:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
			self.net.add_output(place, funcname, MultiArc([Variable('var')] * weight))

	def sketch(self, varlist, holelist, substitution=None):
		'''outline the component function in string form, either non-complete or complete ver.'''
		assert len(varlist) == self.output_len() and len(holelist) == self.input_len()
		sk = "let "
		sk += comma_join(varlist)
		sk += " = "
		if self.name in ['^', '=', ' * ']:
			assert len(self.paras) == 2
			self.name = '(' + self.name + ')' # be careful about this inconsistency
		sk += self.name
		if substitution is None:
			para2print = ('#' + str(hole) + '(' + typing + ')' for hole, typing in zip(holelist, self.param_types()))
		else:
			para2print = (substitution[hole] for hole in holelist)
		for param in para2print:
			sk += ' ' + param
		return sk

class SketchLine(object):
	'''An abstract data structure for a line of sketch(semantic of a line)
		sketch feature added'''
	def __init__(self, comp, variables, holes):
		self._comp = comp
		self._holes = holes # list of (hole#, type)
		self._vars = variables # list of (var_name, type)
	def __str__(self):
		return (self._comp.name if self._comp else '(none)') + '(holes: ' + str(self._holes) + \
				 ', vars: ' + str(self._vars) + ')'
	def holes(self):
		return (hole for hole in self._holes)
	def variables(self):
		'''a polymorphistic method'''
		return (var for var in self._vars)
	def sketch(self, subst=None):
		'''take care of the return line, if it is line like "let a = foo b", pass down to component'''
		if self._comp is None:
			if subst is None:
				return ', '.join(map(lambda x: '#' + str(first_elem_of_tuple(x)), self._holes))
			return ','.join([subst[hole] for hole, _ in self._holes])
		return self._comp.sketch(self._vars, list(map(first_elem_of_tuple, self._holes)), subst)

class Sketch(object):
	"""data structure for a code sketch in purpose to complete in SAT solver"""
	def __init__(self, sklines):
		self.type_vars = {} # each bucket stores the variables having the same type
		self.type_holes = {} # each bucket contains places
		self.var_holes = {} # each bucket(keyed with variable) contains candidate places
		self.hole_vars = {} # each bucket contains variables
		self.s = z3.Solver()
		self.hypos = {}
		# print(sklines)
		self.unit_used = False
		self.args = sklines[0].paras_list()
		self.last_var = next(sklines[-2].variables())[0] # the first var of the second last line
		self.init_frame(sklines)
	def init_frame(self, sklines):
		for skline in sklines:
			self._add_line(skline)
		self._add_var_cands() # good to put here
		self._set_up_constraints()

	def _vars(self):
		for typing in self.type_vars:
			for var in self.type_vars[typing]:
				yield (var, typing)
	def _hypos(self):
		for hole_cands in self.hypos.values():
			for hyp in hole_cands.values():
				yield hyp

	def _add_line(self, line):
		'''
		when encountering every hole, find all candidate variables that will be filled here; 
		at the same time, append holes to type-buckets
		'''
		for hole, typing in line.holes():
			self.hole_vars[hole] = self.type_vars[typing].copy() # shallow copy
			if typing not in self.type_holes:
				self.type_holes[typing] = set()
			self.type_holes[typing].add(hole)
		for var, typing in line.variables():
			if not (var[0].isalpha()): # be careful
				self.unit_used = True
				continue # don't add _(unit into the variable list)
			if typing not in self.type_vars:
				self.type_vars[typing] = set()
			self.type_vars[typing].add(var)

	def _add_var_cands(self):
		''' candidate variables for holes are collected here '''
		for var, typing in self._vars():
			self.var_holes[var] = set()
			candiate_holes = (hole for hole in self.type_holes[typing] if var in self.hole_vars[hole])
			self.var_holes[var].update(candiate_holes)
	def add_rec_constraints(self, holes_matrix, brch):
		''' add constraints to the holes(parameters) in recursive calls
		holes_matrix is like [[h3,h4], [h8,h9]], where hi is (#, type) tuple, all rows align accrd to type
		for a recursive call, ex, foo (v:int) (w:intlist), the vcand_matrix is like
				[[hd], [tl]], hd typed with int, tl typed with intlist
		'''
		try:
			brch_vars = brch.brch_variables()
		except :
			print('no need to add recursive constraints')
			return
		ttypes = map(second_elem_of_tuple, holes_matrix[0])
		vcand_matrix = [[p[0] for p in brch_vars if p[1] == t] for t in ttypes]
		for hs in holes_matrix:
			holes = map(first_elem_of_tuple, hs)
			for hole, variables in zip(holes, vcand_matrix):
				vcandlist = [self.hypos[hole][v] for v in variables]
				if len(vcandlist) == 0:
					raise ConstraintError('recursive call, not enough variables')
				self._exact_one_constraint(vcandlist)

	def _set_up_constraints(self):
		'''set up constraint for each hole and variable respectively'''
		for hole in self.hole_vars:
			self.hypos[hole] = {}
			for var in self.hole_vars[hole]:
				self.hypos[hole][var] = z3.Bool(hypo_var_gen(hole, var))
			vcandlist = list(self.hypos[hole].values())
			if DEBUG:
				print('HOLE CONSTRAINTS LIST: ' + str(vcandlist))
			self._exact_one_constraint(vcandlist)
		self._set_var_constraints()

		if not self.unit_used: # temporaly
			self._set_other_constraints()

	def _exact_one_constraint(self, hs):
		''' exactly one of hs is true '''
		assert isinstance(hs, list)
		self.s.add(z3.AtMost(hs + [1])) # all add up to 0 or 1
		self.s.add(z3.Or(hs))

	def _set_var_constraints(self):
		for var in self.var_holes:
			hcandlist = list(self.hypos[hole][var] for hole in self.var_holes[var])
			if DEBUG:
				print('VAR CONSTRAINTS LIST ' + str(hcandlist))
			self.s.add(z3.AtLeast(hcandlist + [1]))
	
	def _set_other_constraints(self):
		''' constraints that lessen the sketch:code ratio '''
		last_hole, last_var = len(self.hole_vars) - 1, self.last_var
		self.s.add(self.hypos[last_hole][last_var])
		hs = [self.hypos[last_hole][arg] for arg in self.args if arg in self.hypos[last_hole]]
		self.s.add(z3.Not(z3.Or(hs)))

	def _process_model(self):
		m = self.s.model()
		block = []
		for hyp in self._hypos():
			if z3.is_true(m.eval(hyp)):
				block.append(hyp)
		self.s.add(z3.Not(z3.And(block)))
		assignment = block.copy()
		assignment = map(lambda x: decompose_hypo_var(str(x)), assignment)
		if DEBUG:
			assignment = list(assignment)
			assignment.sort()
			print(assignment)
		subst = {}
		for hole, var in assignment:
			subst[hole] = var
		# print(subst)
		return subst

	def enum_subst(self):
		'''enumerate possible completions of the code sketch'''
		# self._add_var_cands()
		# self._set_up_constraints()
		if DEBUG:
			print('Sketch.enum_subst: ')
			print('type_vars: ' + str(self.type_vars))
			print('type_holes: ' + str(self.type_holes))
			print('hole_vars: ' + str(self.hole_vars))
			print('var_holes: ' + str(self.var_holes))
			print()
		while True:
			start = time.clock()
			if z3.sat == self.s.check():
				# print('z3 solve time:', time.clock() - start)
				# print('  -----',end='')
				yield self._process_model()
			else:
				break
