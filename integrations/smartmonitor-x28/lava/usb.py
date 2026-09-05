import os,termios,fcntl,select,time,datetime
from pathlib import Path

def crc(data):
 c=0xffff
 for b in data:
  c^=b
  for _ in range(8):c=(c>>1)^(0xa001 if c&1 else 0)
 return c

def packet(brightness=65,stats=None):
 n=datetime.datetime.now()
 a=bytearray([0x66,0,0,1,(n.year+48)&255,n.month,n.day,n.hour,n.minute,n.second,n.isoweekday()+5*8,brightness])
 for key,val in (stats or {}).items():a.extend(bytes([key])+max(0,min(65535,round(val))).to_bytes(2,'big'))
 a[1:3]=(len(a)+2).to_bytes(2,'big');a+=crc(a).to_bytes(2,'big');return a
class Display:
 def __enter__(self):
  found=[]
  for p in Path('/sys/class/tty').glob('ttyACM*'):
   for parent in (p/'device').resolve().parents:
    try:
     if (parent/'idVendor').read_text().strip()=='1a86' and (parent/'idProduct').read_text().strip()=='8040':found.append('/dev/'+p.name)
    except FileNotFoundError:pass
  if len(found)!=1:raise RuntimeError(f'Expected one X28, found {found}')
  self.fd=os.open(found[0],os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
  fcntl.ioctl(self.fd,termios.TIOCEXCL)
  t=termios.tcgetattr(self.fd);t[0]=t[1]=t[3]=0;t[2]=termios.CS8|termios.CREAD|termios.CLOCAL;t[4]=t[5]=termios.B1000000;t[6][termios.VMIN]=t[6][termios.VTIME]=0
  termios.tcsetattr(self.fd,termios.TCSANOW,t);termios.tcflush(self.fd,termios.TCIOFLUSH)
  return self
 def write(self,data):
  while data:
   if not select.select([],[self.fd],[],2)[1]:raise TimeoutError('USB write timeout')
   n=os.write(self.fd,data);data=data[n:]
  termios.tcdrain(self.fd)
 def read(self,seconds):
  out=bytearray();end=time.monotonic()+seconds
  while time.monotonic()<end:
   if select.select([self.fd],[],[],max(0,end-time.monotonic()))[0]:out.extend(os.read(self.fd,4096))
  return bytes(out)
 def __exit__(self,*args):
  try: fcntl.ioctl(self.fd,termios.TIOCNXCL)
  except OSError: pass
  finally: os.close(self.fd)
