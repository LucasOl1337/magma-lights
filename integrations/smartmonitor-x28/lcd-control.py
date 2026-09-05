#!/usr/bin/env python3
"""X28 CDC display control, based on the installed manufacturer's application.
Normal 0x66 clock/brightness frame only. No firmware or cooling commands.
Brightness 0 requests the current value; sleep uses brightness 1 and idle timeout 1.
"""
import argparse, datetime, fcntl, os, select, termios, time
from pathlib import Path

def crc(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return value

def device():
    for tty in Path('/sys/class/tty').glob('ttyACM*'):
        for parent in (tty/'device').resolve().parents:
            try:
                if (parent/'idVendor').read_text().strip() == '1a86' and (parent/'idProduct').read_text().strip() == '8040':
                    return '/dev/'+tty.name
            except FileNotFoundError:
                pass
    raise SystemExit('Telinha SmartMonitor X28 não encontrada no USB.')

parser = argparse.ArgumentParser(description='Controle da telinha SmartMonitor X28')
parser.add_argument('mode', choices=['off','on','status'])
args = parser.parse_args()
brightness = {'off':1, 'on':100, 'status':0}[args.mode]
idle_timeout = 1 if args.mode == 'off' else 5
fd = os.open(device(), os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try:
    fcntl.ioctl(fd, termios.TIOCEXCL)
    cfg = termios.tcgetattr(fd)
    cfg[0] = cfg[1] = cfg[3] = 0
    cfg[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    cfg[4] = cfg[5] = termios.B1000000
    cfg[6][termios.VMIN] = cfg[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, cfg)
    termios.tcflush(fd, termios.TCIOFLUSH)
    for _ in range(3):
        now = datetime.datetime.now()
        packet = bytearray([0x66, 0, 14, 1, (now.year+48)&255, now.month, now.day,
                            now.hour, now.minute, now.second, now.isoweekday()+idle_timeout*8, brightness])
        packet += crc(packet).to_bytes(2, 'big')
        os.write(fd, packet)
        termios.tcdrain(fd)
        end = time.monotonic()+0.4
        while time.monotonic()<end:
            if select.select([fd], [], [], max(0,end-time.monotonic()))[0]:
                reply = os.read(fd,4096)
                for i in range(max(0,len(reply)-6)):
                    frame=reply[i:i+7]
                    if frame[:3] == b'\x69\x00\x07' and crc(frame[:-2]) == int.from_bytes(frame[-2:],'big'):
                        print(f'Brilho informado pela telinha: {frame[3]}%')
    print({'off':'Brilho mínimo e temporizador de apagamento enviados.', 'on':'Brilho 100% enviado.', 'status':'Consulta enviada.'}[args.mode])
finally:
    fcntl.ioctl(fd, termios.TIOCNXCL)
    os.close(fd)
