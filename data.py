from utility import *
import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *
import z3
import subprocess

DEBUG = True
PAUSE = True

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
		dirs = sigtr['libdirs']
		if not isinstance(dirs, list):
			dirs = [dirs]
		self.dirs = dirs
		self.comps = dict(((comp['name'], Component(comp, self.net)) for comp in parse_multiple_dirs(dirs)))
		self.stategraph = None
		self._synlen = 5
		self.testpath = sigtr['testpath']

	def draw_net(self):
		self.net.draw('draws/' + self.targetfunc.name + '.eps')

	def setup(self):
		start_marking = self.targetfunc.get_start_marking()
		end_marking = self.targetfunc.get_end_marking()
		self.stategraph = StateGraph(self.net, 
			start=start_marking, end=end_marking, aug_graph='draws/clone_added.eps')
		self.stategraph.build()

	def set_syn_len(self, max_len):
		self._synlen = max_len

	def start(self):
		'''interface for outside'''
		for sketch in self.enum_concrete_sketch():
			if self._test(sketch, self.targetfunc.name):
				print('SUCCEEDED!!!')
				break
			print('FAILED')
			if PAUSE:
				input("PRESS ENTER TO CONTINUE.\n")

	def _test(self, testsketch, outname):
		'''compile/test the code against user-provided tests'''
		outpath = 'out/' + outname + '.ml'
		self._write_out(testsketch, outpath)
		test_command = ['ocaml', outpath]
		subproc = subprocess.Popen(test_command, stdout=subprocess.PIPE)
		return b'true' == subproc.communicate()[0]

	def _write_out(self, sketch, outpath):
		'''write the completed sketch into a file'''
		with open(outpath, 'w') as targetfile:
			for dir in self.dirs:
				module_name = last_component(dir)
				module_name = module_name[0].upper() + module_name[1:]
				# print(module_name)
				targetfile.write('open ' + module_name + '\n')
			for line in sketch:
				targetfile.write(line + '\n')
			with open(self.testpath) as test:
				targetfile.write(test.read())

	def enum_concrete_sketch(self):
		'''enumerate completed sketch: wrapper for '''
		for sk, skformatter in self.inc_len_sketch_enum():
			print_sketch(skformatter.format_out())
			for sub in sk.enum_subst():
				print('--->')
				sketch = skformatter.format_out(sub)
				print_sketch(sketch)
				yield sketch
			print('-----------one seq ended-------------')

	def inc_len_sketch_enum(self):
		'''enumerate non-complete sketch'''
		for seq in self.stategraph.enumerate_sketch_l(self._synlen):
			print(seq)
			yield self._gen_sketch(seq)

	def non_rep_sketch_enum(self):
		"""
		for seq in s.enumerate_sketch():
		print(seq)
		for line in gen_sketch(comps, seq):
			print(line)
		print()
		"""
		raise NotImplementedError('not yet implemented')

	def _gen_sketch(self, sequence):
		'''create Sketch object for completion and SketchFormatter for output'''
		counter = itertools.count(0)
		var_gen = var_generator()
		lines = []
		for f in sequence:
			if f.startswith('clone_'): # watchout: mind the name confilction 
				continue
			# ocaml specific
			variables = [('_' if rt == 'unit' else next(var_gen), rt) for rt in self.comps[f].rtypes]
			holes = [next(counter) for i in range(self.comps[f].input_len())]
			skline = SketchLine(self.comps[f], variables, list(zip(holes, self.comps[f].param_types())))
			lines.append(skline)
		# set up return line
		return_holes = [next(counter) for _ in range(self.targetfunc.output_len())]
		retline = SketchLine(None, [], list(zip(return_holes, self.targetfunc.rtypes)))
		lines.append(retline)
		return Sketch(self.targetfunc, lines), SketchFormatter(self.targetfunc, lines)

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
		return 'let ' + self.name + ' ' + sep_join(self.paras) + ' ='

class Component(Signature):
	"""A function in the specified library"""
	def __init__(self, signature, petri):
		super(Component, self).__init__(signature)
		self.net = petri
		self._add_func()

	def id(self):
		return self.name

	def param_types(self):
		'''return the function's parameter types '''
		return list(map(lambda x: x[1], self.paras))
	def _add_func(self):
		"""add transition to the Petri Net"""
		for place in self._in:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		for place in self._out:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		# issue: functions with same name from different modules
		assert not self.net.has_transition(self.id())
		self.net.add_transition(Transition(self.id()))
		for place, weight in self._in.items():
			self.net.add_input(place, self.id(), MultiArc([Variable('var')] * weight))
		for place, weight in self._out.items():
			self.net.add_output(place, self.id(), MultiArc([Variable('var')] * weight))

	def sketch(self, varlist, holelist, substitution=None):
		'''outline the component function in string form, either non-complete or complete ver.'''
		assert len(varlist) == self.output_len() and len(holelist) == self.input_len()
		sk = "let "
		sk += comma_join(varlist)
		sk += " = "
		if self.name in ['^']:
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
		return '(holes: ' + str(self._holes) + ', vars: ' + str(self._vars) + ')'
	def holes(self):
		return (hole for hole in self._holes)
	def variables(self):
		return (var for var in self._vars)
	def sketch(self, subst=None):
		'''take care of the return line'''
		if self._comp is None:
			if subst is None:
				return ', '.join(map(lambda x: '#' + str(first_elem_of_tuple(x)), self._holes))
			return ','.join([subst[hole] for hole, _ in self._holes])
		return self._comp.sketch(self._vars, list(map(first_elem_of_tuple, self._holes)), subst)

class SketchFormatter(object):
	'''a class that format up the systhesised codes'''
	def __init__(self, sigtr, lines):
		assert isinstance(sigtr, TargetFunc)
		assert isinstance(lines[0], SketchLine)
		self._signature = sigtr
		self._lines = lines # list of SketchLine
	def format_out(self, subst=None):
		sk = []
		sk.append(self._signature.sigtr_sketch())
		for skline in self._lines[:-1]:
			toprint = skline.sketch(subst)
			sk.append('\t' + toprint + ' in')
		sk.append('\t' + self._lines[-1].sketch(subst))
		return sk

class Sketch(object):
	"""data structure for a code sketch in purpose to complete in SAT solver"""
	def __init__(self, signature, sklines):
		self.type_vars = {} # each bucket stores the variables having the same type
		self.type_holes = {} # each bucket contains places
		self.var_holes = {} # each bucket(keyed with variable) contains candidate places
		self.hole_vars = {} # each bucket contains variables
		self.s = z3.Solver()
		self.hypos = {}
		self.init_frame(signature, sklines)
	def init_frame(self, signature, sklines):
		self._add_signature(signature)
		for skline in sklines:
			self._add_line(skline)
	def _vars(self):
		for typing in self.type_vars:
			for var in self.type_vars[typing]:
				yield (var, typing)
	def _hypos(self):
		for hole_cands in self.hypos.values():
			for hyp in hole_cands.values():
				yield hyp
	def _add_signature(self, sigtr):
		'''Simply add parameters(variables) into types, and set up variable constraints frame'''
		assert isinstance(sigtr, Signature)
		for name, typing in sigtr.paras:
			if typing not in self.type_vars:
				self.type_vars[typing] = set()
			self.type_vars[typing].add(name)
			self.var_holes[name] = set()
		# print('Sketch.add_signature: ')
		# print('type_vars ' + str(self.type_vars))

	def _add_line(self, line):
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
			assert is_variable(var)
			if typing not in self.type_vars:
				self.type_vars[typing] = set()
			self.type_vars[typing].add(var)

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
			if DEBUG:
				print('HOLE CONSTRAINTS LIST: ' + str(vcandlist))
			self.s.add(z3.AtMost(vcandlist + [1])) # all add up to 0 or 1
			self.s.add(z3.Or(vcandlist))

		for var in self.var_holes:
			hcandlist = list(self.hypos[hole][var] for hole in self.var_holes[var])
			if DEBUG:
				print('VAR CONSTRAINTS LIST ' + str(hcandlist))
			self.s.add(z3.AtLeast(hcandlist + [1]))
	
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
		import time
		self._add_var_cands()
		self._set_up_constraints()
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
				print(time.clock() - start)
				print('  -----',end='')
				yield self._process_model()
			else:
				break

