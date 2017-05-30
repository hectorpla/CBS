import TEfixer

prog = 'teprog/square.ml'
info = 'teprog/fix1.json'
fixer = TEfixer.TEfixer(info, progfile=prog)
fixer.fix()