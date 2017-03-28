from os import listdir
# from data import *
import json
import itertools
import re

first_elem_of_tuple = lambda x: x[0]
second_elem_of_tuple = lambda x: x[1]

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
	except IOError as ioe:
		print('IO error: ', ioe)
	except ValueError as ve:
		print('value error parsing ' + file, ":", ve)
	finally:
		f.close()
	return result

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

RE_GENERICS = "'[a-z][0-9a-z]*"

def decompose_types(tobreak):
	return tobreak.split(' -> ')
def recompose_types(components):
	return ' -> '.join(components)
def ext_symbols(tstring):
	return set(re.findall(RE_GENERICS, tstring))
def ext_syms_list(tlist):
	result = set()
	for t in tlist:
		result |= ext_symbols(t)
	return result
class BindRepl(object):
	def __init__(self, mapping):
		self.mapping = mapping
	def __call__(self, matchobj):
		return self.mapping[matchobj.group(0)]
def instantiate_generics(tlist, typepool):
	'''given all types in a function as a list, return the grounded types'''
	assert isinstance(typepool, list)
	symbols = ext_syms_list(tlist)
	if len(symbols) == 0:
		yield tlist
		return # mind python version
	selections = itertools.combinations_with_replacement(typepool, len(symbols))
	for sel in selections:
		subst = dict(zip(symbols,sel))
		bindrepl = BindRepl(subst)
		yield [re.sub(RE_GENERICS, bindrepl, t) for t in tlist], subst # not good?
def func_id_in_petri(orig, subst):
	''' example: val map : ('a -> 'b) -> 'a list -> 'b list with substitution {'a:int, 'b:bool}
	    -> map_int_bool
	'''
	sublist = sorted(subst.items())
	return '_'.join(itertools.chain([orig], map(second_elem_of_tuple, sublist)))

def restore_id(composite):
	'''reverse the process of giving a generic function with specific id in the petri net'''
	return composite.split('_')[0]
