"""Hidden-input launcher. Tokens enter only the selected child process environment."""
import argparse,json,os,subprocess,sys
from getpass import getpass
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('roles',choices=['writer,viewer','viewer','native','viewer,native']);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
if not a.command:p.error('Supply a fleet command or test')
if '--config' in a.command:p.error('Configuration is supplied by the launcher')
cfg=json.loads(a.config.read_text(encoding='utf8'));env={k:v for k,v in os.environ.items() if not k.startswith('AXOLDB_')}
for role in a.roles.split(','):
 variable=cfg[role+'TokenEnvironment'];env[variable]=getpass('Scoped '+role+' credential (hidden): ')
if a.command[0]=='test':
 t=argparse.ArgumentParser();t.add_argument('--run',required=True);t.add_argument('--native-record',type=Path,required=True);t.add_argument('--output',type=Path,required=True);args=t.parse_args(a.command[1:])
 env.update(FLEET_TEST_CONFIG=str(a.config.resolve()),FLEET_TEST_RUN=args.run,FLEET_NATIVE_RECORD=str(args.native_record.resolve()))
 command=[sys.executable,'-B','tests/run.py','integration','--output',str(args.output)]
else:command=[sys.executable,'-B','-m','fleet',*a.command,'--config',str(a.config)]
sys.exit(subprocess.run(command,cwd=Path(__file__).resolve().parent,env=env).returncode)
