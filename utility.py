from os import listdir
from data import *
import json
import itertools

first_elem_of_tuple = lambda x: x[0]

def parse_multiple_dirs(dirs):
	l = []
	for dir in dirs:
		l.extend(parse_dir(dir))
	return l

def parse_dir(dir):
	if dir[-1] != '/':
		dir += '/'
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
		print('value error parsing', ":", ve)
	finally:
		f.close()
	return result

def var_generator():
	cur = 0
	while True:
		yield 'v' + str(cur)
		cur += 1

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
