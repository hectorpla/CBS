class SketchFormatter(object):
	'''a class that format up the systhesised codes'''
	def __init__(self, lines, rec_fuc=False):
		self._lines = lines # list of SketchLine
		self.rec_fuc = rec_fuc
	def format_out(self, subst=None):
		sk = []
		sk.append(self._lines[0].sketch(rec=self.rec_fuc))
		for skline in self._lines[1:-1]:
			toprint = skline.sketch(subst)
			sk.append('\t' + toprint + ' in')
		sk.append('\t' + self._lines[-1].sketch(subst))
		return sk
