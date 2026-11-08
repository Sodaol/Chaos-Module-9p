// Run the installed UI code with explicit LVGL/filesystem/command mocks.
const fs=require('fs'),path=require('path');
const {lua,lauxlib,lualib,to_luastring,to_jsstring}=require(path.resolve(__dirname,'../node_modules/fengari'));
const root=path.resolve(__dirname,'..'),src=fs.readFileSync(root+'/n67/generated/main.lua');
const take=(a,b)=>src.subarray(src.indexOf(Buffer.from(a)),src.indexOf(Buffer.from(b),src.indexOf(Buffer.from(a))));
const ui=take('local root=lvgl.Object(nil,','local function system_version()');
const ensure=take('local function ensure_chaos_dir()','local function write_icon()');
const auto=take('local AUTO_PATH=','keep(root);keep(scheduler)');
const click=take('install:onevent(lvgl.EVENT.SHORT_CLICKED','local scheduler=');
const env=Buffer.from(`
local saved=nil;local commands={};local objects={};local timers={};local work=nil;local armed=false;local runs=0
local lvgl={FLAG={SCROLLABLE=1,PRESS_LOCK=2,CLICKABLE=4,EVENT_BUBBLE=8,GESTURE_BUBBLE=16,HIDDEN=32},ALIGN={TOP_LEFT=1,CENTER=2},EVENT={SHORT_CLICKED=1},OPA=function(n)return n end,Font=function(n,s)return s end}
local function object(parent,props)
 local o={parent=parent,props=props,flags=0};objects[#objects+1]=o
 function o:clear_flag(f)self.flags=self.flags & ~f end
 function o:add_flag(f)self.flags=self.flags | f end
 function o:set(p)for k,v in pairs(p)do self.props[k]=v end end
 function o:onevent(e,c)self.tap=c end
 return o
end
lvgl.Object=object;lvgl.Label=object
lvgl.Timer=function(props)local t={props=props};function t:pause()self.paused=true end;function t:step()if not self.paused then props.cb(self)end end;timers[#timers+1]=t;return t end
local io={open=function(p,m)
 if m=='rb' then if saved==nil then return nil end;return {read=function()return saved end,close=function()return true end} end
 return {write=function(_,s)if p:find('auto%-install')then saved=s end;return true end,close=function()return true end}
end}
local os={remove=function()end,execute=function(cmd)commands[#commands+1]=cmd;return nil,'exit',1 end}
local function keep()end;local function install_app()runs=runs+1 end
`);
const checks=Buffer.from(`
assert(root.props.bg_color==0x1c1c1e and install.props.bg_color==0x2563eb)
assert(caption.props.text=='运行' and title_font==32 and body==24)
assert(main_view.props.align.y_ofs==0 and settings_view.props.align.y_ofs==3000)
settings_open.tap();assert(main_view.props.align.y_ofs==3000 and settings_view.props.align.y_ofs==0)
assert(auto_button.parent==settings_view and auto_button.flags & lvgl.FLAG.HIDDEN==0)
auto_button.tap();assert(saved=='1' and automatic)
settings_back.tap();assert(main_view.props.align.y_ofs==0)
assert(reset==nil and restart==nil and #commands==0)
install.tap();assert(work);assert(coroutine.resume(work));assert(runs==1)
`);
const code=Buffer.concat([env,ui,ensure,auto,click,checks]);
const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);
let e=lauxlib.luaL_loadbuffer(L,new Uint8Array(code),code.length,to_luastring('installer UI check'));
if(!e)e=lua.lua_pcall(L,0,lua.LUA_MULTRET,0);
if(e)throw Error(to_jsstring(lua.lua_tostring(L,-1)));
console.log('PASS installed Lua UI: original palette/geometry, view navigation, saved auto switch, no reset/reboot controls, manual run.');
