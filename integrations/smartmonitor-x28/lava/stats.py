from usb import Display,packet
from pathlib import Path
import time,json,subprocess,signal
base=Path(__file__).resolve().parent
run=True

def stop(*args):
 global run;run=False
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def cpu():
 values=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(values),values[3]+values[4]
def cputemp():
 for hw in Path('/sys/class/hwmon').glob('hwmon*'):
  if (hw/'name').read_text().strip()=='k10temp':return float((hw/'temp1_input').read_text())/1000
 raise RuntimeError('CPU temperature unavailable')
def memory():
 m={a: int(b.split()[0]) for a,b in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())}
 return 100*(1-m['MemAvailable']/m['MemTotal'])
prev=cpu()
with Display() as d:
 while run:
  time.sleep(1)
  cur=cpu();delta=cur[0]-prev[0];cpuuse=100*(1-(cur[1]-prev[1])/delta) if delta else 0;prev=cur
  gpu=subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=3).stdout.strip().splitlines()[0].split(',')
  values={1:cputemp(),2:float(gpu[0]),3:cpuuse,4:float(gpu[1]),5:memory()}
  d.write(packet(65,values));d.read(.02)
  (base/'live.json').write_text(json.dumps({'time':time.time(),'cpu_temp':values[1],'gpu_temp':values[2],'cpu_load':values[3],'gpu_load':values[4],'ram_used':values[5]}))
