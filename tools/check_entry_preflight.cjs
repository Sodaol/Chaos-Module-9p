const fs=require('fs'),path=require('path');const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(process.env.FENGARI_PATH);
const source=fs.readFileSync(path.join(__dirname,'../n67/generated/main.lua'),'utf8');const a=source.indexOf('local function entry_preflight()'),z=source.indexOf('\nlocal function install_app()',a);if(a<0||z<0)throw Error('missing preflight');
const code=`local mask=0;local queries=0;local OFF_PREFLIGHT=7
local function phase()end;local function mark()end;local function fn(n)return n end
local function native(n)assert(n==7);queries=queries+1;return mask end
`+source.slice(a,z)+`
entry_preflight();assert(queries==1)
for _,v in ipairs({{1,'E7D4'},{2,'E7C3'},{3,'E7C3'}})do mask=v[1];local ok,err=pcall(entry_preflight);assert(not ok and err:find(v[2],1,true))end
`;
const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);let e=lauxlib.luaL_loadstring(L,to_luastring(code));if(!e)e=lua.lua_pcall(L,0,0,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));console.log('PASS shipped ID-only preflight Lua: absent allowed, current and old IDs stopped, old-version priority');
