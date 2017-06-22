from data import *
from sformat import *
import utility

class SynBranch(object):
	''' basically do the same work as synthesis.
		be careful: a synbracn composes a synthesis in order to reuse synthesis info,
			but that causes cyclic reference
	'''
	def __init__(self, parent_synthesis, brch, collection, sb_id):
		assert parent_synthesis.stategraphs is not None
		self.synt = parent_synthesis # compose the original synthesis(do so because different branches share the same end)
		self.brch = brch
		self.sb_collection = collection
		self.sb_id = sb_id # the order this branch is in the synthesis
		self.accepting_partial = None

		# the end marking remains the same
		print('BRANCH start', self.brch.start_marking)
		print('BRANCH end', self.synt.end_marking)
	def _sketch_other_case(self):
		return '|_ -> raise Syn_exn'
	def _enum_brch_codes(self):
		''' use the parent synthesis to synthesize brch codes '''
		id_cand = self.brch.id_func_variables()
		start = self.brch.start_marking
		yield from self.synt.enum_concrete_code(self.brch, id_cand, start, brchout=False)
		for substart in self.brch.enum_sub_start():
			print('CHANGE START VAR: sub start marking:', substart)
			brchsks = self.synt.enum_concrete_code(self.brch, [], substart, brchout=False)
			yield from brchsks
	def _make_runable(self, brchpart):
		''' make complete program by concating branch part and the rest '''
		runablesketch = [self.synt.targetfunc.sketch()]
		runablesketch.extend([self.brch.matchline])
		for sb in self.sb_collection[:-1]: # add branch codes sythesized successfully previously
			assert sb.accepting_partial is not None
			runablesketch.extend(sb.accepting_partial)
		runablesketch.extend(brchpart)
		runablesketch.extend([self._sketch_other_case()])
		# print(runablesketch)
		return runablesketch
	def _test_partial(self, partial, outname):
		''' a wrapper of the test method of Synthesis '''
		print('  (partial test run)')
		return self.synt._test(partial, outname)
	def get_accepting_partial(self):
		''' if there is one return it, otherwise return None '''
		print('finding accepting partial: ' + str(self.brch))
		outfile = self.synt.targetfunc.name + '_brch_' + str(self.brch.brch_id)
		for brchpart in self._enum_brch_codes():
			torun = self._make_runable(brchpart)
			if self._test_partial(torun, outfile):
				self.accepting_partial = brchpart
				return brchpart

subtask_counter = itertools.count(1) # TEMPORARY
class SynPart(object):
	def __init__(self, parent_synthesis, subfunc, mid_tests):
		''' 
			mid_tests is an iterable that each time yield a ([args], result) tuple  
			test cases as ["let fun arg0 arg2 = <expected output>"; test2...]
		'''
		self.synt = parent_synthesis
		self.subfunc = subfunc
		self.func_name = subfunc.name
		self.testfile = 'test/' + self.func_name + '_test.ml'
		self.tests = mid_tests
	def _write_test(self):
		try:
			with open(self.testfile, 'w') as f:
				toline = lambda args,result: self.func_name + ' ' + ' '.join(args) + ' = ' + result
				lines = (toline(*test) for test in self.tests)
				utility.write_tests_tofile(lines, f)
		except Exception as e:
			print(e)
			exit()
	def get_subtask_code(self):
		''' 
			borrow the parent as a whole, access and modify the parent,
			might be bad 
		'''
		self._write_test()
		# old_test = self.synt.testpath
		# self.synt.testpath = self.testfile ## begin
		start = self.subfunc.get_start_marking()
		end = self.subfunc.get_end_marking()
		self.synt.subtask_sgs = [StateGraph(self.synt.net, start=start, end=end)]
		sub_code = None
		for code in self.synt.enum_straight_code(firstline=self.subfunc, 
				stmrk=start, endmrk=end, rec_funcname=self.synt.name_of_syn_func()):
			if self.synt._test(code, self.func_name, testpath=self.testfile):
				sub_code = code
				break
		# self.synt.testpath = old_test ## end (if failed, this command may not run)
		return sub_code

class Synthesis(object):
	"""An instance of this class conducts a systhesis task for a Target Signature"""
	def __init__(self, sigtr_dict=None, sigtr_file=None, func_scores=None, enab_func_para=False):
		assert sigtr_dict or sigtr_file
		self.sigtr_dict = sigtr_dict if sigtr_dict else parse_json(sigtr_file)
		self.targetfunc = TargetFunc(self.sigtr_dict)
		if self.targetfunc is None:
			raise parseError('format for the target function is incorrect')
		self.net = PetriNet('NET for ' + self.sigtr_dict['name'])
		dirs = self.sigtr_dict['libdirs']
		self.dirs = dirs if isinstance(dirs, list) else [dirs]
		self.enab_func_para = enab_func_para
		self.comps = None
		self.stategraphs = None
		self.subtask_sgs = None # state graphs for subgraphs
		self._synlen = 5
		self._construct_components()
		self.priority_dict = parse_json(func_scores) if func_scores else None
		self.accepting_subcode = None
		self.finished_subdict = None

		# attributes allowed to be changed
		self.tgttype = self.targetfunc.rtypes[0] # for only one return value
		self.start_marking = self.targetfunc.get_start_marking() 
		self.end_marking = self.targetfunc.get_end_marking()

		self._init_stats()
		self._config_output_paths()
	def _construct_components(self):
		'''establish component info'''
		assert self.comps is None
		self.comps = {}
		for comp in parse_multiple_dirs(self.dirs):
			if self.enab_func_para or not has_func_para(comp['paramTypes']):
				self.add_component_to_net(comp)
		# self.comps[self.targetfunc.name] = Component(self.sigtr_dict, self.net) # add self component
		self.add_component_to_net(self.sigtr_dict)
	def add_component_to_net(self, comp_dict):
		''' can be called by outside, add a component to the synthesis net '''
		assert self.stategraphs is None
		comp_id = func_id(comp_dict['name'], comp_dict.get('module', ''))
		self.comps[comp_id] = Component(comp_dict, self.net)
		assert comp_id == self.comps[comp_id].id()
	def name_of_syn_func(self):
		return self.targetfunc.name
	def _init_stats(self):
		self.sketch_counter = itertools.count(0)
		self.enum_counter = itertools.count(0)
		self.brch_counter = itertools.count(1)
		self.part_counter = itertools.count(1)
		self.syn_start_time = time.clock()
		self.sum_test_time = 0
	def _config_output_paths(self):
		self.outpath = 'out/'
		self.drawpath = 'draws/'
		try_mkdir(self.outpath)
		try_mkdir(self.drawpath)

	def _build_graph(self, sg):
		''' wrapper for building the complete reachability graph, 
			DECREPATATED because no need construct whole reachability graph '''
		start = time.clock()
		sg.build()
		print('state graph(' + str(len(sg)) + ' states) build time:', time.clock() - start)
	def setup(self):
		'''build up state graph according to the start'''
		self.stategraphs = [StateGraph(self.net, start=self.start_marking, end=self.end_marking)]
		# self._build_graph(self.stategraphs[0])
	def set_syn_len(self, max_len):
		self._synlen = max_len		

	def _branch_out(self, brchlist, brch):
		'''
			create a new branch that does the subtask of synthesis
			(a branch of pattern matching) 
		'''
		newbrch_id = next(self.brch_counter)
		newbrch = SynBranch(self, brch, brchlist, brch)
		brchlist.append(newbrch)
		return newbrch
	
	def syn_subtask(self, sub_dict, middle_tests):
		''' 
			Called by outside to synthesize a subtask of the whole task;
			if successful, add new syn'ed function to the petri net 
			and update stategraph 
		'''
		sub_name = self.name_of_syn_func() + '_sub' + str(next(self.part_counter))
		subdict_copy = sub_dict.copy() # for later check
		sub_dict['name'] = sub_name
		subfunc = SubFunc(sub_dict)
		synpart = SynPart(self, subfunc, middle_tests)
		accepting_subcode = synpart.get_subtask_code()
		if not accepting_subcode:
			return None
		assert len(self.stategraphs) == 1 and self.stategraphs[0].steps_explored == 0
		self.comps[sub_name] = Component(sub_dict, self.stategraphs[0].net)
		# print(self.stategraphs, '\n', self.stategraphs[0].net.transition())
		for sg in self.stategraphs:
			# update reachability graph 
			# (create edges connected by the transition of the subfunc)
			sg.update_with_func(sub_name)
		if self.accepting_subcode is None:
			self.accepting_subcode = []
		self.accepting_subcode.append((sub_name, accepting_subcode)) # make it a tuple
		if self.finished_subdict is None:
			self.finished_subdict = []
		self.finished_subdict.append(subdict_copy)
		return accepting_subcode
	def subfunc_syned(self, subdict):
		if self.finished_subdict is None:
			return False
		for sd in self.finished_subdict:
			if subdict == sd:
				return True
		return False

	def resume_syn(self):
		''' resume synthesis after getting the solution for middle results '''
		print('==========================  resume synthesis  ==============================')
		assert len(self.accepting_subcode) == 1
		subcode_id, subcode = self.accepting_subcode[-1]
		sublen = len(subcode) - 2 # assume straight program without considering clone
		tosync_name = self.name_of_syn_func()
		print(subcode_id)
		testfile = self.sigtr_dict['testpath']
		try:
			for code in self.enum_straight_code(firstline=self.targetfunc, 
					stmrk=self.start_marking, endmrk=self.end_marking, 
					rec_funcname=tosync_name, midfun=subcode_id, 
					midfun_len=sublen):
				compound_code = subcode + code
				if self._test(compound_code, self.name_of_syn_func(), testpath=testfile):
					print('SUCCEEDED!!!')
					return compound_code
		except KeyboardInterrupt:
			self.statistics()
		self.statistics()

	def start(self, enab_brch=True):
		'''interface for outside'''
		self.testpath = self.sigtr_dict['testpath']
		id_cand = self.targetfunc.id_func_variables() # arguments in signature having target type
		start_time = time.clock()
		try:
			for code_snippet in self.enum_concrete_code(self.targetfunc, id_cand, 
						brchout=enab_brch, rec_funcname=self.targetfunc.name):
				if self._test(code_snippet, self.targetfunc.name):
					print('SUCCEEDED!!! ')
					self.statistics()
					return code_snippet
				test_time = time.clock() - start_time
				print('Failed: Time to evaluate this proposal', test_time)
				self.sum_test_time += test_time
				if PAUSE:
					input("PRESS ENTER TO CONTINUE.\n")
				start_time = time.clock()
		except KeyboardInterrupt as kbi:
			print('Synthesis Interrupted')
			self.statistics()
			raise kbi
		print('FAILED...')
		self.statistics()
	def _test(self, totest, outfilename, testpath=None):
		'''compile/test the code against user-provided tests'''
		testpath = testpath if testpath else self.testpath
		outpath = self.outpath + outfilename + '.ml'
		utility.make_dir_for_file(outpath)
		self._write_out(totest, testpath, outpath)
		test_command = ['ocaml', outpath]
		subproc = subprocess.Popen(test_command, stdout=subprocess.PIPE)
		result = subproc.communicate()[0]
		return b'true' == result
	def _write_out(self, code_snippet, testpath, outpath):
		'''write the completed code into a file'''
		with open(outpath, 'w') as targetfile:
			targetfile.write('exception Syn_exn\n\n')
			for line in code_snippet:
				targetfile.write(line + '\n')
			with open(testpath) as test:
				targetfile.write(test.read())
	def id_codes(self, firstline, varpool):
		'''yield functions that return one of the parameters(in signature or branch)'''
		for para in varpool:
			sklines = [firstline]
			sklines.append(SketchLine(None, [], [(0, self.tgttype)])) # single hole
			formatter = SketchFormatter(sklines)
			lines = formatter.format_out({0:para})
			print_sketch(lines)
			next(self.enum_counter)
			yield lines
	def enum_branched_codes(self):
		print('--- START OF BRANCH ENUMERATING ---')
		list_args = self.targetfunc.paras_of_list_type()
		for arg, t in list_args:
			# assume t as a string has the formate: 'a list
			elemtype, _ = t.split(' ')
			branchings = []
			branchings.append(Branch(self.targetfunc, (arg, t), []))
			branchings.append(Branch(self.targetfunc, (arg, t), [('hd', elemtype),('tl', t)]))
			combined = [self.targetfunc.sketch()] # not good?
			combined.append(branchings[0].matchline)
			synbrchs = [] # life span: only lives in the branch enumeration phrase (may cause problem, maybe a good idea)
			for b in branchings:
				self._branch_out(synbrchs, b)
				partial_sketch = synbrchs[-1].get_accepting_partial()
				if partial_sketch is None:
					combined = None
					break
				print('$$branch', b, 'synthesized successfully\n')
				combined.extend(partial_sketch)
			if combined is None:
				break
			print('++++++Success in Brach Enumerating+++++++')
			yield combined
	def enum_concrete_code(self, firstline, id_varpool=[], stmrk=None, brchout=True, rec_funcname=None):
		''' 
		enumerate completed sketch, called from Synthesis object that stands alone or allowed by synbranch
		concrete sketch example:
				let make_string arg0 arg1 = # firstline, can also be pattern matching (firstline, stmrk)
					# the body can be id function (id_varpool)
					let v0 = Char.uppercase_ascii arg1 in # (sequence determined by strmk)
					let v1 = String.make arg0 v0 in
					v1 # variable with target type

		strategy: check id function first; then if possible, try branch before straight-line code
		'''
		yield from self.id_codes(firstline, id_varpool)
		print('--- END OF ID SKETCH ---')
		if brchout:
			yield from self.enum_branched_codes()
			print('--- END OF BRANCH ENUMERATING ---')
		print('--- START OF STRAIGHT ENUMERATING ---')
		if stmrk is None:
			stmrk = self.targetfunc.get_start_marking()
		yield from self.enum_straight_code(firstline=firstline, stmrk=stmrk, rec_funcname=rec_funcname)

	def enum_straight_code(self, firstline, stmrk=None, endmrk=None, rec_funcname=None, 
			midfun=None, midfun_len=None):
		for sk, skformatter in self._enum_straight_sketch(firstline, stmrk, endmrk, 
				rec_funcname, midfun, midfun_len):
			print(' ~sketche with holes~ ')
			print_sketch(skformatter.format_out())
			next(self.sketch_counter)
			# branch: recursive call restriction

			for concrtsk in sk.enum_subst():
				print('--->')
				concretelines = skformatter.format_out(concrtsk)
				print_sketch(concretelines)
				next(self.enum_counter) # count sketch
				yield concretelines

	def _enum_straight_sketch(self, firstline, stmrk, endmrk=None, rec_funcname=None, 
			midfun=None, midfun_len=None):
		''' enumerate non-complete sketches(with holes), build stategraph if necessary '''
		def enum_straight(stategraph, start_marking, end_marking):
			''' helper for the outer function, call interface from the search plugin '''
			for seq in stategraph.enumerate_sketch_l(stmrk=start_marking, endmrk=end_marking, 
					max_depth=self._synlen, func_prio=self.priority_dict):
				if rec_funcname is not None and rec_funcname in seq:
					continue
				try:
					sketch = self._gen_sketch(seq, firstline)
					print(seq)
					yield sketch
				except ConstraintError:
					pass # ignore sketches that cannot be concretized
		def enum_through(stategraph, start_marking, end_marking):
			for seq in stategraph.enum_with_part(start_marking, end_marking, midfun,
					midfun_len, self._synlen, self.priority_dict):
				# TODO: copy & paste, should change
				if rec_funcname is not None and rec_funcname in seq:
					continue
				try:
					sketch = self._gen_sketch(seq, firstline)
					print(seq)
					yield sketch
				except ConstraintError:
					pass
		enum = enum_through if midfun else enum_straight
		graphpool = self.subtask_sgs if isinstance(firstline, SubFunc) else self.stategraphs
		for sg in graphpool:
			if stmrk in sg:
				yield from enum(sg, stmrk, endmrk)
				return
		print('<build new graph> new start:', stmrk)
		# In the new graph, endmark might not be reachable from startmark <- exception will be thrown
		graphpool.append(StateGraph(self.net, start=stmrk, end=self.end_marking))
		yield from enum(graphpool[-1], stmrk, endmrk)

	def _gen_sketch(self, sequence, firstline):
		'''create Sketch object for completion and SketchFormatter for output'''
		assert isinstance(sequence, list) # check the sequence
		counter = itertools.count(0)
		var_gen = var_generator()
		lines = []
		lines.append(firstline) # should be modified to append branch argument
		rec_holes = []
		for f in sequence:
			if f.startswith('clone_'): # watchout: mind the name confilction 
				continue
			func_id = restore_id(f) # recover the name of the function from ground tag
			subst = dict(zip(ext_syms_list(self.comps[func_id].io_types()), ground_terms(f)))
			vartypes = [instantiate(t, subst) for t in self.comps[func_id].rtypes]
			holetypes = [instantiate(t, subst) for t in self.comps[func_id].param_types()]

			variables = [('_' if rt == 'unit' else next(var_gen), rt) for rt in vartypes] # ocaml specific: unit type
			holenames = [next(counter) for i in range(self.comps[func_id].input_len())]
			holes = list(zip(holenames, holetypes))
			skline = SketchLine(self.comps[func_id], variables, holes)
			lines.append(skline)
			if f == self.targetfunc.name: # record the holes associated with recursive calls
				rec_holes.append(holes)
		return_holes = [next(counter) for _ in range(self.targetfunc.output_len())] # set up return line
		retline = SketchLine(None, [], list(zip(return_holes, self.targetfunc.rtypes)))
		lines.append(retline)
		sk = Sketch(lines)
		if len(rec_holes) > 0:
			sk.add_rec_constraints(rec_holes, firstline)
		return sk, SketchFormatter(lines)
	def _confine_rec_holes(self):
		''' yet not defined '''
		pass
	def statistics(self):
		"""show statistics after synthesis"""
		print('|---------------------- STATISTICS --------------------------|')
		print('Synthesis Time(printing included): {0}s'.format(time.clock() - self.syn_start_time))
		print(next(self.sketch_counter), 'sketches enumerated')
		num_concrete = next(self.enum_counter)
		print(num_concrete, 'concrete code snippets enumerated')
		print('Average enumeration time: {0}s'.format(self.sum_test_time / num_concrete))
		print('Number of states explored for each stategraph:')
		for sg in self.stategraphs:
			print(sg.num_states_explored())
		print('|------------------------------------------------------------|')

	def print_comps(self):
		''' print components of the Synthesis instance, for debug '''
		for i, c in enumerate(self.comps.values()):
			print(i, c)
	def draw_net(self):
		''' draw the clean Petri net right after loading the specified libraries '''
		numnode = len(self.net._place) + len(self.net._trans) # for convenience
		if numnode > 200:
			print('*************** Warning: PetriNet too large(' + str(numnode) 
				+ ' nodes), drop drawing ***************')
			return
		self.net.draw(self.drawpath + self.targetfunc.name + '.eps')
	def draw_augmented_net(self):
		''' draw the Petri net where transitions are contrained and
			clone transitions are added
		'''
		assert self.stategraphs is not None
		print('stategraphs[0] start:', self.stategraphs[0][0])
		self.stategraphs[0].goto(0)
		self.stategraphs[0].net.draw(self.drawpath + self.targetfunc.name + '_aug.eps')
	def draw_state_graph(self):
		self.stategraphs[0].draw(self.drawpath + self.targetfunc.name + '_sg.eps')

	def draw_alpha(self, filename=None, relevant=False):
		''' draw the simple-graph reachability graph '''
		if filename is None:
			filename = self.targetfunc.name
		useful_places = self.stategraphs[0].useful_places
		graph = self.net.construct_alpha_graph()
		attr = dict(style="invis", splines="true")
		todraw = snakes.plugins.gv.Graph(attr)
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
