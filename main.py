from utility import * # snakes module inside

directory = "./json/char"
net, comps = construct_net('ocaml_char', directory)

net.draw('draws/ocaml_char.eps')

start_marking = Marking(char=MultiSet(['t']))
end_marking = Marking(int=MultiSet(['t']))
s = StateGraph(net, start=start_marking, end=end_marking, aug_graph='draws/clone_added.eps')

s.build()
s.draw('draws/state_graph.eps')

# for state in s :
# 	print(state, s.net.get_marking())

## simply listing all paths without repeating state  
# for seq in s.enumerate_sketch():
# 	print(seq)
# 	for line in gen_sketch(comps, seq):
# 		print(line)
# 	print()


for seq in s.enumerate_sketch_l(6):
	print(seq)
	for line in gen_sketch(comps, seq):
		print(line)
		pass
	print()
