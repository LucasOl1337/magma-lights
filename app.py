#!/usr/bin/env python3
import sys,math,threading
from pathlib import Path
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,Gdk,GLib,Gio
from controller import Controller,ControlError,PRESETS,telemetry,BASE

DEMO='--demo' in sys.argv
class DemoController(Controller):
 def __init__(self):super().__init__(Path.home()/'.config/magma-lights/demo.json',runner=lambda cmd:None)

def label(text,css=None,wrap=False):
 l=Gtk.Label(label=text,xalign=0)
 if css:l.add_css_class(css)
 if wrap:l.set_wrap(True)
 return l

def box(vertical=False,space=0):return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,spacing=space)
def button(text,css,fn):
 b=Gtk.Button(label=text);b.add_css_class(css);b.connect('clicked',lambda _:fn());return b

def swatch(color):
 d=Gtk.DrawingArea();d.set_size_request(29,29)
 def draw(area,cr,w,h):
  cr.set_source_rgb(*[int(color[i:i+2],16)/255 for i in (0,2,4)]);cr.arc(w/2,h/2,10,0,math.tau);cr.fill()
 d.set_draw_func(draw);return d

class App(Gtk.Application):
 def __init__(self):
  super().__init__(application_id='local.omarchy.MagmaLights',flags=Gio.ApplicationFlags.NON_UNIQUE if DEMO else Gio.ApplicationFlags.DEFAULT_FLAGS)
  self.control=DemoController() if DEMO else Controller();self.state=self.control.load();self.busy=False;self.syncing=False;self.actions=[];self.presets={};self.switches={}
 def do_activate(self):
  if self.get_active_window():self.get_active_window().present();return
  css=Gtk.CssProvider();css.load_from_path(str(BASE/'style.css'));Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
  self.win=Gtk.ApplicationWindow(application=self,title='Magma · Luzes do PC');self.win.set_default_size(1040,840);self.win.connect('close-request',lambda _:self.busy)
  hb=Gtk.HeaderBar();hb.set_title_widget(label('Luzes do PC','muted'));self.win.set_titlebar(hb)
  root=box(True,19);root.set_margin_start(30);root.set_margin_end(30);root.set_margin_top(8);root.set_margin_bottom(20)
  scroll=Gtk.ScrolledWindow();scroll.set_overlay_scrolling(False);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.set_child(root);scroll.set_vexpand(True);outer=box(True,12);outer.append(scroll);self.win.set_child(outer)
  head=box(False,16);head.append(swatch('FF6B35'));titles=box(True,3);titles.append(label('MAGMA','title'));titles.append(label('Seu PC, do seu jeito.','muted'));head.append(titles)
  spacer=box();spacer.set_hexpand(True);head.append(spacer);head.append(label('CONTROLE LOCAL','pill'));root.append(head)
  hero=box(False,24);hero.add_css_class('hero');ht=box(True,6);ht.set_hexpand(True);ht.append(label('SEU CLIMA AGORA','eyebrow'));self.hero_title=label('Lava','hero-title');ht.append(self.hero_title);self.hero_note=label('Último preset enviado · #FF3000','hero-note');ht.append(self.hero_note)
  restore=button('↻  Reaplicar cor','primary',lambda:self.dispatch('reapply'));restore.set_halign(Gtk.Align.START);ht.append(restore);self.actions.append(restore);hero.append(ht)
  art=Gtk.DrawingArea();art.set_size_request(270,136);art.set_draw_func(self.draw_fans);hero.append(art);root.append(hero);self.art=art
  columns=box(False,20);left=box(True,15);left.set_hexpand(True);right=box(True,15);right.set_size_request(323,-1);columns.append(left);columns.append(right);root.append(columns)
  line=box(False,8);line.append(label('Escolha uma vibe','section-title'));left.append(line)
  grid=Gtk.Grid(column_spacing=10,row_spacing=10,column_homogeneous=True)
  for i,(key,(name,color,note)) in enumerate(PRESETS.items()):
   b=Gtk.Button();b.add_css_class('preset');inner=box(True,5);top=box(False,8);top.append(swatch(color));top.append(label(name,'preset-name'));inner.append(top);inner.append(label(note,'preset-note'));b.set_child(inner);b.connect('clicked',lambda _,k=key:self.dispatch('preset',preset=k));grid.attach(b,i%3,i//3,1,1);self.presets[key]=b;self.actions.append(b)
  left.append(grid)
  customize=box(True,10);customize.add_css_class('panel');row=box(False,8);row.append(label('Intensidade','device-name'));gap=box();gap.set_hexpand(True);row.append(gap);self.percent=label('100%','pill');row.append(self.percent);customize.append(row)
  sr=box(False,8);self.scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,10,100,5);self.scale.set_draw_value(False);self.scale.set_value(self.state['brightness']);self.scale.set_hexpand(True);self.scale.connect('value-changed',lambda w:self.percent.set_label(f'{round(w.get_value())}%'));sr.append(self.scale);apply=button('Aplicar','soft',lambda:self.dispatch('brightness',brightness=round(self.scale.get_value())));self.actions.extend([self.scale,apply]);sr.append(apply);customize.append(sr)
  sep=Gtk.Separator();customize.append(sep);row=box(False,8);row.append(label('Sua cor','device-name'));self.hex=Gtk.Entry();self.hex.set_placeholder_text('#FF3000');self.hex.set_max_length(7);self.hex.set_width_chars(9);self.hex.set_hexpand(True);self.hex.set_text('#'+self.state['color']);row.append(self.hex);choose=button('Usar','soft',lambda:self.dispatch('custom',color=self.hex.get_text()));row.append(choose);self.actions.extend([self.hex,choose]);customize.append(row);left.append(customize)
  devices=box(True,16);devices.add_css_class('panel');devices.append(label('No gabinete','section-title'))
  for key,name,detail,icon in [('fans','Fans','3 canais · cor sincronizada','weather-clear-symbolic'),('ram','Memória RAM','ENE + Corsair','media-flash-symbolic'),('gpu','Placa de vídeo','RTX 4070 Ti SUPER','video-display-symbolic')]:
   row=box(False,12);image=Gtk.Image.new_from_icon_name(icon);image.add_css_class('device-icon');row.append(image);t=box(True,3);t.set_hexpand(True);t.append(label(name,'device-name'));t.append(label(detail,'muted'));row.append(t);s=Gtk.Switch();s.set_valign(Gtk.Align.CENTER);s.set_active(self.state[key]);s.connect('notify::active',lambda w,_,k=key:self.device_changed(k,w.get_active()));row.append(s);devices.append(row);self.switches[key]=s;self.actions.append(s)
  right.append(devices)
  screen=box(True,12);screen.add_css_class('panel');sr=box(False,12);ic=Gtk.Image.new_from_icon_name('video-display-symbolic');ic.add_css_class('device-icon');sr.append(ic);t=box(True,3);t.append(label('Telinha do cooler','device-name'));self.screen_note=label('Painel Magma · stats ao vivo','muted');t.append(self.screen_note);sr.append(t);screen.append(sr)
  statrow=box(False,25);self.cpu_stat=label('—','stat-value');self.gpu_stat=label('—','stat-value')
  for name,val in [('CPU',self.cpu_stat),('GPU',self.gpu_stat)]:
   v=box(True,2);v.append(label(name,'eyebrow'));v.append(val);statrow.append(v)
  screen.append(statrow);sr=box(False,8)
  for text,action in [('Mostrar stats','screen_on'),('Apagar','screen_off')]:
   b=button(text,'soft',lambda a=action:self.dispatch(a));b.set_hexpand(True);sr.append(b);self.actions.append(b)
  screen.append(sr);right.append(screen)
  extras=Gtk.Expander(label='Outros dispositivos');eb=box(True,8);eb.set_margin_top(8);eb.append(label('Teclado Logitech · controle em teste.','muted'));test=button('Testar a cor atual no teclado','soft',lambda:self.dispatch('keyboard'));eb.append(test);self.actions.append(test);eb.append(label('FIFINE e MCHOSE · controle de luz ainda indisponível.','muted',True));extras.set_child(eb);left.append(extras)
  bottom=box(False,12);sleep=Gtk.Button();sleep.add_css_class('sleep');sb=box(False,13);si=Gtk.Image.new_from_icon_name('weather-clear-night-symbolic');si.set_pixel_size(28);sb.append(si);st=box(True,3);st.append(label('Modo dormir','section-title'));st.append(label('Apaga gabinete + telinha','muted'));sb.append(st);sleep.set_child(sb);sleep.set_hexpand(True);sleep.connect('clicked',lambda _:self.dispatch('sleep'));bottom.append(sleep);self.actions.append(sleep)
  restore=button('☀  Restaurar luzes','soft',lambda:self.dispatch('restore'));bottom.append(restore);self.actions.append(restore);bottom.set_margin_start(30);bottom.set_margin_end(30);outer.append(bottom)
  statusrow=box(False,9);self.spinner=Gtk.Spinner();statusrow.append(self.spinner);self.status=label('Pronto. Escolha um preset para aplicar.','status',True);self.status.set_hexpand(True);statusrow.append(self.status);statusrow.set_margin_start(30);statusrow.set_margin_end(30);statusrow.set_margin_bottom(14);outer.append(statusrow)
  self.sync();self.refresh_stats();GLib.timeout_add_seconds(3,self.refresh_stats);self.win.present()
 def draw_fans(self,widget,cr,w,h):
  color=self.state['color'] if self.state['fans'] else '403C42';rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
  for cx,cy,r in [(62,74,40),(141,59,46),(227,80,33)]:
   for linewidth,alpha in [(13,.045),(8,.10),(3,.95)]:
    cr.set_line_width(linewidth);cr.set_source_rgba(*rgb,alpha);cr.arc(cx,cy,r,0,math.tau);cr.stroke()
   cr.set_source_rgb(.06,.045,.055);cr.arc(cx,cy,r-8,0,math.tau);cr.fill()
   for i in range(7):
    cr.save();cr.translate(cx,cy);cr.rotate(i*math.tau/7);cr.set_source_rgba(*rgb,.36);cr.move_to(4,0);cr.curve_to(20,-15,r-9,-7,r-12,6);cr.curve_to(18,10,7,8,4,0);cr.fill();cr.restore()
   cr.set_source_rgb(*rgb);cr.arc(cx,cy,5,0,math.tau);cr.fill()
 def device_changed(self,key,enabled):
  if not self.syncing and not self.busy:self.dispatch('device',device=key,enabled=enabled)
 def sync(self):
  self.syncing=True
  for k,w in self.switches.items():w.set_active(self.state[k])
  for k,b in self.presets.items():
   b.remove_css_class('selected')
   if self.state['preset']==k and not self.state['sleeping']:b.add_css_class('selected')
  name='Boa noite' if self.state['sleeping'] else PRESETS.get(self.state['preset'],('Sua cor',))[0]
  self.hero_title.set_label(name)
  self.hero_note.set_label(('Gabinete apagado' if self.state['sleeping'] else ('Último preset enviado' if self.state['applied_at'] else 'Cor selecionada'))+' · #'+self.state['color'])
  self.hex.set_text('#'+self.state['color']);self.scale.set_value(self.state['brightness']);self.percent.set_label(f'{self.state["brightness"]}%');self.art.queue_draw();self.syncing=False
 def refresh_stats(self):
  data={'cpu_temp':53,'gpu_temp':50} if DEMO else telemetry()
  self.cpu_stat.set_label(f'{data["cpu_temp"]:.0f} °C' if data else '—');self.gpu_stat.set_label(f'{data["gpu_temp"]:.0f} °C' if data else '—')
  self.screen_note.set_label('Recebendo sensores ao vivo' if data else 'Sem atualização recente')
  return True
 def dispatch(self,action,**params):
  if self.busy:return
  self.busy=True;self.status.remove_css_class('error');self.status.set_label('Aplicando… só um instante.');self.spinner.start()
  for w in self.actions:w.set_sensitive(False)
  def work():
   try:s,msg=self.control.action(action,**params);err=False
   except Exception as e:s=self.control.load();msg=str(e);err=True
   GLib.idle_add(done,s,msg,err)
  def done(s,msg,err):
   self.state=s;self.sync();self.busy=False;self.spinner.stop();self.status.set_label(msg)
   if err:self.status.add_css_class('error')
   for w in self.actions:w.set_sensitive(True)
   self.refresh_stats();return False
  threading.Thread(target=work,daemon=True).start()

if __name__=='__main__':App().run([sys.argv[0]])
