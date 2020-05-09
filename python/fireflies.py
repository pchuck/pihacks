#
# fireflies.py
#
# 'firefly' primitives used by the tk and raspberry pi versions of the
# swarm app. See tk_swarm.py or led_swarm.py.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
from random import randrange, getrandbits
from collections import namedtuple


# Points have an x/y component (used for coordinates, dimensions)
#
Point = namedtuple('point', 'x y')


# Fireflies is a container for a swarm of fireflies.
#
class Fireflies(object):
    def __init__(self, bounds, count, maxv, varyv):
        self.flies = []
        for i in range(count):
            p = Point(randrange(bounds.x), randrange(bounds.y))
            if(varyv):
                nmv = Point(randrange(maxv.x) + 1, randrange(maxv.y) + 1)
                self.flies.append(Firefly(bounds, p, nmv))
            else:
                self.flies.append(Firefly(bounds, p, maxv))

# Firefly
#
# A firefly has a current position and velocity.
# Velocity is randomly and incrementally perturbed.
# Movement is governed by max velocity (maxv) and positional boundaries (max).
#
class Firefly(object):
    def __init__(self, bounds, pos, maxv):
        self.b = bounds # bounding extent
        self.p = pos # current position
        self.v = Point(0, 0) # velocity
        self.maxv = maxv # maximum velocity

    def move(self):
        # perturb the velocity, random velocity delta
        rvd = randrange(3) - 1 
		
        # changing only x or y is smoother than changing both simultaneously
        if(bool(getrandbits(1))):
            self.v = Point(self.v.x, self.v.y + rvd)
        else:
            self.v = Point(self.v.x + rvd, self.v.y)

        # limit velocity
        if(self.v.x >  self.maxv.x): self.v = Point( self.maxv.x,  self.v.y)
        if(self.v.y >  self.maxv.y): self.v = Point( self.v.x,     self.maxv.y)
        if(self.v.x < -self.maxv.x): self.v = Point(-self.maxv.x,  self.v.y)
        if(self.v.y < -self.maxv.y): self.v = Point( self.v.x,    -self.maxv.y)
			
        # invert velocity if move would go out of bounds
        if(self.p.x + self.v.x >= self.b.x):
           self.v = Point(-abs(self.v.x), self.v.y)
        if(self.p.x + self.v.x < 0):
           self.v = Point(abs(self.v.x), self.v.y)
        if(self.p.y + self.v.y >= self.b.y):
           self.v = Point(self.v.x, -abs(self.v.y))
        if(self.p.y + self.v.y < 0):
           self.v = Point(self.v.x, abs(self.v.y))

        # apply the velocity to arrive at new position
        self.p = Point(self.p.x + self.v.x, self.p.y + self.v.y)
