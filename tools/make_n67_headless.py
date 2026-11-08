from pathlib import Path
import json,hashlib,shutil,zipfile
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
OUT=R/'n67/headless-test';OUT.mkdir(exist_ok=True)
s=(G/'main.lua').read_bytes()
# Reuse the exact current installer implementation and encoded resources.
s=s[:s.index(b'local root=lvgl.Object(nil,')]
s=s.replace(b"/data/app/watchface/market/990000000029/_lua/_Lua/",b"/data/chaos/headless-test/")
s=s.replace(b"'/data/chaos-n67.log','/data/chaos-n67.mark','/data/chaos-n67-read.txt'",b"'/data/chaos/headless-test/boot.log','/data/chaos/headless-test/boot.mark','/data/chaos/headless-test/read.txt'")
s=s.replace(b'local function yield_step() coroutine.yield() end',b'local function yield_step() coroutine.yield() end')
header=b"""-- Manual headless experiment; does not install or modify system startup.
-- Default preflight performs no native calls or timer/object creation.
local dis=io.open('/data/chaos/disable','rb')
if dis then dis:close();print('DISABLED /data/chaos/disable');return end
"""
tail=b"""
local mode=(arg and arg[1]) or 'preflight'
local function version()
 local f=assert(io.open('/system/version/version.ini','rb'),'version unavailable')
 local s=f:read('*a');f:close();return s:match('version%s*=%s*([%d.]+)')
end
assert(version()=='3.1.190','firmware version mismatch')
assert(type(lvgl.Timer)=='function' and type(lvgl.FLAG)=='table','LVGL API missing')
assert(#MODULE_BIN==MODULE_SIZE and #CHAOS_BIN==CHAOS_SIZE,'payload mismatch')
assert(#CHAOS_RELOCS%4==0,'relocation file malformed')
local last=-4
for i=1,#CHAOS_RELOCS,4 do
 local off=string.unpack('<I4',CHAOS_RELOCS,i)
 assert(off%4==0 and off>last and off+4<=CHAOS_SIZE,'relocation order/bounds')
 local val=word(CHAOS_BIN,off)
 assert(val>=0x1d100000 and val<=0x1d100000+CHAOS_SIZE+1,'relocation value')
 last=off
end
print('PREFLIGHT OK',RELEASE,'bridge',MODULE_SIZE,'core',CHAOS_SIZE)
if mode=='preflight' then return end
assert(mode=='run','usage: lua boot-test.lua [preflight|run]')
local function sleep_ms(ms)
 local ok,k,c=os.execute('usleep '..tostring(ms*1000))
 assert(ok==true and k=='exit' and c==0,'sleep failed')
end
-- Keep this Lua VM alive after handoff until its lifecycle is proven on device.
-- The application registry mutation still runs in bt_reg_tick on the GUI timer.
local co=coroutine.create(function()
 mark('headless manual start');probe_batch();load_module()
 local found=native(fn(OFF_INSTALL_CHECK),0x0C4467B5,APP_ID)
 if heap(found,4) then mark('already installed; no replacement');return end
 assert(found==0,'registry not ready '..tostring(found))
 ensure_chaos_dir();write_icon()
 BLOCK=native(MALLOC,RES.size);own(BLOCK,RES.size)
 copy_fast(BLOCK,resident(BLOCK));sync_fast(BLOCK+0xE8,8)
 load_chaos();arm_registrar();armed=true
 for i=1,60 do
  sleep_ms(1000)
  local b=read(BLOCK+0xF0,96);local stage=word(b,4)
  mark(string.format('stage=%d bc=%d tries=%d launcher=%x ticks=%d',stage,word(b,0x5c),word(b,0x4c),word(b,0x40),word(b,0x30)))
  if stage==3 and heap(word(b,0x40),32) then
   mark('registered; VM retained');print('REGISTERED; keep this worker running')
   while true do sleep_ms(1000);coroutine.yield() end
  end
  assert(stage<0x100,'registration error '..stage)
 end
 error('registration timeout; VM retained for diagnosis')
end)
while coroutine.status(co)~='dead' do
 local ok,e=coroutine.resume(co)
 if not ok then
  mark('ERROR '..tostring(e));print('ERROR',e)
  -- Do not destroy a potentially live Lua timer after partial handoff.
  if REG_TIMER then while true do sleep_ms(1000) end end
  return
 end
 sleep_ms(10)
end
"""
(OUT/'boot-test.lua').write_bytes(header+s+tail)
for f in G.glob('chaos-*.dat'):shutil.copyfile(f,OUT/f.name)
meta={'system_startup_installed':False,'device_verified':False,'version':'ui15-photo2','vm_lifecycle':'retained during manual run','source_main_sha256':hashlib.sha256((G/'main.lua').read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(OUT)
