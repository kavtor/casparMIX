#!/usr/bin/env python3
"""Verify checksums and identical combined/ordered patch trees on pinned upstream."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--release',type=Path,required=True);p.add_argument('--upstream-checkout',type=Path);a=p.parse_args();release=a.release.resolve();manifest=json.loads((release/'manifest.json').read_text());pin=manifest['upstream'];commit=pin['commit']
 if pin['repository']!='https://github.com/CasparCG/server.git' or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Unexpected upstream pin')
 for line in (release/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split(None,1);path=(release/name.strip()).resolve()
  if release not in path.parents or path.is_symlink():raise ValueError('Unsafe checksum path')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Checksum mismatch: '+name)
 combined=release/f'casparMIX-{manifest["casparmix_version"]}-casparcg-{pin["tag"].removeprefix("v").removesuffix("-stable")}.patch'
 ordered=[]
 for change in manifest['changes']:
  path=(release/change['patch']).resolve()
  if release not in path.parents:raise ValueError('Unsafe patch path')
  ordered.append(path)
 with tempfile.TemporaryDirectory(prefix='casparmix-verify-') as d:
  root=Path(d);upstream=a.upstream_checkout.resolve() if a.upstream_checkout else root/'upstream'
  def run(*args,cwd=None):return subprocess.check_output(args,cwd=cwd,stderr=subprocess.STDOUT)
  if not a.upstream_checkout:
   run('git','init','-q',str(upstream));run('git','-C',str(upstream),'fetch','--depth=1',pin['repository'],commit)
  run('git','-C',str(upstream),'cat-file','-e',commit+'^{commit}')
  trees=[]
  for label,patches in [('combined',[combined]),('ordered',ordered)]:
   work=root/label;run('git','clone','--quiet','--shared','--no-checkout',str(upstream),str(work));run('git','-C',str(work),'checkout','--quiet','--detach',commit)
   for patch in patches:run('git','-C',str(work),'apply','--index',str(patch))
   trees.append(run('git','-C',str(work),'write-tree').decode().strip())
  if trees[0]!=trees[1]:raise ValueError('Combined/ordered tree mismatch')
  print('VERIFIED checksums, upstream pin and identical combined/ordered tree:',trees[0])
if __name__=='__main__':main()
