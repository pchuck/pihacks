# micropython for Raspberry Pi Pico
# pi pico + LCD 1.3" ST7789 SPI Display (240x240 IPS LCD)
#
# etch-a-sketch
#
from machine import Pin,SPI,PWM
import framebuf
import time
import os

BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

class LCD_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 240
        self.height = 240

        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,100000_000,polarity=0,
                       phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()
        
        self.red   =   0x07E0
        self.green =   0x001f
        self.blue  =   0xf800
        self.white =   0xffff
        self.black =   0x0000
        self.yellow =  0x07ff

        # extents of the mandelbrot region plane
        self.x0 = -1.5
        self.y0 = -1.5
        self.x1 = 1.5
        self.y1 = 1.5

        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize display"""  
        self.rst(1)
        self.rst(0)
        self.rst(1)
        
        self.write_cmd(0x36)
        self.write_data(0x70)

        self.write_cmd(0x3A) 
        self.write_data(0x05)

        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)

        self.write_cmd(0xB7)
        self.write_data(0x35) 

        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)   

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6)
        self.write_data(0x0F) 

        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)

        self.write_cmd(0xE0)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)

        self.write_cmd(0xE1)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)
        
        self.write_cmd(0x21)

        self.write_cmd(0x11)

        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xef)
        
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)
        
        self.write_cmd(0x2C)
        
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def render_mandelbrot_row(self, y, step=16, n=64):
        factor = int(0xffff / n)
        for x in range(0, self.width, step):
            xp = self.x0 + (self.x1 - self.x0) * x / self.width
            yp = self.y0 + (self.y1 - self.y0) * y / self.height
            c = complex(xp, yp)
            z = 0
            for i in range(n):
                z = z * z + c
                if abs(z) > 2:
                    break
            self.fill_rect(x, y, step, step, i * factor)
            #self.pixel(x, y, i * factor)

    def render_mandelbrot(self, step=16, n=64):
        for y in range(0, self.height, step):
            self.render_mandelbrot_row(y, step, n)


if __name__=='__main__':
    pwm = PWM(Pin(BL))
    pwm.freq(1000)
    pwm.duty_u16(32768) # max 65535

    LCD = LCD_1inch3()
    LCD.fill(LCD.black)

    keyA = Pin(15,Pin.IN,Pin.PULL_UP)
    keyB = Pin(17,Pin.IN,Pin.PULL_UP)
    keyX = Pin(19 ,Pin.IN,Pin.PULL_UP)
    keyY = Pin(21 ,Pin.IN,Pin.PULL_UP)
    
    up = Pin(2,Pin.IN,Pin.PULL_UP)
    down = Pin(18,Pin.IN,Pin.PULL_UP)
    left = Pin(16,Pin.IN,Pin.PULL_UP)
    right = Pin(20,Pin.IN,Pin.PULL_UP)
    ctrl = Pin(3,Pin.IN,Pin.PULL_UP)

    n = 256 # max iterations
    minstep = 1 # minimum step size
    step = maxstep = 16 # initial step size
    row = 0 # current row
   
    debounce = False # button debounce
    changed = True # zoom or pan change tracking

    while(1):
        d = (LCD.x1 - LCD.x0) / 4 # zoom factor
        if changed: # redraw from start
            print(d)
            step = maxstep
            row = 0
            changed = False

        # ctrl
        if(ctrl.value() == 0):
            l = "ctrl"
            print(l)

        # zoom out
        if(keyA.value() == 0 and debounce == False):
            LCD.x0 = LCD.x0 - d; LCD.x1 = LCD.x1 + d; 
            LCD.y0 = LCD.y0 - d; LCD.y1 = LCD.y1 + d; 
            debounce = True; changed = True; print("zout")

        # zoom in
        if(keyB.value() == 0 and debounce == False):
            LCD.x0 = LCD.x0 + d; LCD.x1 = LCD.x1 - d; 
            LCD.y0 = LCD.y0 + d; LCD.y1 = LCD.y1 - d; 
            debounce = True; changed = True; print("zin")

        # unused
        if(keyX.value() == 0):
            debounce = True; print("keyX")

        # unused
        if(keyY.value() == 0):
            debounce = True; print("keyY")
        
        # pan up
        if(up.value() == 0 and debounce == False):
            LCD.y0 = LCD.y0 - d; LCD.y1 = LCD.y1 - d
            debounce = True; changed = True; print("up")

        # pan down
        if(down.value() == 0 and debounce == False):
            LCD.y0 = LCD.y0 + d; LCD.y1 = LCD.y1 + d
            debounce = True; changed = True; print("down")
        
        # pan left
        if(left.value() == 0 and debounce == False):
            LCD.x0 = LCD.x0 - d; LCD.x1 = LCD.x1 - d
            debounce = True; changed = True; print("left")
        
        # pan right
        if(right.value() == 0 and debounce == False):
            LCD.x0 = LCD.x0 + d; LCD.x1 = LCD.x1 + d
            debounce = True; changed = True; print("right")
        

        # full screen rendering
        # LCD.render_mandelbrot(step=step, n=n)
        # vs.
        # row-wise rendering
        if(step > minstep):
            LCD.render_mandelbrot_row(row, step=step, n=n)

        if(debounce == True):
            time.sleep(0.25)
            debounce = False

        row += step
        if row >= LCD.height:
            row = 0
            step = int(step / 2)

        LCD.show()

    time.sleep(1)
    LCD.fill(0xFFFF)



