from tkinter import *
from synthesis import *
from os import mkdir

class FiledError(Exception):
	pass

def decode_string(string):
	temp = string.strip(' \'\"')
	return bytes(temp, "utf-8").decode("unicode_escape")

def select_from_list(lst, selector):
	''' note: this function return a map object '''
	assert isinstance(lst, list) and isinstance(selector, list)
	return map(lst.__getitem__, selector)

class App(Frame):
	def __init__(self, master=None):
		super().__init__(master)
		self.sigtr_dict = None
		self.test_entries = []
		self.active_tests = 0
		self.max_active = 10
		self.midtest_entries = []

		self.midtestframe = None

		self.pack()
		self.create_left_panel()
		self.create_right_panel()

		# synthesis parameters
		self.syn_len = 6
	def create_left_panel(self):
		self.leftframe = Frame(self, width=500, height=600)
		self.leftframe.pack_propagate(0)
		self.leftframe.pack(side='left')

		self.codeview = Text(self.leftframe, width=60, height=25)
		self.codeview.insert(INSERT, 'Synthesized code...')
		self.codeview.grid(row=0, column=0)
		# self.codeview.pack(side='top')

		self.errorview = LabelFrame(self.leftframe, text='Error Message')
		self.errorview.grid(row=1, column=0)
		self.errmsg = StringVar()
		self.errmsg_label = Label(self.errorview, text='To show error...', 
			textvariable=self.errmsg, width=60)
		self.errmsg_label.pack()

		self.left_input_sub_panel = Frame(self.leftframe)
		self.left_input_sub_panel.grid(row=2, column=0)

		# input entries
		name_label = Label(self.left_input_sub_panel, text='Function name:')
		name_label.grid(row=0, column=0)
		self.name_entry = Entry(self.left_input_sub_panel, text='Please input name of the function:')
		self.name_entry.grid(row=0, column=1)
		
		para_label = Label(self.left_input_sub_panel, text='Function parameters(separated by ";"):')
		para_label.grid(row=1, column=0)
		self.para_entry = Entry(self.left_input_sub_panel, text='', width=30)
		self.para_entry.grid(row=1, column=1)

		para_type_label = Label(self.left_input_sub_panel, text='Parameter types (separated by ";"):')
		para_type_label.grid(row=2, column=0)
		self.para_type_entry = Entry(self.left_input_sub_panel, text='', width=30)
		self.para_type_entry.grid(row=2, column=1)

		return_type_label = Label(self.left_input_sub_panel, text='Return type:')
		return_type_label.grid(row=3, column=0)
		self.return_type_entry = Entry(self.left_input_sub_panel)
		self.return_type_entry.grid(row=3, column=1)

		libs_label = Label(self.left_input_sub_panel, text='Libraries(separated by ";"):')
		libs_label.grid(row=4, column=0)
		self.libs_entry = Entry(self.left_input_sub_panel, width=30)
		self.libs_entry.grid(row=4, column=1)

	def create_right_panel(self):
		self.rightframe = Frame(self, width=380, height=550)
		self.rightframe.pack(side='left')
		self.rightframe.pack_propagate(0)

		self.testframe = LabelFrame(self.rightframe, text='Test Cases', width=30, height=500)
		self.testframe.pack()

		test_example = Label(self.testframe, text='Example: stutter [1;2] = [1;1;2;2]')
		# test_example.grid(row=0, column=0)
		test_example.pack(side='top')

		def add_test():
			if self.active_tests < len(self.test_entries):
				self.test_entries[self.active_tests][0].pack(side='top')
			elif self.active_tests < self.max_active:
				self.test_entries.append((Entry(self.testframe, width=300), StringVar()))
				ent, content = self.test_entries[-1]
				ent['textvariable'] = content
				content.set('test ' + str(len(self.test_entries)))
				ent.pack(side='top')
			else:
				print('active tests:', self.active_tests)
				return
			self.active_tests += 1
		add_test() # add one test initially

		def delete_test():
			if self.active_tests < 2:
				return
			self.test_entries[self.active_tests-1][0].pack_forget()
			self.active_tests -= 1

		# button groups
		self.add_button = Button(self.rightframe, text='Add test', command=add_test)
		self.add_button.pack(side='bottom')
		self.delete_button = Button(self.rightframe, text='Delete test', command=delete_test)
		self.delete_button.pack(side='bottom')
		self.clear_button = Button(self.rightframe, text='Clear text', 
			command=lambda: self.codeview.delete(1.0, END))
		self.clear_button.pack(side='bottom')
		self.syn_button = Button(self.rightframe, text='Start synthesis', command=self.start_synthesis)
		self.syn_button.pack(side='bottom')
		
		set_len_frame = Frame(self.rightframe)
		set_len_frame.pack(side='bottom')
		set_len_label = Label(set_len_frame, text='Program length')
		set_len_label.grid(row=0, column=0)
		self.set_len_entry = Entry(set_len_frame, width=3)
		self.set_len_entry.grid(row=0, column=1)
		def set_len():
			try:
				self.syn_len = int(self.set_len_entry.get())
			except ValueError:
				pass
		set_len_button = Button(set_len_frame, text='Set length', command=set_len)
		set_len_button.grid(row=0, column=2)

		importframe = Frame(self.rightframe)
		importframe.pack(side='bottom')
		import_entry = Entry(importframe)
		import_entry.grid(row=0, column=0)
		def import_json():
			def set_text(ent, text):
				ent.delete(0, END)
				ent.insert(0, text)
			try:
				filename = import_entry.get()
				sigtr = parse_json('signatures/' + filename)
				list2string = lambda lst : '; '.join(lst)
				set_text(self.name_entry, sigtr['name'])
				set_text(self.para_entry, list2string(sigtr['paramNames']))
				set_text(self.para_type_entry, list2string(sigtr['paramTypes']))
				set_text(self.return_type_entry, sigtr['tgtTypes'])
				set_text(self.libs_entry, 
					list2string(sigtr['libdirs']) if isinstance(sigtr['libdirs'], list) else sigtr['libdirs'])
			except Exception as e:
				print(e)
			with open(sigtr['testpath'], 'r') as testfile:
				testcases = re.findall(r'try\((.*?)\)', testfile.read()) # match test wrapped by "try()"
				for _ in range(self.active_tests - len(testcases)):
					delete_test()
				for i, testcase in enumerate(testcases):
					if i > self.max_active - 1:
						return
					if self.active_tests <= i:
						add_test()
					set_text(self.test_entries[i][0], testcase)
		import_button = Button(importframe, text='Import json file', command=import_json)
		import_button.grid(row=0, column=1)

		midtest_button = Button(self.rightframe, text='Add middle tests', command=self.create_mid_test_panel)
		midtest_button.pack(side='bottom')

		syn_part_button = Button(self.rightframe, text='Syn Part', command=self.synthesize_nested_function)
		syn_part_button.pack(side='bottom')

	def create_mid_test_panel(self):
		if self.midtestframe:
			return
		self.midtestframe = LabelFrame(self, text='Middle tests', width=320, height=300)
		self.midtestframe.pack(side='top')

		examplelb = Label(self.midtestframe, text='Examples: 0; 2; "10/2"')
		examplelb.pack(side='top')

		argspecframe = Frame(self.midtestframe)
		argspecframe.pack(side='top')
		argspeclb = Label(argspecframe, text='arg#:')
		argspeclb.grid(row=0, column=0)
		self.argspec_entry = Entry(argspecframe)
		self.argspec_entry.insert(0, 'specify argument number')
		self.argspec_entry.grid(row=0, column=1)

		for _ in range(self.max_active):
			self.midtest_entries.append(Entry(self.midtestframe))
			self.midtest_entries[-1].pack(side='top')

	def read_sigt_info(self):
		self.sigtr_dict = {}
		extract_list = lambda lst : list(map(str.strip, lst.split(';')))
		self.sigtr_dict['name'] = self.name_entry.get().strip()
		self.sigtr_dict['paramNames'] = extract_list(self.para_entry.get())
		self.sigtr_dict['paramTypes'] = extract_list(self.para_type_entry.get())
		self.sigtr_dict['libdirs'] = extract_list(self.libs_entry.get())
		self.sigtr_dict['tgtTypes'] = extract_list(self.return_type_entry.get())
		print(self.sigtr_dict)
		# check valid synthesis parameter
		if any([e == '' or e == [''] for e in self.sigtr_dict.values()]):
			self.errmsg.set('Some of the fields are empty')
			raise FiledError()
		if len(self.sigtr_dict['paramNames']) != len(self.sigtr_dict['paramTypes']):
			self.errmsg.set('Lengths of parameters and types do not agree')
			raise FiledError()



	def get_inputs(self, selector):	
		selected = select_from_list(self.test_entries, selector)
		io_series = (e[0].get().split('=') for e in selected)
		lhs, rhs = [], []
		for l, _ in io_series:
			lhs.append(list(map(decode_string, l.split()[1:]))) # BUG: space in string!!!
			# rhs.append(r.strip())
		return lhs

	def synthesize_nested_function(self):
		if not self.sigtr_dict:
			self.read_sigt_info()
		try:
			spec_args = list(map(lambda x:int(x.strip()), self.argspec_entry.get().split(';')))
			midtest_inputs = [decode_string(e.get()) for e in self.midtest_entries]
			effective_list = [i for i in range(self.max_active) if midtest_inputs[i] != '']
			middle_results = list(select_from_list(midtest_inputs, effective_list))
		except Exception as e:
			print(e)
			return
		selected_inputs = self.get_inputs(effective_list)
		# select horizontally
		selected_argslist = [list(select_from_list(arglist, spec_args)) for arglist in selected_inputs]
		print(selected_argslist)

	def start_synthesis(self):
		try:
			self.read_sigt_info()
		except FiledError:
			return
		folder = 'test'
		test_file = folder + '/' + self.sigtr_dict['name'] + '.ml'

		def write_test():
			try:
				mkdir(folder)
			except FileExistsError:
				pass
			with open(test_file, 'w') as f:
				for i, test_entry in enumerate(self.test_entries[:self.active_tests]):
					f.write('let test{0} = try('.format(i))
					f.write(test_entry[1].get())
					f.write(') with Syn_exn -> true\n')
				f.write('let _ = print_string (string_of_bool ({0}))\n'.\
					format(' && '.join(['test' + str(i) for i in range(self.active_tests)])))
		def read_test_info():
			write_test()
			self.sigtr_dict['testpath'] = test_file
		read_test_info()

		self.errmsg.set('')
		score = 'json/scores.json'
		synt = Synthesis(sigtr_dict=self.sigtr_dict, func_scores=score)
		synt.setup()
		print('Program length:', self.syn_len)
		synt.set_syn_len(self.syn_len)
		try:
			solution = synt.start()
		except snakes.plugins.search.CannotReachErrorr as cre:
			self.errmsg.set(cre)
			return
		if solution:
			self.codeview.delete(1.0, END)
			for line in solution:
				self.codeview.insert(END, line + '\n')

root = Tk('OCaml Program Synthesis')
root.geometry("1100x600")
app = App(master=root)
app.mainloop()
