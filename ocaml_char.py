import snakes.plugins
snakes.plugins.load(["gv", "pos", "search"], "snakes.nets", "snk")
from snk import *

simple_tok = True
pn = PetriNet('ocaml_char')
pn.add_place(Place('char'))
pn.add_place(Place('int'))
pn.add_place(Place('string'))

pn.add_transition(Transition('code'))
pn.add_input('char', 'code', Variable('c'))
if simple_tok: pn.add_output('int', 'code', Expression('c'))
else: pn.add_output('int', 'code', Expression('ord(c)'))

pn.add_transition(Transition('chr'))
pn.add_input('int', 'chr', Variable('c'))
if simple_tok: pn.add_output('char', 'chr', Expression('c'))
else: pn.add_output('char', 'chr', Expression('chr(c)'))

pn.add_transition(Transition('escaped'))
pn.add_input('char', 'escaped', Variable('c'))
if simple_tok: pn.add_output('string', 'escaped', Expression('c'))
else: pn.add_output('string', 'escaped', Expression('repr(c)'))

pn.add_transition(Transition('lowercase_ascii'))
pn.add_input('char', 'lowercase_ascii', Variable('c'))
if simple_tok: pn.add_output('char', 'lowercase_ascii', Expression('c'))
else: pn.add_output('char', 'lowercase_ascii', Expression('c.lower()'))

pn.add_transition(Transition('uppercase_ascii'))
pn.add_input('char', 'uppercase_ascii', Variable('c'))
if simple_tok: pn.add_output('char', 'uppercase_ascii', Expression('c'))
else: pn.add_output('char', 'uppercase_ascii', Expression('c.upper()'))

pn.add_transition(Transition('^'))
pn.add_input('string', '^', MultiArc([Variable('s1'), Variable('s2')]))
if simple_tok: pn.add_output('string', '^', Expression('s1'))
else: pn.add_output('string', '^', Expression('s1 + s2'))

##### test end marking
# char=MultiSet(['t', 't'])
# string=MultiSet(['t']), int=MultiSet(['t'])
# char=MultiSet(['t']), string=MultiSet(['t']), int=MultiSet(['t'])
#####
end_marking = Marking(string=MultiSet(['t']*2))

pn.set_marking(Marking(char=MultiSet(['t'])))
s = StateGraph(pn, end=end_marking, aug_graph='draws/clone_added.eps')
s.build()
# s.build_until(end_marking)

pn.draw('draws/ocaml_char.eps')
s.draw('draws/state_graph.eps', debug=True)

# s._node2node_path_rec(end_marking)
print('---------------')
for seq in s.enumerate_sketch():
	print(seq)

# print('------------state graph--------------')
# for state in s :
# 	print(state, s.net.get_marking())
# 	print('completed %s, todo %s' % (s.completed(), s.todo()))
	# print(" =>", list(s.successors()))
	# print(" <=", list(s.predecessors()))
