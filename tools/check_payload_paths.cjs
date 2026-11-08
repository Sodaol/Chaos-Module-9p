const fs=require('fs'),path=require('path');const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(process.env.FENGARI_PATH);
const g=path.join(__dirname,'../n67/generated');const pack=fs.readFileSync(g+'/resource.bin'),source=fs.readFileSync(g+'/main.lua');const leaves=[];
for(let i=0;i<pack.readUInt32LE(0xd8);i++){const p=pack.readUInt32LE(pack.readUInt32LE(0xdc)+i*16+8),z=pack[p+3],n=pack.readUInt16LE(p);const name=pack.subarray(p+20,p+20+z).toString();if(name.endsWith('.dat'))leaves.push([name.split('/').pop(),pack.subarray(p+20+z,p+20+z+n)]);}
const filecode='local files={}\n'+leaves.map(([n,b])=>"files['/alt/"+n+"']='"+[...b].map(x=>'\\'+x.toString().padStart(3,'0')).join('')+"'\n").join('');
const a=source.indexOf(Buffer.from('local function read_payload()')),z=source.indexOf(Buffer.from('\nlocal OFF_MAGIC'),a);const prefix=source.subarray(a,z);
const expected=fs.readFileSync(g+'/chaos.bin');
for(const setup of ["local SCRIPT_PATH='/alt'", "local SCRIPT_PATH='/alt/'", "local SCRIPT_PATH='/alt/main.lua'", "local debug={getinfo=function()return {source='@/alt/main.lua'}end}", "local SCRIPT_PATH='/missing';for k,v in pairs(files)do files[k:gsub('/alt/','/data/app/watchface/market/990000000029/_lua/_Lua/')]=v end"]){
 const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);const b=Buffer.concat([Buffer.from('local MODULE_SIZE='+fs.readFileSync(g+'/bridge.bin').length+'\n'+filecode+setup+"\nlocal io={open=function(p,m)if files[p]then return {read=function()return files[p]end,close=function()return true end}end end}\n"),prefix,Buffer.from('\nreturn read_payload()')]);
 let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(b),b.length,to_luastring('payload path test'));if(!e)e=lua.lua_pcall(L,0,1,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));if(!Buffer.from(lua.lua_tolstring(L,-1)).equals(expected))throw Error('decoded wrong image');
}
console.log('PASS packed payload lookup: SCRIPT_PATH directory with/without slash, main.lua path, debug source path, fixed-path fallback; every decoded byte matches native image');
for(const change of ["files={}","files['/alt/chaos-01.dat']=nil;local backup={};for k,v in pairs(files)do backup[k:gsub('/alt/','/data/app/watchface/market/990000000029/_lua/_Lua/')]=v end;for k,v in pairs(backup)do files[k]=v end"]){
 const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);const b=Buffer.concat([Buffer.from('local MODULE_SIZE='+fs.readFileSync(g+'/bridge.bin').length+'\n'+filecode+change+"\nlocal SCRIPT_PATH='/alt/'\nlocal io={open=function(p,m)if files[p]then return {read=function()return files[p]end,close=function()return true end}end end}\n"),prefix,Buffer.from("\nlocal ok,err=pcall(read_payload);assert(not ok and err:find('安装数据缺失',1,true))")]);let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(b),b.length,to_luastring('missing payload'));if(!e)e=lua.lua_pcall(L,0,0,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));
}
console.log('PASS missing/incomplete payload rejected with named error');
