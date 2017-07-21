import TEfixer
import argparse

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-prog', metavar='name of file to fix', type=str, help='')
parser.add_argument('-json', metavar='json', type=str, help='')
args = parser.parse_args()

folder = 'teprog/'



prog = 'teprog/square_b.ml'
info = 'teprog/fix2.json'
fixer = TEfixer.TEfixer(info, progfile=prog)
fixer.fix()	