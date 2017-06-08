import TEfixer

prog = 'teprog/square_b.ml'
info = 'teprog/fix2.json'
fixer = TEfixer.TEfixer(info, progfile=prog)
fixer.fix()