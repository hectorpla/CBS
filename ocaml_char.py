import snakes.plugins
snakes.plugins.load(["gv", "pos", "hello"], "snakes.nets", "snk")
from snk import *

import utility

pn = PetriNet('ocaml_char')
pn.add_place(Place('char'))
pn.add_place(Place('int'))
pn.add_place(Place('string'))

pn.add_transition(Transition('code'))
pn.add_input('char', 'code', Variable('c'))
pn.add_output('int', 'code', Expression('ord(c)'))

pn.add_transition(Transition('chr'))
pn.add_input('int', 'chr', Variable('c'))
pn.add_output('char', 'chr', Expression('chr(c)'))

pn.add_transition(Transition('escaped'))
pn.add_input('char', 'escaped', Variable('c'))
pn.add_output('string', 'escaped', Expression('repr(c)'))

pn.add_transition(Transition('lowercase_ascii'))
pn.add_input('char', 'lowercase_ascii', Variable('c'))
pn.add_output('char', 'lowercase_ascii', Expression('c.lower()'))

pn.add_transition(Transition('uppercase_ascii'))
pn.add_input('char', 'uppercase_ascii', Variable('c'))
pn.add_output('char', 'uppercase_ascii', Expression('c.upper()'))

W = {} # the max outgoing weights for places
# clone transition for each type
for place in pn.place():
	t = place.name
	tr = 'clone_' + t
	W[t] = utility.max_out(place)
	pn.add_transition(Transition(tr))
	pn.add_input(t, tr, Variable(t[:3]))
	pn.add_output(t, tr, MultiArc([Expression(t[:3]), Expression(t[:3])]))

pn.globals._env['pn'] = pn # not safe

for trans in pn.transition():
	place_name = list(trans.post.keys())[0] # for function that has only one return value
	place = pn.place(place_name)
	expr = Expression("pn.place('%s').tokens.__len__() <= %d" % (place_name, W[place_name]))
	expr.globals.attach(pn.globals)
	trans.guard = expr

del W

pn.set_marking(Marking(char=['a']))
s = StateGraph(pn)
s.build()

print('--------------------------')
for state in s :
	print(state, s.net.get_marking())
	print('completed %s, todo %s' % (s.completed(), s.todo()))
	# print(" =>", list(s.successors()))
	# print(" <=", list(s.predecessors()))

pn.draw('draws/ocaml_char.eps')
# pn.place('char').add(['a','b'])
# pn.draw('draws/ocaml_char1.eps')
# pn.transition('code').fire(pn.transition('code').modes()[0])
# pn.draw('draws/ocaml_char2.eps')