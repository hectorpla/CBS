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

# def gen_sketch(components, sequence):
# 	counter = itertools.count(0)
# 	var_gen = var_generator()
# 	sketch = []
# 	sketch.append('let func =')
# 	for f in sequence:
# 		if f.startswith('clone_'): # watchout: mind the name confilction 
# 			continue
# 		sketch.append('\t' + (components[f].sketch(var_gen, counter)[0]) + ' in') # sketch() return a tuple
# 	sketch.append('in #' + ', '.join([str(next(counter)) for _ in range(1)]))
# 	return sketch

def complete_sketch():
	pass