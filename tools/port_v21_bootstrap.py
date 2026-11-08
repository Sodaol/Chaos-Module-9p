"""Port the audited v2.1 self-contained injection routines into a fresh bridge.
Only the independent prefix changes length. Relative calls among the remaining
functions retain their distances; calls into that prefix are explicitly rejected.
"""
from pathlib import Path
import hashlib,json
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
R=Path(__file__).resolve().parents[1];G=R/'n67/generated';V=R/'n67/injection-v21'
reference=json.loads((V/'reference.json').read_text('utf8'))
for name,digest in reference['files'].items():
    assert hashlib.sha256((V/name).read_bytes()).hexdigest()==digest,name
j=json.loads((G/'bridge.json').read_text('utf8'));old=(G/'bridge.bin').read_bytes()
assert len(old)==j['size'] and hashlib.sha256(old).hexdigest()==j['sha256']
names=('bt_magic','bt_copy_bytes','bt_sync_code')
cut=max(j['functions'][n]['offset']+j['functions'][n]['size'] for n in names)
prefix=(V/'bootstrap.bin').read_bytes();delta=len(prefix)-cut
assert cut==210 and len(prefix)==218 and delta%2==0
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
for name,f in j['functions'].items():
    if name in names:continue
    assert f['offset']>=cut
    for i in md.disasm(old[f['offset']:f['offset']+f['size']],f['offset']):
        if i.mnemonic in ('bl','b','b.w','cbz','cbnz') and '#' in i.op_str:
            target=int(i.op_str.rsplit('#',1)[1],0)
            assert target>=cut,('cross-prefix relative branch',name,hex(i.address),hex(target))
new=bytearray(prefix+old[cut:])
for name,f in j['functions'].items():
    if name not in names:f['offset']+=delta
j['functions']['bt_magic'].update(offset=0,size=10)
j['functions']['bt_copy_bytes'].update(offset=10,size=76)
j['functions']['bt_sync_code'].update(offset=86,size=132)
timer=(V/'timer-bootstrap.bin').read_bytes();f=j['functions']['bt_timer_bootstrap']
assert len(timer)==f['size']==90
new[f['offset']:f['offset']+f['size']]=timer
j['size']=len(new);j['sha256']=hashlib.sha256(new).hexdigest()
j['ranges']=[{'offset':0,'size':len(new),'kind':'thumb'}]
j['injection_reference']=reference['reference_sha256']
(G/'bridge.bin').write_bytes(new);(G/'bridge.json').write_text(json.dumps(j,indent=2),'utf8')
print('Ported v2.1 injection: exact 218-byte copy/cache prefix and 90-byte timer bootstrap; remaining relative calls checked')
