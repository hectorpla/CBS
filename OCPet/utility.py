from os import listdir
import json
import itertools
import re

first_elem_of_tuple = lambda x: x[0]
second_elem_of_tuple = lambda x: x[1]

def cap_initial(s):
	return str.upper(s[0]) + s[1:]
def func_id(module, name):
	if len(module) == 0:
		return name
	return cap_initial(module) + '.' + name

# parsing utility
def parse_multiple_dirs(dirs):
	l = []
	for dir in dirs:
		l.extend(parse_dir(dir))
	return l

def parse_dir(dir):
	if dir[-1] != '/':
		dir += '/'
	# try:
	# 	listdir(dir)
	m = map(lambda file: parse_json(dir + file), listdir(dir))
	return [e for e in m if e is not None]

def parse_json(file):
	# print('parsing file:', file)
	result = None
	try:
		f = open(file, 'r')
		serial = f.read()
		result = json.loads(serial)
		f.close()
	except IOError as ioe:
		print('IO error: ', ioe)
	except ValueError as ve:
		print('value error parsing ' + file, ":", ve)
	return result

# utilities for z3
def var_generator():
	cur = 0
	while True:
		yield 'v' + str(cur)
		cur += 1
def is_variable(name):
	return name.startswith('v') and all(map(str.isdigit, name[1:]))

def sep_join(tuplelist, sep=' '):
	'''used for generating parameter lists
	input: [(paraName, paraType), ...]'''
	assert len(tuplelist[0]) == 2
	return sep.join(map(first_elem_of_tuple, tuplelist))

def comma_join(tuplelist):
	return sep_join(tuplelist, ', ')

def hypo_var_gen(hole, var):
	return 'h_' + str(hole) + '_' + var

def decompose_hypo_var(hypo_name):
	decomposed = hypo_name.split('_')
	return int(decomposed[1]), decomposed[2]

def last_component(path):
	return [c for c in path.split('/') if c is not ''][-1]

def print_sketch(sketch):
	for line in sketch:
		print(line)

# utility for generic grounding
RE_GENERICS = "'[a-z][0-9a-z]*"

def decompose_types(tobreak):
	return tobreak.split(' -> ')
def recompose_types(components):
	return ' -> '.join(components)
def ext_symbols(tstring):
	return set(re.findall(RE_GENERICS, tstring))
def ext_syms_list(tlist):
	syms = set()
	for t in tlist:
		syms |= ext_symbols(t)
	return sorted(syms) # sorted to made the order guarantee
class BindRepl(object):
	def __init__(self, mapping):
		self.mapping = mapping
	def __call__(self, matchobj):
		return self.mapping[matchobj.group(0)]
def instantiate(gtype, subst):
	assert isinstance(gtype, str)
	bindrepl = BindRepl(subst)
	return re.sub(RE_GENERICS, bindrepl, gtype)
def instantiate_generics(tlist, typepool):
	''' given all types in a function as a list, 
		return the grounded types and symbol bindings
	'''
	assert isinstance(typepool, list)
	symbols = ext_syms_list(tlist)
	if len(symbols) == 0:
		yield tlist, {}
		return # mind python version
	selections = itertools.combinations_with_replacement(typepool, len(symbols))
	for sel in selections:
		subst = dict(zip(symbols,sel))
		bindrepl = BindRepl(subst)
		yield [instantiate(t, subst) for t in tlist], subst # not good?

GROUND_SEP = '-'
def func_id_in_petri(orig, subst):
	''' example: 
			val map : ('a -> 'b) -> 'a list -> 'b list with substitution {'a:int, 'b:bool}
	    	-> map_int_bool
	'''
	sublist = sorted(subst.items()) 
	return GROUND_SEP.join(itertools.chain([orig], map(second_elem_of_tuple, sublist)))

def ground_terms(composite_id):
	''' retrieve the binding info from the tagged id of a grounded function
		example:
			from map_int_bool, extract binding [('a:)int, ('b:)bool]
		Note: should merge with function restore_id
	'''
	return composite_id.split(GROUND_SEP)[1:]

def restore_id(composite_id):
	'''reverse the process of giving a generic function with specific id in the petri net'''
	return composite_id.split(GROUND_SEP)[0]

def has_func_para(types):
	for t in types:
		if '->' in t:
			return True
	return False

# write test to file
def write_tests_tofile(lines, f):
	for test_num, test in enumerate(lines):
		f.write('let test{0} = try('.format(test_num))
		f.write(test)
		f.write(') with Syn_exn -> true\n')
	f.write('let _ = print_string (string_of_bool ({0}))\n'.\
		format(' && '.join(['test' + str(i) for i in range(test_num+1)])))
