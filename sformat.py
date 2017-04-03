class SketchFormatter(object):
	'''a class that format up the systhesised codes'''
	def __init__(self, lines):
		# assert isinstance(sigtr, TargetFunc)
		# assert isinstance(lines[0], SketchLine)
		# self._signature = sigtr
		self._lines = lines # list of SketchLine
	def format_out(self, subst=None):
		sk = []
		# sk.append(self._signature.sketch())
		sk.append(self._lines[0].sketch())
		for skline in self._lines[1:-1]:
			toprint = skline.sketch(subst)
			sk.append('\t' + toprint + ' in')
		sk.append('\t' + self._lines[-1].sketch(subst))
		return sk