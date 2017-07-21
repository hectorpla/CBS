from synthesis import *
import argparse

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-filename', metavar='filename', type=str, help='..')
parser.add_argument('-len', metavar='length of program', type=int, default=7)
args = parser.parse_args()

signtr = 'signatures/' + args.filename #'signatures/intchar2string.json'
score = 'json/scores.json'
length = args.len

construct_start = time.clock()
syns = Synthesis(sigtr_file=signtr, func_scores=score, enab_func_para=False)
print('time spent on initializing a synthesis:', time.clock() - construct_start)

draw_start = time.clock()
syns.draw_net()
print('net drawing time:', time.clock() - draw_start)

syns.setup() # prep for synthesis, i.e. construct PetriNet, build state graph, etc.
syns.draw_alpha()
print('Synthesis set up successfully')

syns.draw_augmented_net()
syns.draw_state_graph()
syns.set_syn_len(length) # set the maximum program length

syns.start(enab_brch=True)
