"""Flutter-specific evidence profile, invoked through tools/verify.py."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,shutil,subprocess,sys,time

APP=Path(__file__).resolve().parents[1]
ROOT=APP.parents[1]

def manifest():
    files={}
    for path in APP.rglob('*'):
        rel=path.relative_to(APP)
        if not path.is_file() or any(x in {'.dart_tool','build','.gradle','ephemeral','coverage'} for x in rel.parts):
            continue
        if path.name in {'local.properties','.flutter-plugins-dependencies'}:continue
        files[str(rel)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return files

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--flutter',default=os.environ.get('FLUTTER_BIN'))
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():parser.error('Use a new evidence directory; prior failures are preserved.')
    output.mkdir(parents=True)
    direct=Path.home()/'snap/flutter/common/flutter/bin/flutter'
    flutter=args.flutter or (str(direct) if direct.exists() else shutil.which('flutter'))
    if not flutter:parser.error('Flutter SDK unavailable')
    report={'profile':'flutter','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'environment':{'platform':platform.platform(),'architecture':platform.machine(),'python':sys.version},
        'checks':[],'limits':['Software/UI fixtures only; no Pi, aircraft, camera, speaker or ElevenLabs integration.',
            'This runner does not launch/inspect a browser or emulator. Separate UI inspection follows.']}
    def save(): (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name,cmd,timeout=900):
        started=time.monotonic()
        print('RUN: '+name,flush=True)
        with (output/(name+'.txt')).open('w') as log:
            try:
                result=subprocess.run(cmd,cwd=APP,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
                code=result.returncode
            except subprocess.TimeoutExpired:
                code=-1;log.write('\nTIMEOUT\n')
        check={'name':name,'pass':code==0,'exit_code':code,'command':cmd,
            'seconds':time.monotonic()-started,'log':name+'.txt'}
        report['checks'].append(check);save()
        print(('PASS: ' if code==0 else 'FAIL: ')+name,flush=True)
        return code==0
    run('flutter-version',[flutter,'--version'],60)
    run('pub-get',[flutter,'pub','get'],120)
    report['source_before']=manifest()
    checks=[
      ('format',[str(Path(flutter).parent/'dart'),'format','--output=none','--set-exit-if-changed','lib','test','integration_test','test_driver'],120),
      ('analyze',[flutter,'analyze'],180),
      ('tests',[flutter,'test','--coverage','--reporter=expanded'],240),
      ('backend-contract',[sys.executable,str(ROOT/'tools/portable_checks.py'),
        '--rounds','3','--flutter',flutter,'--output',str(output/'backend-contract')],180),
      ('web-production',[flutter,'build','web','--release','--no-web-resources-cdn','--base-href','/'],300),
      ('web-preview',[flutter,'build','web','--release','--no-web-resources-cdn','--dart-define=UI_PREVIEW=true','--base-href','/'],300),
      ('android-preview',[flutter,'build','apk','--debug','--dart-define=UI_PREVIEW=true','--target-platform','android-x64'],1200),
      ('android-production',[flutter,'build','apk','--debug','--target-platform','android-x64'],900),
      ('android-phone',[flutter,'build','apk','--debug'],1200),
    ]
    if sys.platform == 'darwin':
        checks.append(('macos-production',[flutter,'build','macos','--release'],900))
    for name,command,timeout in checks:
        if not run(name,command,timeout):break
        if name.startswith('web-'):
            dest=APP/'build'/name
            if dest.exists():shutil.rmtree(dest)
            shutil.copytree(APP/'build/web',dest)
        if name.startswith('android-'):
            built=APP/'build/app/outputs/flutter-apk/app-debug.apk'
            dest=APP/'build'/name
            dest.mkdir(exist_ok=True)
            shutil.copy2(built,dest/'ball-drone.apk')
            report.setdefault('artifacts',{})[name]={'path':str(dest/'ball-drone.apk'),
                'sha256':hashlib.sha256(built.read_bytes()).hexdigest()}
    report['source_after']=manifest()
    report['checks'].append({'name':'source-stability','pass':report['source_before']==report['source_after']})
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    report['pass']=len(report['checks'])==len(checks)+3 and all(c['pass'] for c in report['checks'])
    save()
    print(str(output/'report.json'),flush=True)
    return 0 if report['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
