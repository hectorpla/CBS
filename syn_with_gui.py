from tkinter import *
# from tkinter.ttk import *

class App(Frame):
	def __init__(self, master=None):
		super().__init__(master)
		self.test_entries = []
		self.active_tests = 0
		self.pack()

		self.create_left_panel()
		self.create_right_panel()

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
		self.errmsg = Label(self.errorview, text='To show error...', width=60)
		self.errmsg.pack()

		self.left_input_sub_panel = Frame(self.leftframe)
		self.left_input_sub_panel.grid(row=2, column=0)
		# self.left_input_sub_panel.pack(side='bottom')


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

		self.testframe = LabelFrame(self.rightframe, text='Test Cases', width=30)
		self.testframe.pack()

		test_example = Label(self.testframe, text='stutter [1;2] [] = [1;1;2;2]')
		# test_example.grid(row=0, column=0)
		test_example.pack(side='top')


		def add_test():
			if self.active_tests < len(self.test_entries):
				self.test_entries[self.active_tests][0].pack(side='top')
				# print('pack...')
			elif self.active_tests < 10:
				self.test_entries.append((Entry(self.testframe, width=250), StringVar()))
				ent, content = self.test_entries[-1]
				ent['textvariable'] = content
				content.set('test ' + str(len(self.test_entries)))
				ent.pack(side='top')
				# print('append')
			else:
				print('active tests:', self.active_tests)
				return
			self.active_tests += 1
			# print('active tests:', self.active_tests)
		add_test() # add one test initially
		
		def delete_test():
			if self.active_tests < 2:
				return
			self.test_entries[self.active_tests-1][0].pack_forget()
			self.active_tests -= 1
			# print('active tests:', self.active_tests)

		self.add_button = Button(self.rightframe, text='Add test', command=add_test)
		self.add_button.pack(side='bottom')
		self.delete_button = Button(self.rightframe, text='Delete test', command=delete_test)
		self.delete_button.pack(side='bottom')
		self.syn_button = Button(self.rightframe, text='Start synthesis')
		self.syn_button.pack(side='bottom')

root = Tk()
root.geometry("900x600")
app = App(master=root)
app.mainloop()