"""Local controls for this machine. No background RGB polling, shell or network."""
from pathlib import Path
import copy, fcntl, json, os, re, subprocess, time

BASE=Path(__file__).resolve().parent
STATE=Path.home()/'.config/magma-lights/state.json'
PRESETS={
 'lava':('Lava','FF3000','Laranja incandescente'),
 'brasa':('Brasa','FF850A','Calor suave'),
 'oceano':('Oceano','00BFFF','Azul profundo'),
 'aurora':('Aurora','A472FF','Violeta elétrico'),
 'floresta':('Floresta','22D69A','Verde fresco'),
 'lua':('Lua','D6E4FF','Branco azulado'),
}
DEFAULT={'preset':'lava','color':'FF3000','brightness':100,'fans':True,'ram':True,'gpu':True,'sleeping':False,'last_awake':None,'applied_at':None}

class ControlError(Exception):pass

def normalized(raw):
 s=copy.deepcopy(DEFAULT)
 if isinstance(raw,dict):
  for k in ('fans','ram','gpu','sleeping'):
   if isinstance(raw.get(k),bool):s[k]=raw[k]
  c=raw.get('color','')
  if isinstance(c,str) and re.fullmatch('[0-9a-fA-F]{6}',c):s['color']=c.upper()
  b=raw.get('brightness')
  if type(b) is int and 10<=b<=100:s['brightness']=b
  if raw.get('preset') in PRESETS or raw.get('preset')=='custom':s['preset']=raw['preset']
  if isinstance(raw.get('last_awake'),dict):
   s['last_awake']=normalized({**raw['last_awake'],'last_awake':None})
  if isinstance(raw.get('applied_at'),(int,float)):s['applied_at']=raw['applied_at']
 return s

class Controller:
 def __init__(self,state_path=STATE,runner=None):
  self.path=Path(state_path);self.runner=runner or self._run
 def load(self):
  try:return normalized(json.loads(self.path.read_text()))
  except (OSError,ValueError):return copy.deepcopy(DEFAULT)
 def save(self,s):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2));tmp.replace(self.path)
 @staticmethod
 def _run(cmd):
  try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
  except FileNotFoundError:raise ControlError(f'Programa não encontrado: {cmd[0]}')
  except subprocess.TimeoutExpired:raise ControlError('O dispositivo demorou demais para responder. Tente novamente.')
  if r.returncode:raise ControlError((r.stderr or r.stdout or 'Falha ao aplicar o comando.').strip()[-450:])
  if re.search(r'(device.*not found|invalid mode|unknown mode)',r.stdout+' '+r.stderr,re.I):
   raise ControlError((r.stdout+' '+r.stderr).strip()[-450:])
  return r
 @staticmethod
 def rgb_command(s,keyboard=False):
  factor=s['brightness']/100
  c=''.join(f'{round(int(s["color"][i:i+2],16)*factor):02X}' for i in (0,2,4))
  cmd=['openrgb','--noautoconnect']
  for key,name in [('ram','ENE DRAM'),('ram','Corsair Vengeance RGB DDR5'),('gpu','ASUS TUF GeForce RTX 4070 Ti SUPER Gaming White OC')]:
   cmd+=['--device',name,'--mode','Direct','--color',c if s[key] else '000000']
  if keyboard:cmd+=['--device','G515 LS TKL','--mode','Static','--color',c]
  # Final device must be MSI. A later OpenRGB startup can disturb its mode.
  cmd+=['--device','MSI B650M','--mode','Static' if s['fans'] else 'Direct']
  if s['fans']:cmd+=['--brightness','100']
  cmd+=['--color',c if s['fans'] else '000000']
  return cmd
 def apply_rgb(self,s,keyboard=False):
  if not s['fans']:
   self.runner(['openrgb','--noautoconnect','--device','MSI B650M','--zone','0','--size','200','--zone','1','--size','240','--zone','2','--size','240'])
  self.runner(self.rgb_command(s,keyboard))
 def action(self,action,**params):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.path.with_suffix('.lock').open('w') as lock:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise ControlError('Outro comando está em andamento. Aguarde um instante.')
   s=self.load()
   if action in ('screen_on','screen_off'):
    self.runner([str(Path.home()/'.local/bin/telinha'),'lava' if action=='screen_on' else 'off'])
    return s,'Painel iniciado.' if action=='screen_on' else 'Telinha apagada.'
   n=copy.deepcopy(s)
   if action=='preset':
    key=params['preset']
    if key not in PRESETS:raise ControlError('Preset desconhecido.')
    n.update(preset=key,color=PRESETS[key][1],fans=True,ram=True,gpu=True,sleeping=False)
   elif action=='custom':
    color=params.get('color','').lstrip('#').upper()
    if not re.fullmatch('[0-9A-F]{6}',color):raise ControlError('Digite uma cor como #FF3000.')
    n.update(preset='custom',color=color,sleeping=False)
   elif action=='brightness':
    b=int(params['brightness'])
    if not 10<=b<=100:raise ControlError('A intensidade deve ficar entre 10 e 100%.')
    n['brightness']=b
   elif action=='device':
    key=params['device']
    if key not in ('fans','ram','gpu') or type(params.get('enabled')) is not bool:raise ControlError('Controle inválido.')
    n[key]=params['enabled'];n['sleeping']=False
   elif action=='restore':
    n=normalized(s['last_awake'] or {**s,'fans':True,'ram':True,'gpu':True});n['sleeping']=False
   elif action=='sleep':
    if not s['sleeping']:n['last_awake']={**s,'last_awake':None}
    n.update(fans=False,ram=False,gpu=False,sleeping=True)
   elif action not in ('reapply','keyboard'):raise ControlError('Ação desconhecida.')
   failures=[]
   try:
    self.apply_rgb(n,keyboard=action=='keyboard');n['applied_at']=time.time();self.save(n)
   except ControlError as e:failures.append('RGB: '+str(e));n=s
   if action=='sleep':
    try:self.runner([str(Path.home()/'.local/bin/telinha'),'off'])
    except ControlError as e:failures.append('Telinha: '+str(e))
   if failures:raise ControlError(' / '.join(failures))
   return n,('Gabinete e telinha apagados.' if action=='sleep' else 'Comando enviado. Veja o resultado no PC.')

def telemetry():
 p=Path.home()/'.local/share/smartmonitor-x28/lava/live.json'
 try:
  data=json.loads(p.read_text());age=time.time()-float(data['time'])
  return data if 0<=age<8 else None
 except (OSError,ValueError,KeyError,TypeError):return None

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description='Magma — luzes do PC')
 p.add_argument('action',choices=['preset','sleep','restore','reapply','screen_on','screen_off','status'])
 p.add_argument('preset',nargs='?',choices=list(PRESETS))
 a=p.parse_args();c=Controller()
 try:
  if a.action=='status':print(json.dumps({'last_applied':c.load(),'telemetry':telemetry()},ensure_ascii=False,indent=2))
  else:print(c.action(a.action,**({'preset':a.preset or 'lava'} if a.action=='preset' else {}))[1])
 except ControlError as e:p.exit(1,str(e)+'\n')
