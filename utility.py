import json
from os import listdir
from data import *

def construct_net(name, dir):
	net = PetriNet(name)
	components = dict(((comp[name], Component(comp, net)) for comp in parse_dir(dir)))
	return net, components

def parse_dir(dir):
	if dir[-1] != '/':
		dir += '/'
	m = map(lambda file: parse_json(dir + file), listdir(dir))
	return [e for e in m if e is not None]

def parse_json(file):
	result = None
	try:
		f = open(file, 'r')
		serial = f.read()
		result = json.loads(serial)
	except Exception as e:
		print('json parsing error: ', e)
	finally:
		f.close()
	return result
