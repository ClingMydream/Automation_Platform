"""Conservative one-off resource maintenance. Never prunes projects, data, or tagged images."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone


def run(*args, **kw):
    return subprocess.run(args, check=True, text=True, **kw)


def output(*args):
    return subprocess.check_output(args, text=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true',help='Apply approved system log limits and remove verified empty legacy volumes')
    args=parser.parse_args()
    if os.name!='posix':raise SystemExit('Run on the target Linux server, not the local workstation')
    source=Path(__file__).resolve().parent
    targets=[(source/'60-cling-resource-limits.conf',Path('/etc/systemd/journald.conf.d/60-cling-resource-limits.conf')),
             (source/'cling-system-logs.logrotate',Path('/etc/logrotate.d/cling-system-logs'))]
    for src,dst in targets:
        assert src.is_file()
        print(json.dumps({'source':str(src),'target':str(dst)},ensure_ascii=False))
    empty=[]
    compose=Path('/opt/automation-platform/docker-compose.yml').read_text()
    for name in ('automation-platform_attachment-data','automation-platform_gradle-cache'):
        inspect=subprocess.run(['docker','volume','inspect',name],capture_output=True,text=True)
        if inspect.returncode:continue
        data=json.loads(inspect.stdout)[0]
        mount=Path(data['Mountpoint']).resolve()
        assert mount.parent.parent==Path('/var/lib/docker/volumes') and mount.name=='_data', 'Unexpected volume mount'
        refs=output('docker','ps','-aq','--filter','volume='+name).strip()
        suffix=name.removeprefix('automation-platform_')
        if refs or any(mount.iterdir()) or suffix in compose:
            raise SystemExit('Refusing nonempty, referenced, or configured volume: '+name)
        empty.append(name)
    print(json.dumps({'verified_empty_unused_volumes':empty,'apply':args.apply}))
    if not args.apply:return
    if os.geteuid()!=0:raise SystemExit('Requires root')
    backup=Path('/opt/cling-maintenance-backups')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True,mode=0o700)
    before=shutil.disk_usage('/')
    manifest=[]
    applied=[]
    try:
        for src,dst in targets:
            original=dst.exists()
            saved=backup/dst.name
            if original:shutil.copy2(dst,saved)
            manifest.append({'path':str(dst),'existed':original,'backup':str(saved) if original else None})
            dst.parent.mkdir(parents=True,exist_ok=True)
            # Plain LF and no BOM; do not change existing source configs outside this drop-in.
            dst.write_text(src.read_text(encoding='utf-8-sig'),encoding='utf-8')
            dst.chmod(0o644);applied.append(dst)
        run('/usr/sbin/logrotate','--debug','/etc/logrotate.d/cling-system-logs')
        run('systemctl','restart','systemd-journald')
        run('systemctl','is-active','--quiet','systemd-journald')
        run('journalctl','--rotate')
        run('journalctl','--vacuum-size=512M','--vacuum-time=14d')
        # Existing text logs are compressed, not discarded; rsyslog reopens new files via HUP.
        run('/usr/sbin/logrotate','--force','/etc/logrotate.d/cling-system-logs')
        run('systemctl','is-active','--quiet','rsyslog')
        run('dnf','clean','all')
        # Revalidate immediately before removing only the two known empty legacy volumes.
        for name in empty:
            data=json.loads(output('docker','volume','inspect',name))[0]
            if output('docker','ps','-aq','--filter','volume='+name).strip() or any(Path(data['Mountpoint']).iterdir()):
                raise RuntimeError('Volume changed during audit; refusing removal: '+name)
            run('docker','volume','rm',name)
    except Exception:
        for item in reversed(manifest):
            path=Path(item['path'])
            if item['existed']:shutil.copy2(item['backup'],path)
            elif path in applied:path.unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','systemd-journald'],check=False)
        raise
    after=shutil.disk_usage('/')
    record={'backup':str(backup),'configurations':manifest,'disk_used_before':before.used,
            'disk_used_after':after.used,'bytes_freed':before.used-after.used,'removed_empty_volumes':empty,
            'preserved':'all containers, project sources, databases, tagged images, test evidence and deployment backups'}
    (backup/'maintenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
