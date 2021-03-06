import synthesis
import subprocess
import utility
import os
import re

class TEfixer(object):
	'''
		a client of the class Synthesis, using it to achieve 
		missing functionality in ??
	'''
	def __init__(self, type_info_file, progfile=None, prog=None):
		''' 
			expect the prog be a file or a string of code as strings;  
			position be the line range; type_info and test in .json file
		'''
		assert progfile or prog
		if progfile:
			with open(progfile, 'r') as f:
				self.prog = f.read()
			self.prog_name = progfile.split('/')[-1].split('.')[0] + '_fixed'
		else:
			self.prog = prog
			self.prog_name = self._extract_funcname(prog) + '_fixed' # dummy function name
		self.type_info = utility.parse_json(type_info_file)	
		self.type_info['name'] = self.prog_name
		self.synt = synthesis.Synthesis(self.type_info)
		# print(self.type_info)
	def fix(self):
		funcname = self._extract_rec_funcname(self.prog)
		if funcname:
			self._add_rec_comp()
		self.synt.print_comps()
		self.synt.setup()
		self.synt.draw_augmented_net()
		self.synt.draw_state_graph()
		fix_dir = 'fix/'
		outname = fix_dir + self.prog_name
		utility.make_dir_for_file(outname)
		if 'testpath' in self.__dict__:
			test = self.synt._test
		else:
			test = self._test
		# print(test, self.testpath)
		for fixedcode in self.get_fixed_codes():
			if test(fixedcode, outname, self.__dict__.get('testpath', '')):
				return fixedcode

	def set_testpath(self, path):
		self.testpath = path
	def _extract_funcname(self, prog):
		''' return the name of the function to fix '''
		name1 = re.search((r'let +(\w+)'), prog).group(1)
		name2 = self._extract_rec_funcname(prog)
		return name2 if name2 else name1
	def _extract_rec_funcname(self, prog):
		''' return the name of function to fix if it is recursive '''
		fn2 = re.search((r'let +rec +(\w+)'), prog)
		return fn2.group(1) if fn2 else None
	def _split_code_by_questionmark(self, prog):
		''' 
			find the ?? (where the fixed code would fill) 
			and return code segment before and after that 
		'''
		return re.findall(r'(.*)\?\?(.*)', prog, flags=re.DOTALL)[0]
	def _add_rec_comp(self):
		''' add the funciton to fix as a component to the synthesis instance '''
		# should know the knowledge of the whole picture to add recursive function
		try:
			sgntr = self.type_info['tofix'] # field does not necessarily exist, call debugger?
			self.synt.add_component_to_net(sgntr)
		except:
			pass

	def _test(self, codelines, filename, dummy=None):
		outpath = self.synt.outpath + filename + '.ml'
		with open(outpath, 'w') as targetfile:
			# targetfile.write('exception Syn_exn\n\n')
			for line in codelines:
				targetfile.write(line + '\n')
		test_command = ['ocaml', outpath]
		subproc = subprocess.Popen(test_command, stdout=subprocess.PIPE)
		return b'true' == subproc.communicate()[0]
	def get_fixed_codes(self):
		front, back = self._split_code_by_questionmark(self.prog)
		fst = self.synt.targetfunc
		# brch enum disabled, be careful of the recname
		for code in self.synt.enum_concrete_code(firstline=fst, id_varpool=fst.id_func_variables(),
				brchout=False, rec_funcname=self.prog_name): 
			prog = []
			prog.append(front)
			prog.append("(* syn'd *) (")
			prog.extend(code[1:]) # not correct if the syn'ed code is a recursive func
			prog.append(") (* syn'd *)")
			prog.append(back)
			yield prog
