from utility import *
import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

import copy
import z3
import subprocess

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

counter = itertools.count(1) # temperialy use it
class Branch(IOWeightObject):
	def __init__(self, sigtr, brchbef, brchargs, brchtype='list'):
		''' class for a branch of pattern matching
			brch arg example: 
			in |hd::tl -> ..., hd and tl are branch argument for this branch
			NOTE: consider making this class the subclass of targetFunc!!!
		'''
		assert isinstance(sigtr, Signature) # a branch is derived from a function signature
		assert isinstance(brchbef, tuple) and len(brchbef) == 2 # example (arg0, int list)
		if brchtype != 'list':
			raise NotImplementedError('data structure other than list pattern matching not considered') 
		
		self.paras = brchargs
		self.brchtype = brchtype
		self.brch_id = next(counter)
		self._in = self._in_weights()
		self._out = sigtr._out # bad pattern? member access between siblings
		carg, ctype = brchbef
		self.matchline = 'match ' + carg + ' with'
		self.start_marking = self._branch_marking(sigtr, ctype)
	def _branch_marking(self, sigtr, ctype):
		''' bad. copy & paste, should change '''
		ws = {}
		for i, weight in self._in.items():
			ws[i] = MultiSet(['t'] * weight)
		return Marking(ws) + (sigtr.get_start_marking() - Marking({ctype:MultiSet(['t'])}))
	def brch_sketch(self):
		if self.brchtype == 'list':
			if len(self.paras) == 0:
				return '| [] ->'
			return '|' + '::'.join(self.paras_list()) + '->'
		raise NotImplementedError('other cases')
	def __str__(self):
		'''for debug'''
		return self.brch_sketch()

class SynBranch(object):
	'''basically do the same work as synthesis'''
	def __init__(self, synthesis, brch):
		assert synthesis.stategraph is not None
		print('before copy')
		self.synt = copy.copy(synthesis) # is copy good enough?
		self.brch = brch
		startmrk = self.brch.start_marking
		endmrk = self.synt.stategraph.end_marking
		print(startmrk)
		print(endmrk)
		self.synt.stategraph = StateGraph(self.synt.net, start=startmrk, end=endmrk)
	def _sketch_other_case(self):
		return '| _ -> raise Not_found'
	def _enum_brch_sketch(self):
		self.synt.setup()
		for sketch in self.synt.enum_concrete_sketch(brchout=False):
			brchsk = [self.brch.brch_sketch()] + sketch[1:]
			yield  brchsk # ignore the signature
	def _enum_partial_sketch(self):
		for brchsk in self._enum_brch_sketch():
			runablesketch = [self.synt.targetfunc.sigtr_sketch()]
			runablesketch.extend([self.brch.matchline])
			runablesketch.extend(brchsk)
			runablesketch.extend([self._sketch_other_case()])
			yield runablesketch, brchsk
	def _test_partial(self, partial, outname):
		print('partial test run')
		return self.synt._test(partial, outname)
	def accepting_partial(self):
		'''if there is one return it, otherwise return None'''
		print('finding accepting partial: ' + str(self.brch))
		outfile = self.synt.targetfunc.name + '_brch_' + str(self.brch.brch_id)
		for torun, brchsk in self._enum_partial_sketch():
			if self._test_partial(torun, outfile):
				# print('partial runable:')
				# print(torun)
				return brchsk

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
		self.comps = None
		self.stategraph = None
		self._synlen = 5
		self.testpath = sigtr['testpath']
	def _branch_out(self, brch):
		'''create a new branch that does the subtask of synthesis
		(a branch of pattern matching) '''
		return SynBranch(self, brch)

	def draw_net(self):
		self.net.draw('draws/' + self.targetfunc.name + '.eps')
	def draw_state_graph(self):
		self.stategraph.draw('draws/' + self.targetfunc.name + '_sg.eps')

	def setup(self):
		if self.comps is None:
			self.comps = dict(((comp['name'], Component(comp, self.net)) 
					for comp in parse_multiple_dirs(self.dirs)))
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
	def id_sketches(self):
		'''return one of parameters'''
		tgt = self.targetfunc.rtypes[0] # for only one return value
		for para in self.targetfunc.params_of_type(tgt):
			sklines = [SketchLine(None, [], [(0, tgt)])] # single hole
			formatter = SketchFormatter(self.targetfunc, sklines)
			lines = formatter.format_out({0:para})
			print_sketch(lines)
			yield lines
	def enum_concrete_sketch(self, brchout=True):
		'''enumerate completed sketch'''
		yield from self.id_sketches() # identity functions
		print('-----------end of id sketches-------------')
		if brchout:
			list_args = self.targetfunc.paras_of_list_type()
			for arg, t in list_args:
				# assume t as a string has the formate: ? list
				elemtype, listtype = t.split(' ')
				branchings = []
				branchings.append(Branch(self.targetfunc, (arg, t), []))
				branchings.append(Branch(self.targetfunc, (arg, t), [('hd', elemtype),('tl', listtype)]))
				combined = [self.targetfunc.sigtr_sketch()] # not good
				for b in branchings:
					subsyn = self._branch_out(b)
					partial_sketch = subsyn.accepting_partial()
					if partial_sketch is None:
						combined = None
						break
					combined.extend(partial_sketch)
				if combined is None:
					break
				yield combined
			print('-----------end of branched sketches-------------')
		for sk, skformatter in self.inc_len_sketch_enum():
			print_sketch(skformatter.format_out())
			for concrtsk in sk.enum_subst():
				print('--->')
				concretelines = skformatter.format_out(concrtsk)
				print_sketch(concretelines)
				yield concretelines
			if brchout: print('-----------one seq ended-------------')

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
			func_id = restore_id(f) # recover the name of the function from ground tag
			subst = dict(zip(ext_syms_list(self.comps[func_id].io_types()), ground_terms(f)))
			vartype = [instantiate(t, subst) for t in self.comps[func_id].rtypes]
			holetype = [instantiate(t, subst) for t in self.comps[func_id].param_types()]
			# print(subst)
			# print(vartype)
			# print(holetype)
			# ocaml specific: unit type
			variables = [('_' if rt == 'unit' else next(var_gen), rt) for rt in vartype]
			holes = [next(counter) for i in range(self.comps[func_id].input_len())]
			skline = SketchLine(self.comps[func_id], variables, list(zip(holes, holetype)))
			lines.append(skline)
		# set up return line
		return_holes = [next(counter) for _ in range(self.targetfunc.output_len())]
		retline = SketchLine(None, [], list(zip(return_holes, self.targetfunc.rtypes)))
		lines.append(retline)
		return Sketch(self.targetfunc, lines), SketchFormatter(self.targetfunc, lines)

	def stat(self):
		"""show statistics after synthesis"""
		raise NotImplementedError('not yet implemented')

class Signature(IOWeightObject):
	"""A base class for Component and Target"""
	def __init__(self, sigtr_dict):
		self.name = sigtr_dict['name']
		assert len(sigtr_dict['paramNames']) == len(sigtr_dict['paramTypes'])
		# (key, value) -> (arg name, arg type)
		self.paras = list(zip(sigtr_dict['paramNames'], sigtr_dict['paramTypes']))
		if isinstance(sigtr_dict['tgtTypes'], list):
			self.rtypes = sigtr_dict['tgtTypes'] # return types
		else:
			self.rtypes = [sigtr_dict['tgtTypes']]
		self._in, self._out = self._in_weights(), self._out_weight()
	def input_len(self):
		return len(self.paras)
	def output_len(self):
		return len(self.rtypes)
	def params_of_type(self, t):
		return list(para for para, typing in self.paras if typing == t)

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
	def sigtr_sketch(self):
		"""write out the function definition"""
		return 'let ' + self.name + ' ' + ' '.join(self.paras_list()) + ' ='

class Component(Signature):
	"""A function in the specified library"""
	def __init__(self, signature, petri):
		super(Component, self).__init__(signature)
		self.net = petri
		self._add_funcs()

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
			# print(instance)
			i = list(zip(instance[:inlen], self._in.values())) # {"'a":2} -> [(ground("'a"), 2)]
			o = list(zip(instance[inlen:], self._out.values()))
			self._add_func(i, o, func_id_in_petri(self.id(), subst))
	def _add_func(self, _in, _out, funcname):
		"""add transition to the Petri Net"""
		for place, _ in _in:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		for place, _ in _out:
			if not self.net.has_place(place):
				self.net.add_place(Place(place))
		# issue: functions with same name from different modules
		assert not self.net.has_transition(funcname)
		self.net.add_transition(Transition(funcname))
		for place, weight in _in:
			self.net.add_input(place, funcname, MultiArc([Variable('var')] * weight))
		for place, weight in _out:
			self.net.add_output(place, funcname, MultiArc([Variable('var')] * weight))

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
			if not is_variable(var): continue # don't add _(unit into the variable list)
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
