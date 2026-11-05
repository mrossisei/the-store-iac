"""Regresión de túneles: simula expiración por inactividad sin acceder a AWS."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, signal, sys, time
root = pathlib.Path(os.environ['TUNNEL_TEST_ROOT'])
args = sys.argv[1:]
def value(flag): return args[args.index(flag) + 1]
def event(text):
    with (root / 'events').open('a') as f: f.write(text + '\n')
if pathlib.Path(sys.argv[0]).name == 'sleep':
    time.sleep(0.04)
elif pathlib.Path(sys.argv[0]).name == 'kubectl':
    config = pathlib.Path(value('--kubeconfig')).read_text()
    port = '16443' if ':16443' in config else '26443'
    active = root / ('active-' + port)
    try:
        data = json.loads(active.read_text())
        if data['target'] not in config: sys.exit(1)
        os.kill(data['pid'], 0)
        (root / ('heartbeat-' + port)).touch()
        print('ok')
    except (OSError, ValueError): sys.exit(1)
elif args[:2] == ['ssm', 'send-command']:
    event('config ' + value('--instance-ids'))
    print('command-id')
elif args[:2] == ['ssm', 'wait']:
    pass
elif args[:2] == ['ssm', 'get-command-invocation']:
    print('server: https://127.0.0.1:6443\ninstance: ' + value('--instance-id'))
elif args[:2] == ['ssm', 'start-session']:
    port = json.loads(value('--parameters'))['localPortNumber'][0]
    target = value('--target')
    active = root / ('active-' + port)
    heartbeat = root / ('heartbeat-' + port)
    heartbeat.touch()
    active.write_text(json.dumps({'pid': os.getpid(), 'target': target}))
    event('start ' + port + ' ' + target)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while time.time() - heartbeat.stat().st_mtime < 0.4:
            time.sleep(0.02)
        event('expired ' + port)
    finally:
        try:
            if json.loads(active.read_text())['pid'] == os.getpid(): active.unlink()
        except (OSError, ValueError): pass
else:
    raise RuntimeError(args)
'''


class TunnelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kind-tunnel-test-')
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'bin').mkdir()
        self.script = self.root / 'scripts' / 'acceso-kind.sh'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'acceso-kind.sh', self.script)
        for name in ('aws', 'kubectl', 'sleep'):
            executable = self.root / 'bin' / name
            executable.write_text(MOCK)
            executable.chmod(0o755)
        self.env = dict(os.environ, TUNNEL_TEST_ROOT=str(self.root),
                        PATH=str(self.root / 'bin') + ':' + os.environ['PATH'])

    def tearDown(self):
        # Cada mock y supervisor está en una sesión separada; no tocar procesos reales.
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            try:
                command = (process / 'cmdline').read_bytes()
                if str(self.root).encode() in command:
                    os.kill(int(process.name), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
        time.sleep(0.1)
        self.temp.cleanup()

    def connect(self, a='i-test-a', b='i-test-b'):
        result = subprocess.run(['bash', str(self.script), 'us-east-1', a, b],
                                env=self.env, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        configs = json.loads(result.stdout)  # Stdout debe seguir siendo solo JSON.
        return configs

    def events(self):
        return (self.root / 'events').read_text().splitlines()

    def test_upload_wait_does_not_expire_sessions_and_reuses_them(self):
        self.connect()
        time.sleep(1.0)  # Más del doble del idle timeout simulado.
        self.assertFalse(any(line.startswith('expired ') for line in self.events()))
        self.connect()
        self.assertEqual(sum(line.startswith('start ') for line in self.events()), 2)
        self.assertEqual(sum(line.startswith('config ') for line in self.events()), 2)

    def test_reopens_expired_tunnel(self):
        self.connect()
        session = json.loads((self.root / 'active-16443').read_text())
        os.kill(session['pid'], signal.SIGTERM)
        time.sleep(0.1)
        self.connect()
        self.assertEqual(self.events().count('start 16443 i-test-a'), 2)

    def test_new_instance_does_not_reuse_old_cluster(self):
        self.connect()
        configs = self.connect(a='i-replacement-a')
        self.assertIn('i-replacement-a', Path(configs['kubeconfig_a']).read_text())
        self.assertIn('start 16443 i-replacement-a', self.events())
        self.assertEqual(self.events().count('start 26443 i-test-b'), 1)


if __name__ == '__main__':
    unittest.main()
