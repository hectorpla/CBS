import synthesis
import subprocess
import utility
import os
import re

class TEfixer(object):
	def __init__(self, type_info_file, progfile=None, prog=None):
		''' expect the prog be a file or lines of code as strings; position be the line range; 
			type_info and test in .json file
		'''
		assert progfile or prog
		if progfile:
			with open(progfile, 'r') as f:
				self.prog = f.read()
			self.prog_name = progfile.split('/')[-1].split('.')[0] + '_fixed'
		else:
			self.prog = prog
			self.prog_name = self._extract_funcname(prog)
		self.type_info = utility.parse_json(type_info_file)	
		self.type_info['name'] = self.prog_name
		self.synt = synthesis.Synthesis(self.type_info)
		# print(self.type_info)
	def fix(self):
		funcname = self._extract_rec_funcname(self.prog)
		if funcname:
			self._add_rec_comp()
		self.synt.setup()
		self.synt.draw_augmented_net()
		self.synt.draw_state_graph()
		fix_dir = 'out/fix/'
		try:
			os.mkdir(fix_dir)
		except FileNotFoundError:
			os.mkdir(fix_dir.split('/')[0])
			os.mkdir(fix_dir)
		except FileExistsError:
			pass
		for fixedcode in self.get_fixed_codes():
			if self._test(fixedcode, fix_dir + self.prog_name):
				break

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
		''' find the ?? (where the fixed code would fill) and return code segment before and after that '''
		return re.findall(r'(.*)\?\?(.*)', prog, flags=re.DOTALL)[0]
	def _add_rec_comp(self):
		''' add the funciton to fix as a component to the synthesis instance '''
		try:
			sgntr = self.type_info['tofix'] # field does not necessarily exist
			self.synt.add_component_to_net(sgntr)
		except KeyError:
			pass
	def _test(self, codelines, filename):
		outpath = filename + '.ml'
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
		for code in self.synt.enum_concrete_code(firstline=fst, id_varpool=fst.id_func_variables(),
				brchout=False, rec_funcname=self.prog_name): # brch enum disabled
			prog = []
			prog.append(front)
			prog.append("(* syn'd *) (")
			prog.extend(code[1:]) # not correct if the syn'ed code is a recursive func
			prog.append(") (* syn'd *)")
			prog.append(back)
			yield prog
