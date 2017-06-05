import synthesis
import subprocess
import utility
import os
import re

class TEfixer(object):
	def __init__(self, type_info_file, prog=None, progfile=None):
		''' expect the prog be a file or lines of code as strings; position be the line range; 
			type_info and test in .json file
		'''
		assert progfile or prog
		self.prog = prog
		if prog is None:
			with open(progfile, 'r') as f:
				self.prog = f.read()
		type_info = utility.parse_json(type_info_file)
		print(type_info)
		self.synt = synthesis.Synthesis(type_info)
		# self.bugpos = self.parse_pos(type_info['position'])
		self.prog_name = progfile.split('/')[-1].split('.')[0] + '_fixed' if progfile \
			else type_info['name']
	# def parse_pos(self, posstr):
	# 	start, end = posstr.split(',')
	# 	return (int(start), int(end))
	def fix(self):
		self.synt.setup()
		self.synt.draw_augmented_net()
		self.synt.draw_state_graph()
		fix_dir = 'out/fix/'
		try:
			os.mkdir(fix_dir)
		except FileNotFoundError:
			os.mkdir(fix_dir.split('/')[0])
		except FileExistsError:
			pass
		for fixedcode in self.get_fixed_codes():
			if self._test(fixedcode, fix_dir + self.prog_name):
				break

	def _split_code_by_questionmark(self, prog):
		''' find the ?? (where the fixed code would fill) and return code segment before and after that '''
		return re.findall(r'(.*)\?\?(.*)', prog, flags=re.DOTALL)[0]
		# return first.split('\n'), second.split('\n')

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
		first, second = self._split_code_by_questionmark(self.prog)	
		for code in self.synt.enum_concrete_code(firstline=self.synt.targetfunc, rec_funcname=self.prog_name):
			# fixedpart = '(' + ' '.join(code[1:]) + ')' # not correct if the syn'ed code is a recursive func
			prog = []
			prog.append(first)
			prog.append("(* syn'd *) (")
			prog.extend(code[1:]) # vulnerable
			prog.append(") (* syn'd *)")
			prog.append(second)
			yield prog
