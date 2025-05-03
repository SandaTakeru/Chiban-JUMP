# -*- coding: utf-8 -*-

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
	from .chiban_jump import ChibanJump
	return ChibanJump(iface)
