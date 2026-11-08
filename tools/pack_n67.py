"""Pack a LINKED Thumb ELF, retaining only internal ABS32 slide relocations.

This is not an insmod .ko: Lua places its zero-filled image in retained heap.
Relative branches are already resolved by LLD and invariant under a slide.
"""
from pathlib import Path
import json,struct,hashlib
from elftools.elf.elffile import ELFFile
BASE=0x1d100000
def pack(src,out):
 with Path(src).open('rb') as f:
  elf=ELFFile(f)
  assert elf.elfclass==32 and elf.little_endian and elf['e_machine']=='EM_ARM' and elf['e_type']=='ET_EXEC'
  alloc=[s for s in elf.iter_sections() if s['sh_flags']&2 and s['sh_size']]
  end=max(s['sh_addr']+s['sh_size'] for s in alloc)
  assert min(s['sh_addr'] for s in alloc)==BASE and end-BASE<512*1024
  image=bytearray((end-BASE+3)&~3)
  for s in alloc:
   if s['sh_type']!='SHT_NOBITS':image[s['sh_addr']-BASE:s['sh_addr']-BASE+s['sh_size']]=s.data()
  symbols=elf.get_section_by_name('.symtab')
  undefined={s.name for s in symbols.iter_symbols() if s['st_shndx']=='SHN_UNDEF' and s.name}
  # Clang's discarded ARM unwind records retain these symbol-table names.
  assert undefined <= {'__aeabi_unwind_cpp_pr0','__aeabi_unwind_cpp_pr1'},undefined
  reloc=[];counts={}
  for s in elf.iter_sections():
   if s['sh_type']!='SHT_REL':continue
   if not elf.get_section(s['sh_info'])['sh_flags']&2:continue
   for r in s.iter_relocations():
    assert symbols.get_symbol(r['r_info_sym']).name not in undefined, 'unresolved alloc relocation'
    typ=r['r_info_type'];off=r['r_offset']-BASE;counts[typ]=counts.get(typ,0)+1
    assert typ in (0,2,10,30),f'unsupported runtime relocation {typ}'
    if typ==2:
     assert off%4==0 and 0<=off<=len(image)-4
     value=struct.unpack_from('<I',image,off)[0]
     sym=symbols.get_symbol(r['r_info_sym'])
     assert BASE<=sym['st_value']<=end, f'external ABS32 {sym.name}'
     assert BASE<=value<=end+1, f'non-image ABS32 {value:x}'
     reloc.append(off)
  reloc=sorted(set(reloc))
  funcs={s.name:s['st_value']-BASE for s in symbols.iter_symbols() if s['st_info']['type']=='STT_FUNC' and BASE<=s['st_value']<end}
  m={'abi':'N67 CN 3.1.190','link_base':BASE,'size':len(image),'code_size':elf.get_section_by_name('.text')['sh_size'],
   'entry':funcs['chaos_n67_init'],'functions':funcs,'relocations':reloc,'relocation_types':counts,'sha256':hashlib.sha256(image).hexdigest()}
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(image);out.with_suffix('.json').write_text(json.dumps(m,indent=2),'utf-8')
 print(f'Rust image {len(image)} bytes; {len(reloc)} internal ABS32 relocations; no unresolved runtime references')
 return image,m
def slide(image,m,base):
 b=bytearray(image)
 for off in m['relocations']:
  v=struct.unpack_from('<I',b,off)[0];struct.pack_into('<I',b,off,(v+base-m['link_base'])&0xffffffff)
 return b
if __name__=='__main__':
 import sys
 pack(sys.argv[1],sys.argv[2])
