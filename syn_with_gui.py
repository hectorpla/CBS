from tkinter import *
from synthesis import *
from os import mkdir

class FiledError(Exception):
	pass

class App(Frame):
	def __init__(self, master=None):
		super().__init__(master)
		self.test_entries = []
		self.active_tests = 0
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
		self.name_entry = Entry(self.left_input_sub_panel, text='Please input name of the function')
		self.name_entry.grid(row=0, column=1)
		
		para_label = Label(self.left_input_sub_panel, text='Function parameters(separated by ";")')
		para_label.grid(row=1, column=0)
		self.para_entry = Entry(self.left_input_sub_panel, text='', width=30)
		self.para_entry.grid(row=1, column=1)

		para_type_label = Label(self.left_input_sub_panel, text='Parameter types (separated by ";")')
		para_type_label.grid(row=2, column=0)
		self.para_type_entry = Entry(self.left_input_sub_panel, text='', width=30)
		self.para_type_entry.grid(row=2, column=1)

		return_type_label = Label(self.left_input_sub_panel, text='Return type')
		return_type_label.grid(row=3, column=0)
		self.return_type_entry = Entry(self.left_input_sub_panel)
		self.return_type_entry.grid(row=3, column=1)

		libs_label = Label(self.left_input_sub_panel, text='Libraries(separated by ";")')
		libs_label.grid(row=4, column=0)
		self.libs_entry = Entry(self.left_input_sub_panel, width=30)
		self.libs_entry.grid(row=4, column=1)

	def create_right_panel(self):
		self.rightframe = Frame(self, width=300, height=400)
		self.rightframe.pack(side='right')
		self.rightframe.pack_propagate(0)

		self.testframe = LabelFrame(self.rightframe, text='Test Cases', width=30, height=500)
		self.testframe.pack()

		test_example = Label(self.testframe, text='stutter [1;2] [] = [1;1;2;2]')
		# test_example.grid(row=0, column=0)
		test_example.pack(side='top')

		def add_test():
			if self.active_tests < len(self.test_entries):
				self.test_entries[self.active_tests][0].pack(side='top')
			elif self.active_tests < 10:
				self.test_entries.append((Entry(self.testframe, width=250), StringVar()))
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
		set_len_frame.pack()
		set_len_label = Label(set_len_frame, text='Program length')
		set_len_label.grid(row=0, column=0)
		self.set_len_entry = Entry()
		self.set_len_entry.grid(row=0, column=1)
		def set_len():
			try:
				self.syn_len = int(self.set_len_entry.get())
			except ValueError:
				pass
		set_len_button = Button(set_len_frame, text='Set length', command=set_len)
		set_len_button.grid(row=0, column=2)

	def start_synthesis(self):
		self.sigtr_dict = {}
		def read_sigt_info():
			extract_list = lambda lst : list(map(str.strip, lst.split(';')))
			self.sigtr_dict['name'] = self.name_entry.get().strip()
			self.sigtr_dict['paramNames'] = extract_list(self.para_entry.get())
			self.sigtr_dict['paramTypes'] = extract_list(self.para_type_entry.get())
			self.sigtr_dict['libdirs'] = extract_list(self.libs_entry.get())
			self.sigtr_dict['tgtTypes'] = extract_list(self.return_type_entry.get())
			print(self.sigtr_dict)
			# check valid synthesis parameter
			if any([e == '' for e in self.sigtr_dict.values()]):
				self.errmsg.set('Some of the fields are empty')
				raise FiledError()
			if len(self.sigtr_dict['paramNames']) != len(self.sigtr_dict['paramTypes']):
				self.errmsg.set('Lengths of parameters and types do not agree')
				return FiledError()
		try:
			read_sigt_info()
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
		synt.set_syn_len(self.syn_len)
		solution = synt.start()
		if solution:
			self.codeview.delete(1.0, END)
			for line in solution:
				self.codeview.insert(END, line + '\n')

root = Tk('OCaml Program Synthesis')
root.geometry("900x600")
app = App(master=root)
app.mainloop()
