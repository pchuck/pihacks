# image_ascii_converter.py
#
# functions for converting an image to ascii 'art'
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
# gray scale level values from http://paulbourke.net/dataformats/asciiart/
#
import numpy as np 
  
def average_luminance(image): 
    """ 
    Given PIL Image (mode 'rgb'), return average value of grayscale value 
    """
    im = np.array(image)
    w, h, d = im.shape
    return np.average(im.reshape(w * h * d))

def image_to_ascii(image, cols, scale, levels): 
    """ 
    Given an image returns an m*n list of text representing the image.
    """

    # 70 vs. 10 levels of 'gray'
    GS1 = " .'`^\",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    GS2 = ' .:-=+*#%@'

    W, H = image.size[0], image.size[1] # dimensions
    w = W / cols # tile width
    h = w / scale # tile height
    rows = int(H / h) # number of rows
    asc = [] # rows of ascii characters

    # generate list of dimensions 
    for j in range(rows): 
        y1 = int(j * h) 
        y2 = int((j + 1) * h) 
        if j == rows - 1: y2 = H # last tile row fix
        asc.append("") 
        for i in range(cols): 
            x1 = int(i * w) # crop image to tile 
            x2 = int((i + 1) * w) 
            if i == cols - 1: x2 = W # last tile col fix
            img = image.crop((x1, y1, x2, y2)) # extract tile
            al = average_luminance(img)
            # luminance to corresponding ascii character
            if levels: gsval = GS1[int(al * 70) >> 8] 
            else: gsval = GS2[int(al * 10) >> 8]
            asc[j] += gsval 

    return asc 

