// Actual shipped installer controls: side effects, work gate and two-tap reset.
const fs=require('fs'),path=require('path');
const {lua,lauxlib,lualib,to_luastring}=require(process.env.FENGARI_PATH);
const source=fs.readFileSync(path.join(__dirname,'../n67/generated/main.lua'));
const start=source.indexOf(Buffer.from('local function preference('));
const end=source.indexOf(Buffer.from('keep(root);keep(scheduler)'),start);
if(start<0||end<start)throw Error('missing installer controls');
const L=lauxlib.luaL_newstate();lualib.luaL_openlibs(L);
const env=Buffer.from(`
local files={['/data/chaos/auto-install']='1',['/data/chaos/launcher.cfg']=string.char(1),
 ['/data/chaos/font/st1.ttf']='FONT',['/data/chaos/icons/01/settings.bin']='ICON',
 ['/data/chaos/n67-app-policy.bin']='APP POLICY',['/data/chaos/n67-beautify-a.bin']='PREFERENCE'}
local failure=nil;local commands={};local timers={};local buttons={};local created={}
local function object(props)
 local o={props=props or {}};function o:set(p)for k,v in pairs(p)do self.props[k]=v end end
 function o:onevent(e,cb)self.tap=cb end;return o
end
local function button(parent,text,y,kind)
 local o,lb=object(),object({text=text});buttons[text]=o;created[#created+1]={o,lb};return o,lb
end
local lvgl={ALIGN={CENTER=9},EVENT={SHORT_CLICKED=1},Timer=function(p)local t={step=p.cb};timers[#timers+1]=t;return t end}
local io={open=function(p,mode)
 if p==failure then return nil end
 if mode=='rb' then if files[p]==nil then return nil end;return {read=function()return files[p]end,close=function()return true end}end
 files[p]='';return {write=function(_,s)files[p]=s;return true end,close=function()return true end}
end}
local reboot_result=true
local os={execute=function(cmd)commands[#commands+1]=cmd;return reboot_result end,remove=function(p)files[p]=nil;return true end}
local AUTO_PATH='/data/chaos/auto-install';local automatic=true;local captions=0
local function auto_caption()captions=captions+1 end
local function keep()end;local function ensure_chaos_dir()end
local main_view,settings_view={},{};local settings_back=object();local compatibility=object()
local work=nil;local armed=false
`);
const checks=Buffer.from(`
assert(#commands==0 and #timers==0,'side effect on watchface entry')
local function preference_button(prefix)for _,v in ipairs(created)do if v[2].props.text:find(prefix,1,true)==1 then return v[1],v[2]end end;error(prefix)end
local pref,lb=preference_button('应用列表显示')
pref.tap();assert(files['/data/chaos/launcher.cfg']==string.char(0))
assert(lb.props.text=='应用列表显示：关')
failure='/data/chaos/launcher.cfg';pref.tap();assert(lb.props.text=='应用列表显示：关')
assert(compatibility.props.text=='入口设置保存失败');failure=nil
armed=true;pref.tap();assert(files['/data/chaos/launcher.cfg']==string.char(1),'installed launcher preference must remain editable');armed=false
work={};buttons['重启'].tap();buttons['重置设置'].tap();buttons['重置设置'].tap()
assert(#commands==0 and #timers==0 and files[AUTO_PATH]=='1','work gate failed');work=nil
buttons['重启'].tap();assert(#commands==0 and #timers==1,'reboot happened in click callback')
timers[1].step();assert(commands[1]=='reboot')
reboot_result=false;buttons['重启'].tap();timers[2].step();assert(compatibility.props.text=='重启请求失败，请手动重启')
buttons['重置设置'].tap();assert(files[AUTO_PATH]=='1','first reset tap deleted settings')
buttons['重置设置'].tap();assert(files[AUTO_PATH]==nil and files['/data/chaos/launcher.cfg']==nil)
assert(files['/data/chaos/font/st1.ttf']=='FONT' and files['/data/chaos/icons/01/settings.bin']=='ICON')
assert(files['/data/chaos/n67-app-policy.bin']=='APP POLICY','reset discarded hidden-app policy')
assert(not automatic and captions==1 and compatibility.props.text=='设置已重置，请重启')
`);
const code=Buffer.concat([env,source.subarray(start,end),checks]);
let rc=lauxlib.luaL_loadbuffer(L,code,code.length,to_luastring('actual-installer-controls'));
if(!rc)rc=lua.lua_pcall(L,0,0,0);
if(rc)throw Error(lua.lua_tojsstring(L,-1));
console.log('PASS shipped Lua controls: entry switches, saved values, commit failure, running gate, deferred reboot and returned failure, two-tap reset, imported assets and app policy preserved');
