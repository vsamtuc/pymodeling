
# 
# Implementing directed graphs to check for deadlocks in 
# a simple Process-Resource scenario
#
# In this model, processes and resources are nodes in a graph.
# When a process P requests a resource R, an edge P->R (from process
# to resource) is formed. Process P is a *suitor*, and the resource is
# *pending* for P.
#
# When a process is granted a requested resource, the edge P->R is
# reversed (becoming R->P). Process P becomes the owner of R.
# 
# If a process has no pending resources, then it can release all
# resources held (removing all edges).
#
# It is well-known that there is a deadlock, if and only if there is
# a cycle in the process-resource graph.
# 
# In this example, we implement a randomized scheduler and we test it on
# a number of processes, simulating the well-known Dining Philosophers
# problem. We count the number of steps to reach deadlock.
#

from modeling import *
from enum import Enum
import random

#
# Model of a directed graph
#

@model
class Vertex:
	outgoing = refs()  
	incoming = refs()

@model
class Edge:
	source = ref(inv=Vertex.outgoing)
	destination = ref(inv=Vertex.incoming)

	def __init__(self, src=None, dest=None):
		self.source = src
		self.destination = dest

#
#
# Graph-based model of processes, resources and requests.
#
#


@model
class Resource(Vertex):

	# Current resource owner process
	def owner(self):
		if self.outgoing:
			return list(self.outgoing)[0].destination
		else:
			return None


#
# A process has a context (a current callable) and maintains
# a list of pending and granted resource requests.
#


@model
class Process(Vertex):

	executor = ref()
	context = attr(object, nullable=False)

	def __init__(self, executor):
		self.executor = executor

	def request(self, r):
		# Request a resource
		Request(self, r)

	def release_all(self):
		# release all resources
		for req in list(self.incoming):
			req.release()

	def run(self):
		self.context = self.context(self)


@model
class Request(Edge):

	proc = attr(Process, nullable=False)
	resource = attr(Resource, nullable=False)

	def __init__(self, proc, res):
		super().__init__(proc,res)

		self.proc = proc
		self.resource = res	

	def release(self):
		# effectively erase this edge from the graph
		self.source, self.destination = None, None

	def run(self):
		print("Grant", self.proc, "->", self.resource)

		# flip edge to grant resource
		self.source, self.destination = self.destination, self.source

	def __str__(self):
		return "%s->%s" % (self.proc, self.resource)


@model
class Executor:
	processes = refs(inv=Process.executor)	
	cycle = attr(int)

	def __init__(self):
		self.cycle = 0

	def run(self):

		while True:
			all_steps = []
			for p in self.processes:
				# either a process is ready (no pending requests) or
				# pending requests are ready
				pending = [req for req in p.outgoing]
				if not pending:
					all_steps.append(p)
				else:
					for req in pending:
						if req.destination.owner() is None:
							all_steps.append(req)

			if not all_steps:
				break

			step = random.choice(all_steps)
			step.run()
			self.cycle+=1


#
# Model of the Dining Philisophers.
# Here, we extend our Process model with 
# a "program".
#

@model
class Fork(Resource):
	def __init__(self,i):
		self.i=i

	def __str__(self):
		return "Fork %d" % self.i


@model
class Philosopher(Process):

	left_fork = attr(Fork, nullable=False)
	right_fork = attr(Fork, nullable=False)

	def __init__(self, i, executor, lf, rf):
		super().__init__(executor)

		self.i = i
		self.left_fork = lf
		self.right_fork = rf
		self.context = Philosopher.think

	def think(self):
		print(self,"thinks")
		return Philosopher.go_hungry

	def go_hungry(self):
		print(self,"goes hungry")
		self.request(self.left_fork)
		self.request(self.right_fork)

		return Philosopher.eat

	def eat(self):
		print(self,"eats")
		self.release_all()

		return Philosopher.think

	def __str__(self):
		return "Phil %d" % self.i



def symposium(n):
	#
	# Create a symposium of n philosophers
	#

	e = Executor()

	forks = [Fork(i) for i in range(n)]

	for i in range(n):
		Philosopher(i, e, forks[i-1], forks[i])

	return e


if __name__=='__main__':

	e = symposium(5)
	e.run()

	print("Philosophers=",len(e.processes),", deadlock after",e.cycle,"steps")

	for p in e.processes:
		print("Phil.",p.i, "holds forks", [f.source.i for f in p.incoming])

