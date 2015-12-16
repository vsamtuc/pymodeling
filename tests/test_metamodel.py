'''
Test module for mf metamodels

Created on Dec 15, 2015

@author: vsam
'''


import pytest
from modeling.mf import *
from modeling.constraints import *

import sys


def test_multiple_inheritance():

	@model
	class Foo:
		a = ref()
		y = attr(int)

	@model
	class Bar(Foo):
		x = attr(int)
		b = refs(inv=Foo.a)

	@model
	class Boo(Foo):
		y = attr(str)

	@model
	class Baz(Bar,Boo):
		x = attr(str)

	assert validate_classes({Foo,Bar,Baz})
	assert model_class(Bar).get_attribute('x') \
		is not model_class(Baz).get_attribute('x')
	assert model_class(Baz).get_attribute('y') \
		is model_class(Boo).get_attribute('y')

	assert model_class(Baz).is_subclass(model_class(Bar))	
	assert model_class(Baz).is_subclass(model_class(Foo))
	assert len(model_class(Baz).all_proper_superclasses())==3
