"""Install the Mac recovery mirror using existing Railway account access."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--project', required=True)
parser.add_argument('--environment', required=True)
parser.add_argument('--service', required=True)
args = parser.parse_args()
os.umask(0o077)
root = Path.home() / 'Library/Application Support/OpenWorld/recovery-mirror'
root.mkdir(mode=0o700, parents=True, exist_ok=True)
root.chmod(0o700)
source = Path(__file__).resolve().parent.parent
shutil.copyfile(source / 'ops/mirror-recovery.py', root / 'sync.py')
shutil.copyfile(source / 'app/backend/recovery.py', root / 'recovery.py')
subprocess.run([sys.executable, '-m', 'venv', str(root / 'runtime')], check=True, capture_output=True)
python = root / 'runtime/bin/python'
subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                'cryptography==50.0.2'], check=True, capture_output=True)
# 4.29 uses the supported relay with existing CLI auth. Later releases require
# separately registered SSH keys; do not silently widen the owner's access.
subprocess.run([shutil.which('npm'), 'install', '--prefix', str(root / 'tools'),
                '--omit=dev', '--no-audit', '--no-fund', '@railway/cli@4.29.0'],
               check=True, capture_output=True)
railway = root / 'tools/node_modules/.bin/railway'
config = {**vars(args), 'railway': str(railway)}
(root / 'mirror-config.json').write_text(json.dumps(config, indent=2) + '\n')
plist = {'Label': 'com.openworld.recovery-mirror',
         'ProgramArguments': [str(python), str(root / 'sync.py')],
         'WorkingDirectory': str(root), 'StartInterval': 3600,
         'EnvironmentVariables': {'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'},
         'StandardOutPath': str(root / 'mirror.log'),
         'StandardErrorPath': str(root / 'mirror-error.log')}
# First prove foreground transfer, checksums, encryption and offline restore.
subprocess.run(plist['ProgramArguments'], cwd=root, check=True)
launch = Path.home() / 'Library/LaunchAgents/com.openworld.recovery-mirror.plist'
launch.parent.mkdir(parents=True, exist_ok=True)
launch.write_bytes(plistlib.dumps(plist))
domain = 'gui/' + str(os.getuid())
subprocess.run(['launchctl', 'bootout', domain + '/' + plist['Label']], capture_output=True)
subprocess.run(['launchctl', 'bootstrap', domain, str(launch)], check=True)
subprocess.run(['launchctl', 'kickstart', domain + '/' + plist['Label']], check=True)
print(json.dumps({'installed': True, 'backgroundCheckStarted': True,
                  'statusFile': str(root / 'status.json'),
                  'limitation': 'Mac must be awake and Railway CLI access must remain valid.'}))
