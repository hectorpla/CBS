from synthesis import *

f = 'signatures/head_of_list.json'
syns = Synthesis(sigtr_file=f, enab_func_para=False)
syns.draw_net()
syns.setup() # prep for synthesis, i.e. construct PetriNet, build state graph, etc.
print('Synthesis set up successfully')
syns.draw_augmented_net()
# syns.draw_state_graph()
syns.set_syn_len(8) # set the maximum program length
syns.start()