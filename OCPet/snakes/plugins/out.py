import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend(module):
	class Place (module.Place):
		def __init__(self, name, tokens=[], check=None, **args):
			self._max_outweight = 0
			module.Place.__init__(self, name, tokens, check, **args)
		def update_maxweight(self, w):
			self._max_outweight = max(_max_outweight, w)
	return Place
