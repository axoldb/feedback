import argparse,json
from pathlib import Path
from . import demo
def main():
 parser=argparse.ArgumentParser(description='Public deterministic fleet example; no model calls by default')
 parser.add_argument('command',choices=['offline','run','read','replay','serve','proposal','native','native-read'])
 parser.add_argument('--config',type=Path);parser.add_argument('--run',default='my-first-run');parser.add_argument('--through',type=int,choices=[0,1],default=1)
 parser.add_argument('--output',type=Path);parser.add_argument('--recorded',type=Path);parser.add_argument('--port',type=int,default=8765)
 args=parser.parse_args()
 if args.command in ['run','read','serve','native','native-read'] and args.config is None:parser.error('--config is required')
 if args.command=='offline':value=demo.offline()
 elif args.command=='run':value=demo.run(args.config,args.run,args.through)
 elif args.command=='read':value=demo.read(args.config,args.run)
 elif args.command=='replay':
  if args.recorded is None:parser.error('--recorded is required; replay never calls a provider')
  value=demo.replay(demo.load(args.recorded))
 elif args.command=='serve':
  from .web import serve
  return serve(args.config,args.run,args.port)
 elif args.command=='native':
  from .native import run
  value=run(args.config,args.run,args.output)
 elif args.command=='native-read':
  if args.recorded is None:parser.error('--recorded is required')
  from .native import verify
  value=verify(args.config,demo.load(args.recorded))
 elif args.command=='proposal':
  if args.recorded is None:parser.error('--recorded is required; use the separately documented optional gateway for live inference')
  from .proposal import recorded
  value=recorded(args.recorded)
 if args.output:demo.save(args.output,value)
 # Avoid unrestricted payload/error logging; complete data is only in the explicit output.
 print(json.dumps({'command':args.command,'status':'PASS','scientificHash':value.get('scientificHash'),'generations':len(value.get('generations',[])) if isinstance(value.get('generations'),list) else value.get('generations')}))
if __name__=='__main__':main()
