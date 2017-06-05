from OCPet import synthesis
import time

signtr = 'signatures/stutter.json'
score = 'json/scores.json'

construct_start = time.clock()
syns = synthesis.Synthesis(sigtr_file=signtr, func_scores=score, enab_func_para=False)
print('time spent on initializing a synthesis:', time.clock() - construct_start)

draw_start = time.clock()
syns.draw_net()
print('net drawing time:', time.clock() - draw_start)

syns.setup() # prep for synthesis, i.e. construct PetriNet, build state graph, etc.
syns.draw_alpha()
print('Synthesis set up successfully')

syns.draw_augmented_net()
syns.draw_state_graph()
syns.set_syn_len(7) # set the maximum program length

syns.start(enab_brch=True)
