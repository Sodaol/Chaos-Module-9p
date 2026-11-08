const fs=require('fs'),path=require('path');const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(process.env.FENGARI_PATH);
const source=fs.readFileSync(path.join(__dirname,'../n67/generated/main.lua'));const a=source.indexOf(Buffer.from("local DATA_VERSION='")),z=source.indexOf(Buffer.from('\nlocal function arm_registrar()',a));if(a<0||z<0)throw Error('missing shipped data updater');
const env=`local files={['/data/chaos/font/st1.ttf']='USERFONT',['/data/chaos/icons/01/alarm.bin']='USERICON',['/data/chaos/launcher.cfg']='0',['/data/chaos/version.txt']='old\\n'}
local writes=0;local fail=nil;local renamed={};local reads={}
local function mark()end
local io={open=function(p,m)
 if m=='rb' then reads[#reads+1]=p;if files[p]==nil then return nil end;return {read=function()return files[p]end,close=function()return true end}end
 if p==fail then return nil end
 writes=writes+1;files[p]='';return {write=function(_,b)files[p]=b;return true end,close=function()return true end}
end}
local os={rename=function(a,b)if fail==b then return nil end;assert(files[a]);files[b]=files[a];files[a]=nil;renamed[#renamed+1]=b;return true end,remove=function(p)files[p]=nil;return true end}
`;
const tests=`
update_program_data();assert(files[DATA_MARKER]==DATA_VERSION..'\\n');assert(renamed[#renamed]==DATA_MARKER);assert(writes==4)
assert(files['/data/chaos/font/st1.ttf']=='USERFONT' and files['/data/chaos/icons/01/alarm.bin']=='USERICON' and files['/data/chaos/launcher.cfg']=='0')
local n=writes;reads={};update_program_data();assert(writes==n and #reads==1 and reads[1]==DATA_MARKER,'same version must only read marker')
files['/data/chaos/chaos_icon.bin']='BROKEN';reads={};update_program_data();assert(writes==n and #reads==1 and files['/data/chaos/chaos_icon.bin']=='BROKEN')
files[DATA_MARKER]='old\\n';files['/data/chaos/chaos_settings_icon.bin']='OLD';fail='/data/chaos/chaos_settings_icon.bin';local ok=pcall(update_program_data);assert(not ok and files[DATA_MARKER]=='old\\n');assert(not files[fail..'.update']);fail=nil;update_program_data();assert(files[DATA_MARKER]==DATA_VERSION..'\\n')
files['/data/chaos/spotify_cover.bin']=nil;reads={};update_program_data();assert(files['/data/chaos/spotify_cover.bin']==nil and #reads==1);\nfail=DATA_MARKER;files[DATA_MARKER]='old\\n';ok=pcall(update_program_data);assert(not ok and files[DATA_MARKER]=='old\\n');assert(not files[DATA_MARKER..'.update'])
`;
const b=Buffer.concat([Buffer.from(env),source.subarray(a,z),Buffer.from(tests)]);const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(b),b.length,to_luastring('data version test'));if(!e)e=lua.lua_pcall(L,0,0,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));console.log('PASS shipped version updater: legacy upgrade, same-version no writes, matching marker skips all asset reads even if damaged/missing, marker-last commit, commit failure cleanup/retry, fonts/icons/settings preserved');
