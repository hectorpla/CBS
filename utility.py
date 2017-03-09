from os import listdir
from data import *
import json
import itertools

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

def comma_join(tuplelist):
	'''used for generating parameter lists
	input: [(paraName, paraType), ...]'''
	assert len(tuplelist[0]) == 2
	return ', '.join(map(lambda x: x[0], tuplelist))

def hypo_var_gen(hole, var):
	return 'h_' + str(hole) + '_' + var

def decompose_hypo_var(hypo):
	return hypo.split()[1:3]
