#!/usr/bin/env python3
#
# firefly.py
#
# A python script for animating a 'swarm' of fireflies.
#
# The swarm consists of a specified number of elements, each with its own
# position and velocity. With each iteration, velocities are perturbed
# using brownian motion which randomly increments or decrements the
# velocity of the element, changing its trajectory and position on the display
# to produce a fluid and natural looking animation.
#
# Run with '--help' to see available options.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys, os
import argparse
from random import randrange
import tkinter as tk


# Firefly primitives
pathname = os.path.dirname(sys.argv[0])        
fullpath = os.path.abspath(pathname)
exec(compile(source=open(fullpath + '/fireflies.py').read(),
			 filename='fireflies.py', mode='exec'))


# FireflyRenderer
#
# Encapsulates all rendering, including the graphics context and/or canvas.
# When fireflies positions have changed, or the canvas changed,
# resize() or render() are called to update the visual representation.
#
# This renderer is specific to tkinter.
#
class FireflyRendererTk(object):
	def __init__(self, canvas, fireflies, size=10, **kwargs):
		self.canvas = canvas
		self.fireflies = fireflies
		self.s = size
		self.max = Point(0, 0) # 0's here and in oval. resize inits everything
		for firefly in self.fireflies.flies:
			firefly.id = canvas.create_oval(0, 0, 0, 0, **kwargs)

	# resize the canvas with new max x and y size
	def resize(self, size):
		for firefly in self.fireflies.flies:
			if(self.max.x == 0 or self.max.y == 0 or size.x ==0 or size.y == 0):
				firefly.p = Point(randrange(size.x), randrange(size.y))
			else:
				scale = Point(size.x / self.max.x, size.y / self.max.y)
				firefly.p = Point(firefly.p.x * scale.x, firefly.p.y * scale.y)
				firefly.b = Point(firefly.b.x * scale.x, firefly.b.y * scale.y)
				firefly.max = size

			self.canvas.coords(firefly.id,
							   firefly.p.x, firefly.p.y,
							   firefly.p.x + self.s, firefly.p.y + self.s)

		self.max = size
			
	# render everything on the canvas
	def render(self): 
		for firefly in self.fireflies.flies:
			self.canvas.move(firefly.id, firefly.v.x, firefly.v.y)

# tkinter app
#
class App(object):
	def __init__(self, master, bounds, 
				 count, size, maxv, varyv, # firefly params
				 delay, **kwargs): # rendering params
		self.master = master
		self.canvas = tk.Canvas(self.master, width=bounds.x, height=bounds.y,
								highlightthickness=0,
								background='black')
		self.canvas.pack(fill="both", expand=True)
		self.fireflies = Fireflies(bounds, count, size, maxv=maxv, varyv=varyv)
		self.renderer = FireflyRendererTk(self.canvas, self.fireflies,
										  size=size, **kwargs)
		self.canvas.bind('<Configure>', self.resize)
		self.canvas.pack(fill="both", expand=True)
		self.master.after(delay, self.animation)
		self.delay = delay

	# canvas resize event handler
	def resize(self, event):
		# print("resize: " + str(event.width) + ", " + str(event.height))
		self.canvas.config(width=event.width, height=event.height)
		self.renderer.resize(Point(event.width, event.height))

	# animation
	def animation(self):
		for fly in self.fireflies.flies: fly.move()
		self.renderer.render()
		self.master.after(self.delay, self.animation)


## argument parsing
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='led_swarm arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	# required arguments
	parser.add_argument('x', type=int, 
		help='The x resolution of the matrix')
	parser.add_argument('y', type=int, 
		help='The y resolution of the matrix')
	parser.add_argument('members', type=int, 
		help='The number of members in the swarm (try 1..1000)')
	# swarm features
	parser.add_argument('--size', '-s', type=int, default=10,
		help='The element size')
	parser.add_argument('--outline', '-o', type=str, default='red',
		help='The element border color')
	parser.add_argument('--color', '-c', type=str, default='darkred',
		help='The element fill color')
	parser.add_argument('--max-x-velocity', '-maxvx', type=int, default=8, 
		help='The maximum member x velocity')
	parser.add_argument('--max-y-velocity', '-maxvy', type=int, default=4, 
		help='The maximum member y velocity')
	parser.add_argument('--delay', '-d', type=float, default=0.01,
		help='The delay (in seconds) between iterations')

	args = parser.parse_args()


	try:		
		root = tk.Tk()
		app = App(root,
				  bounds=Point(args.x, args.y), # canvas size
				  count=args.members, # firefly count
				  size=args.size, # firefly size (diameter)
				  maxv=Point(args.max_x_velocity, args.max_y_velocity), 
				  varyv=True, # whether to randomly vary the velocity max
				  delay=int(args.delay * 1000), # delay between updates
				  outline=args.outline, # sprite outline color
				  fill=args.color, # sprite fill color
				  stipple='gray25') # for alpha-like transparency
		root.mainloop()
			
	except KeyboardInterrupt:
		pass

##
