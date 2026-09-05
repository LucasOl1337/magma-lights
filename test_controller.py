"""Hardware-free regression tests for control safety and saved state."""
import fcntl, tempfile, unittest
from pathlib import Path
from controller import Controller, ControlError

class Controls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.calls=[];self.c=Controller(Path(self.tmp.name)/'state.json', self.calls.append)
 def test_sleep_restore_preserves_custom_color_brightness_and_disabled_device(self):
  self.c.action('custom',color='#A133EE')
  self.c.action('brightness',brightness=35)
  before,_=self.c.action('device',device='gpu',enabled=False)
  self.c.action('sleep');self.c.action('sleep')
  restored,_=self.c.action('restore')
  for key in ['color','preset','brightness','fans','ram','gpu']:
   self.assertEqual(before[key],restored[key])
  self.assertFalse(restored['sleeping'])
 def test_failed_rgb_does_not_claim_saved_success_but_still_sleeps_screen(self):
  self.c.action('preset',preset='oceano');before=self.c.load();seen=[]
  def fail_rgb(cmd):
   seen.append(cmd)
   if cmd[0]=='openrgb':raise ControlError('USB desconectado')
  self.c.runner=fail_rgb
  with self.assertRaisesRegex(ControlError,'USB desconectado'):self.c.action('sleep')
  self.assertEqual(before,self.c.load());self.assertEqual(seen[-1][-1],'off');self.assertTrue(seen[-1][0].endswith('/telinha'))
 def test_invalid_input_never_reaches_hardware(self):
  for value in ['$(whoami)','FF3300;','notrgb','123']:
   with self.assertRaises(ControlError):self.c.action('custom',color=value)
  self.assertEqual([],self.calls);self.assertFalse(self.c.path.exists())
 def test_concurrent_commands_rejected_before_device_access(self):
  with self.c.path.with_suffix('.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaisesRegex(ControlError,'andamento'):self.c.action('preset',preset='lava')
  self.assertEqual([],self.calls)
 def test_fans_are_final_no_zone_update_even_with_keyboard(self):
  self.c.action('keyboard');cmd=self.calls[-1]
  last=max(i for i,v in enumerate(cmd) if v=='--device')
  self.assertEqual(cmd[last:],['--device','MSI B650M','--mode','Static','--brightness','100','--color','FF3000'])
  self.assertNotIn('--zone',cmd)
  self.c.action('sleep');off=self.calls[-2]
  self.assertEqual(off[-6:],['--device','MSI B650M','--mode','Direct','--color','000000'])
  size=self.calls[-3];self.assertIn('--size',size);self.assertNotIn('--color',size)
 def test_screen_actions_do_not_touch_rgb(self):
  self.c.action('screen_on');self.c.action('screen_off')
  self.assertEqual(len(self.calls),2);self.assertTrue(all(c[0].endswith('/telinha') for c in self.calls))

if __name__=='__main__':unittest.main()
