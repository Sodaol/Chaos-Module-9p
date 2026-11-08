"""Execute actual ARM ID-only preflight; native lookup is explicit fixture."""
from pathlib import Path
import json
from test_port_pages import PortBand
from unicorn.arm_const import *
G=Path(__file__).resolve().parents[1]/'n67/generated'
class IdBand(PortBand):
 def __init__(self,base):self.ids={};self.lookups=[];super().__init__(base)
 def hook(self,u,a,n,ud):
  if a==0xc4467b4:
   id=u.reg_read(UC_ARM_REG_R0);self.lookups.append(id);u.reg_write(UC_ARM_REG_R0,self.ids.get(id,0));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=IdBand(base);code=(G/'bridge.bin').read_bytes();meta=json.loads((G/'bridge.json').read_text());bridge=0x1d700000;b.u.mem_map(bridge,(len(code)+4095)&~4095);b.u.mem_write(bridge,code);b.sym['pf']=bridge+meta['functions']['bt_entry_preflight']['offset']
 new=b.alloc(60);old=b.alloc(60);b.w32(new+0x10,0xe7d4);b.w32(old+0x10,0xe7c3)
 for ids,mask in [({},0),({0xe7d4:new},1),({0xe7c3:old},2),({0xe7d4:new,0xe7c3:old},3),({0xe7d4:old},0),({0xe7d4:1},0)]:
  b.ids=ids;b.lookups=[];assert b.call('pf')==mask;assert b.lookups==[0xe7d4,0xe7c3]
 # No package/page/health checks: an orphan page is deliberately irrelevant.
 b.ids={};b.w32(0x200a0218,0xe7d40000);assert b.call('pf')==0
 print(f'PASS ID-only ARM {base:x}: exactly two ID queries; old/new/both/absent, wrong ID and invalid pointer rejected; page/package/health not inspected')
