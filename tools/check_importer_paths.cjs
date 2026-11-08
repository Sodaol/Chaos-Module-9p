const fs=require('fs'),path=require('path');const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(process.env.FENGARI_PATH);
const src=fs.readFileSync(path.join(__dirname,'../n67/importer.lua.in'),'utf8');const a=src.indexOf('local function resolve_sources()'),z=src.indexOf('\nlocal DIR=',a);const fn=src.slice(a,z);
const body=`local M={entries={{src='alarm.dat'},{src='font-00.dat'}}};local BASE='/fixed/';local SCRIPT_PATH='/actual/main.lua';local closed=0
local files={['/actual/alarm.dat']=true,['/actual/font-00.dat']=true}
local io={open=function(p,m)assert(m=='rb');if files[p] then return {close=function()closed=closed+1 end}end end}
`+fn+`
resolve_sources();assert(BASE=='/actual/' and closed==2)
BASE='/fixed/';SCRIPT_PATH=nil;files={['/fixed/alarm.dat']=true,['/fixed/font-00.dat']=true};resolve_sources();assert(BASE=='/fixed/')
BASE='/fixed/';SCRIPT_PATH='/actual';files={['/actual/alarm.dat']=true,['/fixed/font-00.dat']=true};local ok,err=pcall(resolve_sources);assert(not ok and err:find('素材缺失',1,true),'must not combine different directories')
BASE='/fixed/';SCRIPT_PATH='/actual';files={};ok,err=pcall(resolve_sources);assert(not ok and err:find('alarm.dat',1,true))
`;
const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);let e=lauxlib.luaL_loadstring(L,to_luastring(body));if(!e)e=lua.lua_pcall(L,0,0,0);if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));
if(src.indexOf('resolve_sources() --')>src.indexOf('  mkdir(DIR)'))throw Error('must validate before writes');console.log('PASS importer source resolution: actual/fallback directory, all source handles closed, no mixed directories, missing file named, source check precedes writes');
