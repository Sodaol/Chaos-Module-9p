// Execute bytes from the actual packed installer, including the LZSS decoder
// and the Lua relocation algorithm. Firmware calls are explicit test doubles.
const fs=require('fs'),path=require('path');
const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(process.env.FENGARI_PATH||path.resolve(__dirname,'../node_modules/fengari'));
const root=path.resolve(__dirname,'..'),g=path.join(root,'n67/generated');
const pack=fs.readFileSync(g+'/resource.bin');let source;
if(pack.subarray(0x28,0x34).toString()!=='990000000029')throw Error('incorrect watchface ID');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'n67/manifest.json'),'utf8'));
if(manifest.app_id!==0xe7d4||manifest.page_id!==0xe7d40000||manifest.face_id!=='990000000029')throw Error('incorrect manifest identity');
for(let i=0,n=pack.readUInt32LE(0xd8),t=pack.readUInt32LE(0xdc);i<n;i++){
 const p=pack.readUInt32LE(t+i*16+8),z=pack[p+3],s=pack.readUInt16LE(p);
 if(pack.subarray(p+20,p+20+z).toString()==='_lua/_Lua/main.lua')source=pack.subarray(p+20+z,p+20+z+s);
}
if(!source||!source.equals(fs.readFileSync(g+'/main.lua')))throw Error('packed Lua differs');
const leaves=[];for(let i=0;i<pack.readUInt32LE(0xd8);i++){const p=pack.readUInt32LE(pack.readUInt32LE(0xdc)+i*16+8),z=pack[p+3],n=pack.readUInt16LE(p);const name=pack.subarray(p+20,p+20+z).toString();if(name.endsWith('.dat'))leaves.push([name.split('/').pop(),pack.subarray(p+20+z,p+20+z+n)]);}
const assetLua="local files={}\n"+leaves.map(([n,b])=>"files['/data/app/watchface/market/990000000029/_lua/_Lua/"+n+"']='"+[...b].map(x=>'\\'+x.toString().padStart(3,'0')).join('')+"'\n").join('')+"local io={open=function(p,m) if not files[p] then return nil end;return {read=function()return files[p]end,close=function()return true end}end}\n";
const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);
function run(b){let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(b),b.length,to_luastring('N67 validation'));
 if(!e)e=lua.lua_pcall(L,0,lua.LUA_MULTRET,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));}
function take(i=-1){return Buffer.from(lua.lua_tolstring(L,i));}
let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(source),source.length,to_luastring('full installer'));
if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));lua.lua_settop(L,0);
const a=source.indexOf(Buffer.from('local function read_payload()')),z=source.indexOf(Buffer.from('\nlocal OFF_MAGIC'),a);
const prefix=Buffer.concat([Buffer.from('local MODULE_SIZE='+fs.readFileSync(g+'/bridge.bin').length+'\n'),source.subarray(a,z)]),meta=JSON.parse(fs.readFileSync(g+'/chaos.json'));
run(Buffer.concat([Buffer.from(assetLua),prefix,Buffer.from('\nassert(MODULE_BIN==nil and CHAOS_BIN==nil and CHAOS_RELOCS==nil);prepare_module();prepare_chaos();return MODULE_BIN,CHAOS_BIN,CHAOS_RELOCS')]));
if(!take(1).equals(fs.readFileSync(g+'/bridge.bin'))||!take(2).equals(fs.readFileSync(g+'/chaos.bin')))throw Error('decoded payload mismatch');
const reloc=take(3);if(reloc.length!==meta.relocations.length*4)throw Error('relocation length');
meta.relocations.forEach((x,i)=>{if(reloc.readUInt32LE(i*4)!==x)throw Error('relocation mismatch');});lua.lua_settop(L,0);
const txt=source.toString('latin1'),res=/local RES\s*=\s*(\{[^\n]+\})/.exec(txt)[1];
const resident=source.subarray(source.indexOf(Buffer.from('local function resident(')),source.indexOf(Buffer.from('local function load_chaos()')));
const load=source.subarray(source.indexOf(Buffer.from('local function load_chaos()')),source.indexOf(Buffer.from('local function write_icon()')));
const fast=source.subarray(source.indexOf(Buffer.from('local function copy_fast(')),source.indexOf(Buffer.from('local function probe_batch(')));
const orig=fs.readFileSync(g+'/chaos.bin');
for(const base of [0x1d100000,0x1d340000,0x1c900000]){
 const env=`\nlocal RES=${res};local APP_ID,PAGE_ID=0xe7d4,0xe7d40000
local BLOCK=0x3d800000;local MALLOC,OFF_COPY,OFF_SYNC=1,2,3
local module_ready,ranges=true,{};local function fn(n)return n end
local lvgl={FLAG={GESTURE_BUBBLE=65536,EVENT_BUBBLE=131072,PRESS_LOCK=8192}}
local copied,owner,synced=false,'',false
local function mark()end;local function own(p,n)ranges[#ranges+1]={p,p+n}end
local function word(s,off)return string.unpack('<I4',s,off+1)end
local function owned_string(s)owner=s;return 0x3d500000,s end

local function native(f,a,b,c,d)
 if f==MALLOC then assert(a==CHAOS_SIZE);return ${base+0x20000000} end
 if f==OFF_COPY then assert(a==${base+0x20000000} and b==0x3d500000 and c==#owner);copied=owner;return a end
 if f==OFF_SYNC then assert(a==${base+0x20000000} and b==CHAOS_SIZE and copied);synced=true;return b end
 assert(f==${(base+meta.entry)|1} and a==BLOCK and b==65536 and c==131072 and d==8192 and synced)
 return 0x4e363743 end\n`;
 run(Buffer.concat([Buffer.from(assetLua),prefix,Buffer.from(env),fast,resident,load,Buffer.from('\nlocal r=resident(BLOCK);local co=coroutine.create(load_chaos);local pauses=0;while coroutine.status(co)~="dead" do local ok,err=coroutine.resume(co);assert(ok,err);if coroutine.status(co)~="dead" then pauses=pauses+1 end end;assert(pauses>='+Math.ceil(orig.length/8192)+'+'+Math.ceil(meta.relocations.length/128)+',"installation did not yield between bounded blocks");load_chaos();return r,copied')]));
 const r=take(1),image=take(2),expected=Buffer.from(orig);
 for(const off of meta.relocations)expected.writeUInt32LE((orig.readUInt32LE(off)+base-meta.link_base)>>>0,off);
 if(!expected.equals(image))throw Error('actual Lua slide differs at '+base.toString(16));
 if(r.length!==8192||r.readUInt32LE(0x114)!==0x3d800800||r.readUInt32LE(0x11c)!==0xe7d40000||r.readUInt32LE(0x10)!==0x0004e7d4)throw Error('resident ABI');
 lua.lua_settop(L,0);
}
console.log('PASS packed Lua compilation, exact decoded payloads, 8192-byte resident, actual Lua relocation at three bases, init ABI and idempotence; bounded 8KiB decode and relocation coroutine yields');
// Exercise the real auto-install snippet: opt-in persists, delayed retries are
// bounded, registered apps never reinstall, and write failure preserves UI state.
const auto=source.subarray(source.indexOf(Buffer.from("local AUTO_PATH=")),source.indexOf(Buffer.from('keep(root);keep(scheduler)')));
const ensure=source.subarray(source.indexOf(Buffer.from('local function ensure_chaos_dir()')),source.indexOf(Buffer.from('local function write_icon()')));
if (!auto.length)throw Error('auto-install snippet missing');
for(const enabled of [false,true]){
 const env=Buffer.from(`
local SCR_W,SCR_H=336,480
local saved=${enabled?"'1'":"nil"};local fail_write=false;local dir=false
local lvgl={FLAG={SCROLLABLE=1,PRESS_LOCK=2,CLICKABLE=4,EVENT_BUBBLE=8,GESTURE_BUBBLE=16,HIDDEN=32},ALIGN={TOP_LEFT=1,CENTER=2},EVENT={SHORT_CLICKED=1},OPA=function(n)return n end}
local function object(p,props)local o={props=props,flags=0};function o:clear_flag(f)self.flags=self.flags & ~f end;function o:add_flag(f)self.flags=self.flags | f end;function o:onevent(e,c)self.tap=c end;function o:set(v)for k,x in pairs(v)do self.props[k]=x end end;return o end
lvgl.Object=object;lvgl.Label=object;lvgl.Timer=function(p)return {step=function()p.cb()end}end
local root={};local version_font={};local compatibility=object(nil,{})
local settings_view={};local settings_open=object(nil,{});local settings_back=object(nil,{})
local function centered(p,text)return object(p,{text=text})end
local main_view={};local function button(p,text,y,kind)return object(p,{}),object(p,{text=text})end
local reset=object(nil,{});local reset_caption=object(nil,{});local restart=object(nil,{});local restart_caption=object(nil,{})
local function view_show()end
local os={remove=function()end,execute=function(cmd)assert(cmd=='mkdir /data/chaos');if fail_write then return nil,'exit',65280 end;dir=true;return true,'exit',0 end}
local io={open=function(p,m)if m=='rb' then if not saved then return nil end;return {read=function()return saved end,close=function()return true end}end;if fail_write or (p:find('probe') and not dir)then return nil end;return {write=function(_,s)saved=s;return true end,close=function()return true end}end}
local function shell()end;local function keep()end
local armed=false;local work=nil;local calls=0;local function install_app()calls=calls+1 end
`);
 const checks=Buffer.from(`
assert(automatic==${enabled?'true':'false'})
assert(auto_button.flags & lvgl.FLAG.HIDDEN==0,'automatic switch must be visible')
assert(auto_button.flags & lvgl.FLAG.CLICKABLE~=0,'automatic switch must be clickable')
assert(auto_button.props.align.y_ofs+auto_button.props.h<=480,'automatic switch outside screen')
for i=1,2 do auto_timer.step()end;assert(work==nil,'started before delay')
auto_timer.step()
${enabled?'assert(work);assert(coroutine.resume(work));work=nil;assert(calls==1)':"assert(work==nil);auto_button.tap();assert(automatic and saved=='1');auto_timer.step();assert(work);assert(coroutine.resume(work));work=nil"}
for i=1,40 do auto_timer.step();if work then assert(coroutine.resume(work));work=nil end end
assert(auto_tries==3 and calls==3,'retry counts '..auto_tries..'/'..calls)
armed=true;auto_tries=0;for i=1,20 do auto_timer.step()end;assert(work==nil)
auto_button.tap();assert(not automatic and saved=='0')
for i=1,30 do auto_timer.step()end;assert(work==nil,'disabled automatic injection still started')
fail_write=true;auto_button.tap();assert(not automatic and saved=='0' and compatibility.props.text=='自动安装设置未保存','save failure')
`);
 const caseSource=Buffer.concat([env,ensure,auto,checks]);
 try{run(caseSource);}catch(e){fs.writeFileSync(g+'/auto-test-failed.lua',caseSource);throw e;}lua.lua_settop(L,0);
}
// Damaging an external payload leaf is rejected before allocation/registration.
for(const change of ["files[next(files)]=files[next(files)]:sub(2)","local p=next(files);local b=files[p];files[p]=string.char((b:byte(1)+1)%256)..b:sub(2)"]){
 let rejected=false;try{run(Buffer.concat([Buffer.from(assetLua+change+'\n'),prefix,Buffer.from('\nprepare_chaos()')]));}catch(e){rejected=/原生数据(长度错误|校验失败)/.test(e.message);}
 lua.lua_settop(L,0);if(!rejected)throw Error('damaged payload accepted');
}
console.log('PASS actual auto-install Lua: default opt-out, persistent switch, delay, bounded retries, duplicate suppression, save failure; damaged payload leaves rejected');
// Execute the actual module initializer and verify its temporary execution
// source is replaced by resident heap storage before timers can use it.
const bridgeMeta=JSON.parse(fs.readFileSync(g+'/bridge.json'));
const initStart=source.indexOf(Buffer.from('local function load_module()'));
const initEnd=source.indexOf(Buffer.from('local function resident('),initStart);
const f=bridgeMeta.functions,bootEnd=Math.max(...['bt_magic','bt_copy_bytes','bt_sync_code'].map(n=>f[n].offset+f[n].size));
const initEnv=Buffer.from(`
local MODULE_BIN=string.rep('X',${bridgeMeta.size});local MODULE_SIZE=#MODULE_BIN
local MODULE_BLOCK,EXEC=0,0;local module_ready=false;local calls=0;local copied=false;local synced=false
local function prepare_module()assert(#MODULE_BIN==MODULE_SIZE)end
local MALLOC=0x0c0f1171;local SRC=0x3d010010;local DST=0x3d100024
local OFF_COPY=${f.bt_copy_bytes.offset};local OFF_SYNC=${f.bt_sync_code.offset};local OFF_MAGIC=${f.bt_magic.offset};local BOOTSTRAP_SIZE=${bootEnd}
local function mark()end;local function heap(p,n)return p==DST and n==MODULE_SIZE end
local function own(p,n)assert(p==DST and n==((MODULE_SIZE+3)&~3))end
local function owned_string(s)assert(s==MODULE_BIN);return SRC,s end
local function sync_code(p,n)assert(p==SRC and n==BOOTSTRAP_SIZE)end
local function fn(off)return (EXEC+off)|1 end
local function native(entry,a,b,c)
 calls=calls+1
 if entry==MALLOC then assert(a>=MODULE_SIZE);return DST end
 if entry==((SRC-0x20000000+OFF_COPY)|1)then assert(EXEC==SRC-0x20000000 and a==DST and b==SRC and c==MODULE_SIZE);copied=true;return DST end
 if entry==((SRC-0x20000000+OFF_SYNC)|1)then assert(copied and a==DST and b==MODULE_SIZE);synced=true;return MODULE_SIZE end
 assert(entry==((DST-0x20000000+OFF_MAGIC)|1) and synced);return 0x4d544c42
end
`);
run(Buffer.concat([initEnv,source.subarray(initStart,initEnd),Buffer.from('\nload_module();assert(module_ready and EXEC==DST-0x20000000 and calls==4);load_module();assert(calls==4)')]));
lua.lua_settop(L,0);
console.log('PASS actual Lua bootstrap: copy/sync from temporary prefix, resident heap handoff, magic check and idempotence');
// Execute the entire shipped face, with every payload file unavailable. It
// must still build its UI without decoding/copying/relocating any module.
for(const automatic of [false,true]){
 const startupEnv=Buffer.from(`
local payload_reads,objects,native_calls=0,0,0
local lvgl={FLAG={SCROLLABLE=1,PRESS_LOCK=2,CLICKABLE=4,EVENT_BUBBLE=8,GESTURE_BUBBLE=16},ALIGN={TOP_LEFT=1,CENTER=2},EVENT={SHORT_CLICKED=1},OPA=function(n)return n end,Font=function(n,s)return s end}
local function object(parent,props)
 objects=objects+1;local o={props=props}
 function o:clear_flag(f)end;function o:add_flag(f)end
 function o:set(p)for k,v in pairs(p)do self.props[k]=v end end
 function o:onevent(e,fn)self.tap=fn end
 return o
end
lvgl.Object=object;lvgl.Label=object
lvgl.Timer=function(p)local t={props=p};function t:resume()end;return t end
package.loaded['lvgl']=nil;package.preload['lvgl']=function()return lvgl end
local io={open=function(p,m)
 if p:match('%.dat$')then payload_reads=payload_reads+1;error('payload read during face entry')end
 if m=='rb' then
  if p=='/data/chaos/auto-install' then return {read=function()return '${automatic?'1':'0'}'end,close=function()return true end}end
  return nil
 end
 return {write=function()return true end,close=function()return true end}
end}
local os={execute=function()native_calls=native_calls+1;error('native work during face entry')end}
`);
 const startupChecks=Buffer.from(`
assert(objects>10 and caption.props.text=='运行','face UI not ready')
assert(MODULE_BIN==nil and CHAOS_BIN==nil and CHAOS_RELOCS==nil,'eager payload expansion')
assert(payload_reads==0 and native_calls==0 and work==nil)
install.tap();assert(work and coroutine.status(work)=='suspended')
assert(payload_reads==0 and MODULE_BIN==nil and CHAOS_BIN==nil,'click must only queue work')
`);
 run(Buffer.concat([startupEnv,source,startupChecks]));lua.lua_settop(L,0);
}
console.log('PASS complete watchface entry: UI ready with unavailable payload files, zero payload reads, zero module decoding/native work, click only queues installation');
const installFn=source.subarray(source.indexOf(Buffer.from('local function install_app()')),source.indexOf(Buffer.from('install:onevent(lvgl.EVENT.SHORT_CLICKED')));
const ptrCode=source.subarray(source.indexOf(Buffer.from('local function runtime_ptr(')),source.indexOf(Buffer.from('local function keep(')));
for(const residentAddress of [0x3d800000,0x200a8000]){
run(Buffer.concat([Buffer.from(assetLua),prefix,Buffer.from(`
local armed=false;local APP_ID=0xe7d4;local OFF_INSTALL_CHECK=1;local OFF_INSTALL_HEALTH=3;local OFF_PREFLIGHT=3;local MALLOC=2;local BLOCK=0;local RES={size=8192};local block_ready=false;local arms=0;local copy_calls=0
local lvgl={OPA=function(n)return n end}
local function system_version()return '3.1.190'end
local function phase()end;local function probe_batch()end;local function mark()end
local restored_dir,restored_icon=false,false
local function ensure_chaos_dir()restored_dir=true end
local function write_icon()assert(restored_dir);restored_icon=true end
local function load_module()prepare_module()end;local function fn(n)return n end
local function native(f)if f==2 then return 0x3d900000 end;if f==3 then return 63 end;return ${residentAddress} end
local function heap(p,n)return p==0x3d800000 end
local function own()end
local function word(s,o)return string.unpack('<I4',s,o+1)end
local function copy_fast(p,s)
 copy_calls=copy_calls+1
 if p==0x3d9000f0 then assert(word(s,4)==2 and word(s,28)==${residentAddress} and word(s,16)==0xc4467b5 and word(s,56)==0x200a3938) end
end
local function arm_registrar()arms=arms+1 end
local function yield_step()end
local function read(p,n)local t={}for o=0,92,4 do t[#t+1]=string.pack('<I4',o==4 and 3 or (o==28 or o==64) and 0x200a7000 or 0)end;return table.concat(t)end
local function load_chaos()error('already installed: must not load new image')end
local install={set=function()end};local caption={set=function()end};local compatibility={set=function()end}
`),ptrCode,installFn,Buffer.from('\ninstall_app();assert(MODULE_BIN~=nil and CHAOS_BIN==nil and CHAOS_RELOCS==nil and arms==1 and copy_calls==2 and armed)')]));
lua.lua_settop(L,0);
}
console.log('PASS already-resident install route in SRAM/PSRAM: duplicate detection skips image read, expansion, relocation and reinitialization');
const retryCode=source.subarray(source.indexOf(Buffer.from('local function retry_registrar()')),source.indexOf(Buffer.from('local root=lvgl.Object(nil,')));
for(const recover of [false,true]){
 const registrationEnv=Buffer.from(`
local BLOCK,BRIDGE=0x3d800000,0x3d900000
local armed,block_ready=false,true;local arms,readies,resumes,writes=0,0,0,0
local function words(t,n)local out={}for i=0,n-1 do out[#out+1]=string.pack('<I4',t[i] or 0)end;return table.concat(out)end
local r={[0]=0x52474554,[7]=0x200a7000};local b={[0]=0x544d425a}
local function word(s,o)return string.unpack('<I4',s,o+1)end
local function read(p,n)if p==BLOCK+0xf0 then return words(r,24)end;assert(p==BRIDGE and n==28);return words(b,7)end
local function heap(p,n)return p>=0x3c000020 and p+n<0x3efffff8 end
local function write32(p,v)assert(p==BLOCK+0xf0+0x4c and v==0);writes=writes+1;r[19]=0 end
local REG_TIMER={ready=function()readies=readies+1 end,resume=function()
 resumes=resumes+1
 ${recover?'r[1]=3;r[12]=1;r[16]=0x200a8000;b[5]=0x200a9000;b[6]=2':''}
end}
local lvgl={OPA=function(n)return n end}
local install={set=function()end};local caption={set=function(self,v)self.text=v.text end};local compatibility={set=function()end}
local function system_version()return '3.1.190'end;local function phase()end;local function probe_batch()end
local function load_module()end;local function load_chaos()end;local function ensure_chaos_dir()end;local function write_icon()end
local OFF_INSTALL_HEALTH=3;local OFF_PREFLIGHT=3;local io={open=function()return nil end}
local health_calls=0
local function native(f)if f==3 then health_calls=health_calls+1;return ${recover?'health_calls<=6 and 0 or 1':'63'} end;return 0 end;local function fn(n)return n end;local function mark()end
local function arm_registrar()arms=arms+1 end
local function yield_step()coroutine.yield()end
`);
 const registrationChecks=Buffer.from(`
local co=coroutine.create(install_app);local ok,err=true,nil;local steps=0
repeat ok,err=coroutine.resume(co);steps=steps+1 until not ok or coroutine.status(co)=='dead' or steps>2000
assert(steps<=2000 and arms==1 and readies==1 and resumes==1 and writes==0,'bootstrap must be nudged once without reallocating')
${recover?"assert(ok and caption.text=='安装成功' and health_calls>=7)":"assert(not ok and err:find('S0 B0') and err:find('T0 A0 N0 C0'));assert(not err:find('%.lua:'));assert(caption.text~='安装成功')"}
-- Exhausted icon retries may be restarted only for a registered app waiting
-- for its icon. A live native timer must not be duplicated or re-armed.
r[1]=2;r[16]=0;r[19]=80;b[5]=0x3d600000;b[6]=2
retry_registrar();assert(writes==1 and r[19]==0 and readies==1 and resumes==1)
retry_registrar();assert(writes==1)
r[1]=3;r[16]=0;r[19]=80;retry_registrar();assert(writes==2 and r[19]==0)
 r[16]=0x200a7000;r[19]=80;retry_registrar();assert(writes==2)
local text=registration_failure(words(r,24));assert(text:find('S3') and text:find('A80 N1 C2'))
r[0]=0;local good=pcall(retry_registrar);assert(not good and writes==2)
`);
 run(Buffer.concat([registrationEnv,ptrCode,retryCode,installFn,registrationChecks]));lua.lua_settop(L,0);
}
console.log('PASS actual installer registration: one stalled-bootstrap wakeup, bounded timeout with visible state, no false success, exhausted icon retry reset, no duplicate native timer, corrupt context rejection');
const heapCode=source.subarray(source.indexOf(Buffer.from('local function heap(')),source.indexOf(Buffer.from('local function keep(')));
run(Buffer.concat([heapCode,Buffer.from(`
assert(runtime_ptr(0x20000000,4) and runtime_ptr(0x200ffffc,4))
assert(runtime_ptr(0x3d700000,32) and not heap(0x200a8000,32))
assert(not runtime_ptr(0x200ffffc,8) and not runtime_ptr(0x20000001,4))
assert(not runtime_ptr(0x1fffffff,4) and not runtime_ptr(0x20100000,4))
assert(not runtime_ptr(0,4) and not runtime_ptr(27,4))
`)]));lua.lua_settop(L,0);
console.log('PASS registry/desktop/timer pointer validation: SRAM and PSRAM accepted, allocation ownership unchanged, invalid alignment/bounds/status codes rejected');
