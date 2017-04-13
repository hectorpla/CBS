from data import *
from sformat import *

class SynBranch(object):
	''' basically do the same work as synthesis.
		be careful: a synbracn composes a synthesis, so when doing synthesis-related things,
		refer to the synt member
	'''
	def __init__(self, synthesis, brch):
		assert synthesis.stategraphs is not None
		self.synt = synthesis # copy.copy(synthesis) # is copy good enough?
		self.brch = brch

		# the end marking remains the same
		print('BRANCH start', self.brch.start_marking)
		print('BRANCH end', self.synt.end_marking)
	def _sketch_other_case(self):
		return '| _ -> raise Syn_exn'
	def _enum_brch_sketch(self):
		id_cand = self.brch.id_func_variables()
		start = self.brch.start_marking
		yield from self.synt.enum_concrete_sketch(self.brch, id_cand, start, brchout=False)
		for substart in self.brch.enum_sub_start():
			print('sub start marking: ', substart)
			brchsks = self.synt.enum_concrete_sketch(self.brch, [], substart, brchout=False)
			yield from brchsks
	def _make_runable(self, brchsk):
		runablesketch = [self.synt.targetfunc.sketch()]
		runablesketch.extend([self.brch.matchline])
		runablesketch.extend(brchsk)
		runablesketch.extend([self._sketch_other_case()])
		# print(runablesketch)
		return runablesketch
	def _test_partial(self, partial, outname):
		print('  (partial test run)')
		return self.synt._test(partial, outname)
	def accepting_partial(self):
		'''if there is one return it, otherwise return None'''
		print('finding accepting partial: ' + str(self.brch))
		outfile = self.synt.targetfunc.name + '_brch_' + str(self.brch.brch_id)
		for brchsk in self._enum_brch_sketch():
			torun = self._make_runable(brchsk)
			if self._test_partial(torun, outfile):
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
		self.stategraphs = None
		self._synlen = 5
		self.testpath = sigtr['testpath']
		self._construct_components()
		# self.print_comps()
		self.enum_counter = itertools.count(0)

		# attributes allowed to be changed
		self.tgttype = self.targetfunc.rtypes[0] # for only one return value

		self.start_marking = self.targetfunc.get_start_marking() 
		self.end_marking = self.targetfunc.get_end_marking()
	def _construct_components(self):
		'''establish component info'''
		if self.comps is None:
			temp = ((func_id(comp['module'], comp['name']), Component(comp, self.net))
					for comp in parse_multiple_dirs(self.dirs) 
					if self.enab_func_para or not has_func_para(comp['paramTypes']))
			self.comps = dict(temp)

	def _build_graph(self, sg):
		'''wrapper for building a graph'''
		start = time.clock()
		sg.build()
		print('state graph(' + str(len(sg)) + ' states) build time:', time.clock() - start)
	def setup(self):
		'''build up state graph according to the start'''
		# assert self.start_marking == self.firstlineobj.get_start_marking()
		self.stategraphs = [StateGraph(self.net, start=self.start_marking, end=self.end_marking)]
		self._build_graph(self.stategraphs[0])
		
	def set_syn_len(self, max_len):
		self._synlen = max_len

	def _branch_out(self, brch):
		'''create a new branch that does the subtask of synthesis
		(a branch of pattern matching) '''
		return SynBranch(self, brch)
	def start(self):
		'''interface for outside'''
		id_cand = self.targetfunc.id_func_variables() # arguments in signature having target type
		for sketch in self.enum_concrete_sketch(self.targetfunc, id_cand):
			next(self.enum_counter)
			if self._test(sketch, self.targetfunc.name):
				print('SUCCEEDED!!! ' + str(next(self.enum_counter)) + ' sketches enumerated')
				return
			print('FAILED')
			if PAUSE:
				input("PRESS ENTER TO CONTINUE.\n")
		print('Failed...', str(next(self.enum_counter)) + ' sketches enumerated')
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
			targetfile.write('exception Syn_exn\n\n')
			for line in sketch:
				targetfile.write(line + '\n')
			with open(self.testpath) as test:
				targetfile.write(test.read())
	def id_sketches(self, firstline, varpool):
		'''yield functions that return one of the parameters(in signature or branch)'''
		for para in varpool:
			sklines = [firstline]
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
			branchings.append(Branch(self.targetfunc, (arg, t), [('hd', elemtype),('_', t)]))
			combined = [self.targetfunc.sketch()] # not good
			combined.append(branchings[0].matchline)
			for b in branchings:
				subsyn = self._branch_out(b)
				partial_sketch = subsyn.accepting_partial()
				if partial_sketch is None:
					combined = None
					break
				print('$$branch', b, 'synthesized successfully\n')
				combined.extend(partial_sketch)
			if combined is None:
				break
			print('++++++Success in Brach Enumerating+++++++')
			yield combined
	def enum_concrete_sketch(self, firstline, id_varpool, stmrk=None, brchout=True):
		''' 
		enumerate completed sketch, called from Synthesis object that stands alone or allowed by synbranch
		concrete sketch example:
				let make_string arg0 arg1 = # firstline, can also be pattern matching (firstline, stmrk)
					# the body can be id function (id_varpool)
					let v0 = Char.uppercase_ascii arg1 in # (sequence determined by strmk)
					let v1 = String.make arg0 v0 in
					v1 # variable with target type
		'''
		yield from self.id_sketches(firstline, id_varpool)
		print('--- END OF ID SKETCH ---')
		if brchout:
			try:
				yield from self.enum_branch_sketch()
				print('--- END OF BRANCH ENUMERATING ---')
			except snakes.plugins.search.CannotReachErrorr as cre:
				print('///////')
				print(cre)
				exit()
		print('--- START OF STRAIGHT ENUMERATING ---')
		if stmrk is None:
			stmrk = self.targetfunc.get_start_marking()
		for sk, skformatter in self._inc_len_sketch_enum(firstline, stmrk):
			print(' ~sketche with holes~ ')
			print_sketch(skformatter.format_out())
			for concrtsk in sk.enum_subst():
				print('--->')
				concretelines = skformatter.format_out(concrtsk)
				print_sketch(concretelines)
				yield concretelines
			if brchout: print('- one seq ended -')

	def _inc_len_sketch_enum(self, firstline, stmrk):
		'''enumerate non-complete sketches(with holes)'''
		for sg in self.stategraphs:
			if stmrk in sg:
				yield from self._inc_enum(firstline, sg, stmrk)
				return # stop yielding
		# build a new state graph if neccessary
		print('<build new graph> new start:', stmrk)
		# ???: in the new graph, endmark might not be reachable from startmark
		self.stategraphs.append(StateGraph(self.net, start=stmrk, end=self.end_marking))
		self._build_graph(self.stategraphs[-1])
		yield from self._inc_enum(firstline, self.stategraphs[-1], stmrk)
	def _inc_enum(self, firstline, stategraph, start_marking):
		'''helper for _inc_len_sketch_enum()'''
		for seq in stategraph.enumerate_sketch_l(stmrk=start_marking, max_depth=self._synlen):
			print(seq)
			yield self._gen_sketch(seq, firstline)
	def _gen_sketch(self, sequence, firstline):
		'''create Sketch object for completion and SketchFormatter for output'''
		counter = itertools.count(0)
		var_gen = var_generator()
		lines = []
		lines.append(firstline) # should be modified to append branch argument
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
		numnode = len(self.net._place) + len(self.net._trans) # for convenience
		if numnode > 200:
			print('*************** Warning: PetriNet too large(' + str(numnode) 
				+ ' nodes), drop drawing ***************')
			return
		self.net.draw('draws/' + self.targetfunc.name + '.eps')
	def draw_augmented_net(self):
		assert self.stategraphs is not None
		self.stategraphs[0].net.draw('draws/' + self.targetfunc.name + '_aug.eps')
	def draw_state_graph(self):
		self.stategraphs[0].draw('draws/' + self.targetfunc.name + '_sg.eps')
	def draw_alpha(self, filename=None, relevant=False):
		if filename is None:
			filename = self.targetfunc.name
		useful_places = self.stategraphs[0].useful_places
		graph = self.net.construct_alpha_graph()
		attr = dict(style="invis", splines="true")
		todraw = plugins.gv.Graph(attr)
		for out in graph:
			if relevant and out not in useful_places:
				continue
			src = '_'.join(re.sub('[()*]', ' ', out).split())
			todraw.add_node(src, dict(shape="rectangle"))
			for in_ in graph[out]:
				if relevant and in_ not in useful_places:
					continue
				dest = '_'.join(re.sub('[()*]', ' ', in_).split())
				edge_attr = dict(arrowhead="normal", label='')
				if out in useful_places and in_ in useful_places:
					edge_attr['color'] = "red"
				todraw.add_edge(src, dest, edge_attr)
		todraw.render('draws/' + filename + '_alpha.eps')
