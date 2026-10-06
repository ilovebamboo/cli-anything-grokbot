"""Explicit opt-in launch/restart for local Electron CDP. Never force-kill."""
import socket
import subprocess
import time
from cli_anything.grokbot.utils.cdp import CDP, ControlError, discover
from cli_anything.grokbot.utils.grokbot_backend import find_app, app_open


def connect_app(port=9337, restart=False):
    find_app()
    try:
        target = discover(port)
        return {'connected': True, 'endpoint': f'http://127.0.0.1:{port}', 'target': target['id'],
                'restarted': False}
    except ControlError:
        if not restart:
            raise
    probe = socket.socket()
    try:
        probe.bind(('127.0.0.1', port))
    except OSError as e:
        raise ControlError('Port already occupied; refusing to restart Grok Bot') from e
    finally:
        probe.close()
    pids = lambda: subprocess.run(
        ['pgrep','-f',r'^/Applications/Grok Bot.app/Contents/MacOS/Grok Bot($| )'],
        capture_output=True, text=True).returncode == 0
    if pids():
        r = subprocess.run(['osascript','-e','tell application "Grok Bot" to quit'],
                           capture_output=True, text=True, timeout=20)
        if r.returncode: raise ControlError('Grok Bot refused graceful quit; not force-killing')
        end = time.monotonic()+20
        while pids() and time.monotonic()<end: time.sleep(.25)
        if pids(): raise ControlError('Graceful quit did not finish; not force-killing')
    r = subprocess.run(['open','-a','/Applications/Grok Bot.app','--args',
                        '--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}'],
                       capture_output=True,text=True,timeout=10)
    if r.returncode:
        app_open()
        raise ControlError('Debug launch failed; attempted normal app launch')
    end = time.monotonic()+25
    while time.monotonic()<end:
        try:
            target=discover(port)
            return {'connected': True, 'endpoint':f'http://127.0.0.1:{port}',
                    'target':target['id'],'restarted': True,
                    'note':'Local debug port permits control by local processes; quit/reopen normally to disable.'}
        except ControlError: time.sleep(.3)
    raise ControlError('App relaunched but debug endpoint did not become ready; app left running')
