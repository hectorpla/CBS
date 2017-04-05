from data import *
from sformat import *

class SynBranch(object):
	''' basically do the same work as synthesis.
		be careful: a synbracn composes a synthesis, so when doing synthesis-related things,
		refer to the synt member
	'''
	def __init__(self, synthesis, brch):
		assert synthesis.stategraph is not None
		self.synt = copy.copy(synthesis) # is copy good enough?
		self.brch = brch
		self.synt.start_marking = self.brch.start_marking
		self.synt.id_func_pool += self.brch.params_of_type(self.synt.tgttype) # extend the id pool
		self.synt.firstlineobj = self.brch
		# the end marking remains the same
		print('BRANCH start', self.synt.start_marking)
		print('BRANCH end', self.synt.end_marking)
	def _sketch_other_case(self):
		return '| _ -> raise Not_found'
	def _enum_brch_sketch(self):
		self.synt.setup()
		for sk in self.synt.enum_concrete_sketch(brchout=False):
			brchsk = [self.brch.sketch()] + sk[1:]
			yield brchsk # ignore the signature
	def _enum_partial_sketch(self):
		for brchsk in self._enum_brch_sketch():
			runablesketch = [self.synt.targetfunc.sketch()]
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
	def __init__(self, parent=None, sigtr_file=None, enab_func_para=True):
		sigtr = parse_json(sigtr_file)
		self.targetfunc = TargetFunc(sigtr)
		if self.targetfunc is None:
			raise parseError('format for the target function is incorrect')
		self.net = PetriNet('NET for ' + sigtr['name'])
		dirs = sigtr['libdirs']
		if not isinstance(dirs, list): dirs = [dirs]
		self.dirs = dirs
		self.enab_func_para = enab_func_para
		self.comps = None
		self.stategraph = None
		self._synlen = 5
		self.testpath = sigtr['testpath']
		self._construct_components()
		# self.print_comps()
		self.enum_counter = itertools.count(0)

		# attributes allowed to be changed
		self.start_marking = self.targetfunc.get_start_marking() 
		self.end_marking = self.targetfunc.get_end_marking()
		self.tgttype = self.targetfunc.rtypes[0] # for only one return value
		self.id_func_pool = self.targetfunc.params_of_type(self.tgttype) # the candidate pool from which id function pick return variable
		self.firstlineobj = self.targetfunc # first line may be a TargetFunc or a Branch
	def _construct_components(self):
		'''establish component info'''
		if self.comps is None:
			temp = ((func_id(comp['module'], comp['name']), Component(comp, self.net))
					for comp in parse_multiple_dirs(self.dirs) 
					if self.enab_func_para or not has_func_para(comp['paramTypes']))
			self.comps = dict(temp)
	def setup(self):
		assert self.start_marking == self.firstlineobj.get_start_marking()
		self.stategraph = StateGraph(self.net, start=self.start_marking, end=self.end_marking)
		self.stategraph.build()
		
	def set_syn_len(self, max_len):
		self._synlen = max_len

	def _branch_out(self, brch):
		'''create a new branch that does the subtask of synthesis
		(a branch of pattern matching) '''
		return SynBranch(self, brch)
	def start(self):
		'''interface for outside'''
		for sketch in self.enum_concrete_sketch():
			next(self.enum_counter)
			if self._test(sketch, self.targetfunc.name):
				print('SUCCEEDED!!! ' + str(next(self.enum_counter)) + ' sketches enumerated')
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
			for line in sketch:
				targetfile.write(line + '\n')
			with open(self.testpath) as test:
				targetfile.write(test.read())
	def id_sketches(self):
		'''yield functions that return one of the parameters(in signature or branch)'''
		for para in self.id_func_pool:
			sklines = [self.targetfunc]
			sklines.append(SketchLine(None, [], [(0, self.tgttype)])) # single hole
			formatter = SketchFormatter(sklines)
			lines = formatter.format_out({0:para})
			print_sketch(lines)
			yield lines
	def enum_branch_sketch(self):
		print('--- START OF BRANCH ENUMERATING ---')
		list_args = self.targetfunc.paras_of_list_type()
		for arg, t in list_args:
			# assume t as a string has the formate: ? list
			elemtype, _ = t.split(' ')
			branchings = []
			branchings.append(Branch(self.targetfunc, (arg, t), []))
			branchings.append(Branch(self.targetfunc, (arg, t), [('hd', elemtype),('tl', t)]))
			combined = [self.targetfunc.sketch()] # not good
			combined.append(branchings[0].matchline)
			for b in branchings:
				subsyn = self._branch_out(b)
				partial_sketch = subsyn.accepting_partial()
				if partial_sketch is None:
					combined = None
					break
				print('  $$branch', b, 'synthesized successful')
				combined.extend(partial_sketch)
			if combined is None:
				break
			print('+++++++++++++')
			yield combined
	def enum_concrete_sketch(self, brchout=True):
		'''enumerate completed sketch, called by Synthesis object '''
		yield from self.id_sketches()
		print('-----------end of id sketches-------------')
		if brchout:
			try:
				yield from self.enum_branch_sketch()
				print('-----------end of branched sketches-------------')
			except snakes.plugins.search.CannotReachErrorr as cre:
				print('///////')
				print(cre)
				exit()
		print('--- START OF STRAIGHT ENUMERATING ---')
		for sk, skformatter in self._inc_len_sketch_enum():
			print_sketch(skformatter.format_out())
			for concrtsk in sk.enum_subst():
				print('--->')
				concretelines = skformatter.format_out(concrtsk)
				print_sketch(concretelines)
				yield concretelines
			if brchout: print('-----------one seq ended-------------')

	def _inc_len_sketch_enum(self):
		'''enumerate non-complete sketches(with holes)'''
		for seq in self.stategraph.enumerate_sketch_l(self._synlen):
			print(seq)
			yield self._gen_sketch(seq)

	def _gen_sketch(self, sequence):
		'''create Sketch object for completion and SketchFormatter for output'''
		counter = itertools.count(0)
		var_gen = var_generator()
		lines = []
		lines.append(self.firstlineobj) # should be modified to append branch argument
		for f in sequence:
			if f.startswith('clone_'): # watchout: mind the name confilction 
				continue
			func_id = restore_id(f) # recover the name of the function from ground tag
			subst = dict(zip(ext_syms_list(self.comps[func_id].io_types()), ground_terms(f)))
			vartype = [instantiate(t, subst) for t in self.comps[func_id].rtypes]
			holetype = [instantiate(t, subst) for t in self.comps[func_id].param_types()]
			variables = [('_' if rt == 'unit' else next(var_gen), rt) for rt in vartype] # ocaml specific: unit type
			holes = [next(counter) for i in range(self.comps[func_id].input_len())]
			skline = SketchLine(self.comps[func_id], variables, list(zip(holes, holetype)))
			lines.append(skline)
		return_holes = [next(counter) for _ in range(self.targetfunc.output_len())] # set up return line
		retline = SketchLine(None, [], list(zip(return_holes, self.targetfunc.rtypes)))
		lines.append(retline)
		return Sketch(lines), SketchFormatter(lines)

	def stat(self):
		"""show statistics after synthesis"""
		raise NotImplementedError('not yet implemented')

	def print_comps(self):
		comp_counter = itertools.count(0)
		for c in self.comps:
			print(next(comp_counter), c)
	def draw_net(self):
		numnode = len(self.net._place) + len(self.net._trans)
		if numnode > 200:
			print('*************** Warning: PetriNet too large(' + str(numnode) 
				+ ' nodes), drop drawing ***************')
			return
		self.net.draw('draws/' + self.targetfunc.name + '.eps')
	def draw_augmented_net(self):
		assert self.stategraph is not None
		self.stategraph.net.draw('draws/' + self.targetfunc.name + '_aug.eps')
	def draw_state_graph(self):
		self.stategraph.draw('draws/' + self.targetfunc.name + '_sg.eps')
