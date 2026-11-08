// Exercise the shipped install completion loop, including hidden preference.
const fs=require('fs'),path=require('path');
const {lua,lauxlib,lualib,to_luastring}=require(process.env.FENGARI_PATH);
const s=fs.readFileSync(path.join(__dirname,'../n67/generated/main.lua'));
const start=s.indexOf(Buffer.from('local function install_app()'));
const end=s.indexOf(Buffer.from('install:onevent(',start));
if(start<0||end<start)throw Error('installation loop missing');
for(const [health,pref,expected] of [[63,1,'success'],[31,1,'timeout'],[23,1,'incomplete'],[15,1,'incomplete'],[127,1,'timeout'],[31,0,'success'],[31,null,'timeout']]){
 const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);
 const env=Buffer.from(`
local health=${health};local pref=${pref===null?'nil':pref}
local lvgl={OPA=function(x)return x end};local install={set=function()end}
local caption,compatibility={},{};function caption:set(p)self.text=p.text end;function compatibility:set(p)self.text=p.text end
local function system_version()return '3.1.190'end
local function phase()end;local armed=true;local function retry_registrar()end
local OFF_INSTALL_HEALTH=1;local APP_ID=0xe7d4;local BLOCK=0x3d800000
local function fn(x)return x end;local function native(...)return health end
local function read()return string.pack('<I4I4',0,3)..string.rep('\\0',88)end
local function word(s,o)return string.unpack('<I4',s,o+1)end
local function mark()end;local function yield_step()coroutine.yield()end
local function registration_failure()return 'REG'end
local io={open=function()if pref==nil then return nil end;return {read=function()return string.char(pref)end,close=function()end}end}
`);
 const checks=Buffer.from(`
local co=coroutine.create(install_app);local ok,err=true,nil
for i=1,2000 do ok,err=coroutine.resume(co);if not ok or coroutine.status(co)=='dead' then break end end
assert(coroutine.status(co)=='dead')
${expected==='success'?"assert(ok and caption.text=='安装成功',tostring(err))":expected==='incomplete'?"assert(not ok and tostring(err):find('入口不完整',1,true),tostring(err))":"assert(not ok and tostring(err):find('入口未完成',1,true),tostring(err))"}
`);
 const code=Buffer.concat([env,s.subarray(start,end),checks]);
 let rc=lauxlib.luaL_loadbuffer(L,code,code.length,to_luastring('installation-health-completion'));
 if(!rc)rc=lua.lua_pcall(L,0,0,0);if(rc)throw Error(lua.lua_tojsstring(L,-1));
 lua.lua_close(L);
}
// Run the shipped resident recovery branch with its data directory absent.
{
 const a=s.indexOf(Buffer.from("phase('修复已驻留应用图标')"));
 const b=s.indexOf(Buffer.from('\n    else',a));
 if(a<0||b<a)throw Error('resident recovery missing');
 const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);
 const pre=Buffer.from(`
local directory,icon,armed=false,false,false
local BLOCK,found,APP_ID,RES=0x3d800000,0x20010000,0xe7d4,{size=1024}
local function phase()end
local function ensure_chaos_dir()directory=true end
local function write_icon()assert(directory);icon=true end
local function copy_fast()end
local function arm_registrar()assert(icon,'resident launcher repair before restoring deleted icon')end
`);
 const code=Buffer.concat([pre,s.subarray(a,b),Buffer.from('\nassert(directory and icon and armed)')]);
 let rc=lauxlib.luaL_loadbuffer(L,code,code.length,to_luastring('deleted-data-resident-recovery'));
 if(!rc)rc=lua.lua_pcall(L,0,0,0);if(rc)throw Error(lua.lua_tojsstring(L,-1));
 lua.lua_close(L);
}
console.log('PASS shipped install completion and deleted-data resident icon restoration; ID alone never reports success');
