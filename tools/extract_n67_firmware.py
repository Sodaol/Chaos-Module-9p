"""Extract only build inputs from the N67 CN 3.1.190 full OTA; never flash it."""
import argparse,hashlib,io,struct,zipfile
from pathlib import Path

AP_SHA256='3e264bc267431ec71843cc7c2e4acd928b9280ea39ee1cd888636adcebabf82f'

def extract(source,destination):
    data=Path(source).read_bytes()
    if data[:4]!=b'\x60ZZ~' or data[4:12].rstrip(b'\0')!=b'3.1.190':
        raise ValueError('Expected full N67 3.1.190 OTA header')
    base=struct.unpack_from('<I',data,84)[0]
    if data[base:base+4]!=b'ZZZ~':raise ValueError('Missing inner OTA table')
    first=struct.unpack_from('<I',data,base+84)[0]
    selected={b'/data/ota/app/vela_ap.bin':'vela_ap.bin',
              b'/system/font/MiSans-Regular.ttf':'MiSans-Regular.ttf'}
    result={}
    for at in range(base+80,base+first-127,128):
        _,offset,size=struct.unpack_from('<III',data,at)
        name=data[at+12:at+128].split(b'\0',1)[0]
        if name not in selected:continue
        if offset<first or base+offset+size>len(data):raise ValueError('Invalid OTA bounds')
        payload=data[base+offset:base+offset+size]
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members=archive.namelist()
            if len(members)!=1:raise ValueError('Expected one member in build input ZIP')
            payload=archive.read(members[0])
        digest=hashlib.sha256(payload).hexdigest()
        if selected[name]=='vela_ap.bin' and digest!=AP_SHA256:
            raise ValueError('AP fingerprint differs from the supported 3.1.190 firmware')
        result[selected[name]]=(payload,digest)
    if set(result)!=set(selected.values()):raise ValueError('Required build inputs missing')
    output=Path(destination);output.mkdir(parents=True,exist_ok=True)
    for name,(payload,digest) in result.items():
        (output/name).write_bytes(payload)
        print(f'{name}: {len(payload)} bytes SHA256 {digest}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ota');parser.add_argument('destination')
    args=parser.parse_args();extract(args.ota,args.destination)
