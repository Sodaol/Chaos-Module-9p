from pathlib import Path
import sys,json,struct,hashlib,os
from PIL import Image,ImageDraw,ImageChops
R=Path(__file__).resolve().parents[1];W=R/'build-support';B=R/'n67';G=B/'generated'
from page_layout import PAGE_COUNT
sys.path.insert(0,str(W/'work'))
from embed_module import module_expression as binary_expression,compress,LZ_DECODER
def lua(s):return "'"+s.replace('\\','\\\\').replace("'","\\'").replace('\n','\\n')+"'"
def spotify_cover_raw():
 im=Image.new('RGBA',(100,100),(18,18,18,255));d=ImageDraw.Draw(im)
 d.ellipse((8,8,92,92),fill=(29,185,84,255))
 d.arc((26,26,74,74),210,330,fill=(18,18,18,255),width=7)
 d.arc((30,36,70,76),210,330,fill=(18,18,18,255),width=6)
 d.arc((34,46,66,78),210,330,fill=(18,18,18,255),width=5)
 raw=struct.pack('<I',5+100*1024+100*2097152)+im.tobytes('raw','BGRA')
 (B/'assets/spotify_cover.bin').write_bytes(raw)
 return raw
def main():
 B.joinpath('assets').mkdir(exist_ok=True);G.mkdir(exist_ok=True)
 c=json.loads((G/'chaos.json').read_text('utf-8'));j=json.loads((G/'bridge.json').read_text('utf-8'))
 aliases={'MAGIC':'bt_magic','COPY':'bt_copy_bytes','SYNC':'bt_sync_code','TIMER_BOOTSTRAP':'bt_timer_bootstrap','REGTICK':'bt_reg_tick','INSTALL_CHECK':'bt_install_check','INSTALL_HEALTH':'bt_install_health'}
 aliases['PREFLIGHT']='bt_entry_preflight'
 offsets='\n'.join(f'local OFF_{k}=0x{j["functions"][v]["offset"]:x}' for k,v in aliases.items())
 bootstrap_size=max(j['functions'][v]['offset']+j['functions'][v]['size'] for v in ['bt_magic','bt_copy_bytes','bt_sync_code'])
 assert bootstrap_size<=512,'bootstrap prefix unexpectedly large'
 offsets+='\nlocal BOOTSTRAP_SIZE='+str(bootstrap_size)
 vals={0x08:'REG_IDENT',0x0c:'REG_ICON',0x10:'APP_ID|0x00040000',0x1c:'(REG_STUB-0x20000000)|1',
  0xe8:'0x47704800',0xec:'REG_BLK+RES.title',0xf0:'0x52474554',0xf8:'2',0xfc:'0x0C4497CD',
  0x100:'0x0C4467B5',0x104:'0x0C448749',0x108:'0x0C2A47A1',0x10c:'REG_APP',0x110:'REG_PAGE',
  0x114:'REG_BLK+0x800',0x118:'APP_ID',0x11c:'PAGE_ID',0x128:'0x200A3938',0x12c:'0x200A1DE8',0x140:'REG_BLK+RES.cfg',0x144:'REG_APP|1'}
 resident='local v={}\n'+'\n'.join(f'v[0x{k:x}]={v}' for k,v in vals.items())
 resident+="\nlocal strings={[RES.ident]='com.chaos.manager',[RES.icon]='/data/chaos/chaos_icon.bin',[RES.title]='Chaos'}"
 # Use upstream Chaos artwork, converted to the N67 LVGL 8 BGRA image format.
 source=B/'assets/icon-source.png'
 if not source.exists():source.write_bytes((B/'assets/icon.png').read_bytes())
 im=Image.open(source).convert('RGBA').resize((100,100),Image.Resampling.LANCZOS)
 # Clip the native LVGL8 image to a circle with transparent outer corners.
 mask=Image.new('L',(400,400),0);ImageDraw.Draw(mask).ellipse((8,8,391,391),fill=255)
 mask=mask.resize((100,100),Image.Resampling.LANCZOS)
 im.putalpha(ImageChops.multiply(im.getchannel('A'),mask))
 raw=struct.pack('<I',5+100*1024+100*2097152)+im.tobytes('raw','BGRA')
 im.save(B/'assets/icon.png');(B/'assets/icon.bin').write_bytes(raw)
 settings=Image.open(source).convert('RGBA').resize((64,64),Image.Resampling.LANCZOS)
 settings.putalpha(ImageChops.multiply(settings.getchannel('A'),mask.resize((64,64),Image.Resampling.LANCZOS)))
 settings_raw=struct.pack('<I',5+(64<<10)+(64<<21))+settings.tobytes('raw','BGRA')
 (B/'assets/settings-icon.bin').write_bytes(settings_raw)
 settings_write="local f=assert(io.open('/data/chaos/chaos_settings_icon.bin','wb'),'设置图标无法写入');f:write(".encode('utf8')+binary_expression(settings_raw)+b");assert(f:close())"
 icon="local f=assert(io.open('/data/chaos/chaos_icon.bin','wb'),'图标无法写入');f:write(".encode('utf-8')+binary_expression(raw)+b");f:close()"

 # Native N67 UI now reads system assets directly. The reference installer
 # writes the app icon; unused P67 masks/back assets are no longer prerequisites.
 cover_raw=spotify_cover_raw()
 pet_code="local f=assert(io.open('/data/chaos/spotify_cover.bin','wb'),'封面图片无法写入');f:write(".encode('utf-8')+binary_expression(cover_raw)+b");f:close()"
 src=(W/'installers/installer.lua.in').read_text('utf-8')
 # Keep the reference v2.1 loader and Lua-to-native timer handoff verbatim.
 for name,end in [('load_module','local function resident('),('arm_registrar','-- Reuse the bootstrap')]:
  a=src.index('local function '+name+'(');z=src.index(end,a)
  src=src[:a]+(B/'injection-v21'/(name+'.lua.in')).read_text('utf-8')+'\n'+src[z:]

 ui_start=src.index('local root=lvgl.Object(nil,')
 ui_end=src.index('local function system_version()',ui_start)
 src=src[:ui_start]+(B/'installer-ui.lua.in').read_text('utf-8')+'\n'+src[ui_end:]
 for k,v in {'SIZE':str(j['size']),'OFFSETS':offsets,'RES_LAYOUT':'{size=0x2000,status=0x200,ident=0x280,icon=0x2a0,title=0x2e0,cfg=0x300}',
  'APP_ID':'0xE7D4','PAGE_ID':'0xE7D40000','TITLE':lua('Chaos'),'RELEASE':lua('2.2-alpha.57-honeycomb4'),'LOG':lua('/data/chaos-n67.log'),
  'MARK':lua('/data/chaos-n67.mark'),'DUMP':lua('/data/chaos-n67-read.txt'),'RESIDENT':resident,'ICON':'@@CHAOS_ICON@@','PET':'@@PET_ASSET@@'}.items():src=src.replace('@@'+k+'@@',v)
 src=src.replace("    if stage==3 and runtime_ptr(word(bytes,0x40),32) then", """    local ids=native(fn(OFF_PREFLIGHT))
    mark(string.format('registered IDs=%x stage=%d',ids,stage))
    if stage>=2 and stage<20 and (ids & 1)~=0 then""")
 if os.environ.get('CHAOS_SETTINGS_EGG')=='1':
  src=src.replace('local show=true','local show=false').replace("if pref then show=pref:read(1)~=string.char(0);pref:close() end","if pref then pref:close() end")
  src=src.replace('Chaos 注册完成\\n返回表盘后上滑打开 Chaos','已安装彩蛋版\\n系统关于中连点版本文字 5 次')
  src=src.replace('正在注册 ', '正在注册彩蛋 ').replace('请返回表盘后上滑查看应用','不会添加桌面图示')
 src=src.replace('error(registration_failure(last),0)',"error('未查到有效应用 ID E7D4 / '..registration_failure(last),0)")
 # Watchface entry must only create the UI. Reading/checksumming the .dat
 # leaves and expanding the 270+ KiB image here blocks the system UI even
 # when the user never asks to install (or the module is already resident).
 lazy="""local MODULE_BIN,CHAOS_BIN,CHAOS_RELOCS=nil,nil,nil
local CHAOS_SIZE = @@IMAGE_SIZE@@
local CHAOS_BLOCK,CHAOS_EXEC,chaos_ready = 0,0,false
local function prepare_module()
  if MODULE_BIN then return end
  MODULE_BIN = @@BRIDGE_PAYLOAD@@
  assert(#MODULE_BIN==MODULE_SIZE,'payload size')
end
local function prepare_chaos()
  if CHAOS_BIN then return end
  local image = @@CHAOS_PAYLOAD@@
  local relocs = @@CHAOS_RELOCS@@
  CHAOS_BIN,CHAOS_RELOCS=image,relocs
end""".replace('@@IMAGE_SIZE@@',str(c['size']))
 src=src.replace("local MODULE_BIN = '@@MODULE_PAYLOAD@@'",lazy)
 src=src.replace("  if module_ready then return end\n\n  assert(#MODULE_BIN==MODULE_SIZE,'payload size')",
                 "  if module_ready then return end\n  prepare_module()")
 src=src.replace("assert(#MODULE_BIN==MODULE_SIZE,'invalid installer payload')",'-- Payload validation is deferred until installation is requested.')
 src=src.replace('(EXEC~=0 and f>=EXEC and f<EXEC+MODULE_SIZE)','((EXEC~=0 and f>=EXEC and f<EXEC+MODULE_SIZE) or (CHAOS_EXEC~=0 and f>=CHAOS_EXEC and f<CHAOS_EXEC+CHAOS_SIZE))')
 injection='''
local function load_chaos()
  if chaos_ready then return end
  mark('装载 Chaos / 重定位')
  prepare_chaos()
  if CHAOS_BLOCK==0 then CHAOS_BLOCK=native(MALLOC,CHAOS_SIZE);own(CHAOS_BLOCK,CHAOS_SIZE) end
  CHAOS_EXEC=CHAOS_BLOCK-0x20000000
  local chunks,at={},1
  for i=1,#CHAOS_RELOCS,4 do
    local off=string.unpack('<I4',CHAOS_RELOCS,i)
    assert(off%4==0 and off+4<=CHAOS_SIZE,'relocation bounds')
    local val=word(CHAOS_BIN,off)
    assert(val>=0x1d100000 and val<=0x1d100000+CHAOS_SIZE+1,'relocation value')
    chunks[#chunks+1]=CHAOS_BIN:sub(at,off)
    chunks[#chunks+1]=string.pack('<I4',val+CHAOS_EXEC-0x1d100000)
    at=off+5
    if (i-1)%512==0 and coroutine.isyieldable() then coroutine.yield() end
  end
  chunks[#chunks+1]=CHAOS_BIN:sub(at)
  local blob=table.concat(chunks);assert(#blob==CHAOS_SIZE)
  copy_fast(CHAOS_BLOCK,blob)
  sync_fast(CHAOS_BLOCK,CHAOS_SIZE)
  assert(native((CHAOS_EXEC+@@CHAOS_ENTRY@@)|1,BLOCK,lvgl.FLAG.GESTURE_BUBBLE,lvgl.FLAG.EVENT_BUBBLE,lvgl.FLAG.PRESS_LOCK)==0x4e363743,'Chaos init ABI')
  chaos_ready=true
end
local function ensure_chaos_dir()
  local path='/data/chaos/.installer-probe'
  local f=io.open(path,'ab')
  if not f then
    local ok,kind,code=os.execute('mkdir /data/chaos')
    f=io.open(path,'ab')
    assert(f,'无法创建 /data/chaos：'..tostring(ok)..'/'..tostring(kind)..'/'..tostring(code))
  end
  assert(f:close(),'目录检查失败');os.remove(path)
end
'''.replace('@@CHAOS_ENTRY@@',str(c['entry']))
 src=src.replace('local function write_icon()',injection+'\nlocal function write_icon()')
 src=src.replace("phase('准备原生应用');write_icon()","phase('准备原生应用');ensure_chaos_dir();write_icon()")
 # A resident registry entry can outlive deletion of /data/chaos. Restore
 # the icon before asking the native launcher to load that entry again.
 src=src.replace("phase('修复已驻留应用图标')", "phase('修复已驻留应用图标');ensure_chaos_dir();write_icon()")
 src=src.replace("phase('注册应用图标');arm_registrar();armed=true","load_chaos();phase('注册应用图标');arm_registrar();armed=true")
 # This is a conditional, data-only boot route: the selected installer face
 # is started by the stock watchface service. It cannot run behind another face.
 auto="""
local AUTO_PATH='/data/chaos/auto-install'
local automatic=false
local af=io.open(AUTO_PATH,'rb');if af then automatic=af:read(1)=='1';af:close() end
local auto_button=lvgl.Object(settings_view,{w=SCR_W-32,h=56,bg_color=0x1C1C1E,bg_opa=lvgl.OPA(100),radius=24,
 border_width=2,border_color=0x60646C,pad_all=0,align={type=lvgl.ALIGN.TOP_LEFT,x_ofs=16,y_ofs=SCR_H/2-76-28}})
auto_button:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.PRESS_LOCK)
auto_button:add_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)
local auto_text=lvgl.Label(auto_button,{text='',text_font=body,text_color=0xB3B3B3,
 align={type=lvgl.ALIGN.CENTER,x_ofs=0,y_ofs=0}})
auto_text:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
auto_text:add_flag(lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)
local function auto_caption()
 auto_text:set{text=(automatic and '随安装器载入：开' or '随安装器载入：关')}
end
auto_caption()
auto_button:onevent(lvgl.EVENT.SHORT_CLICKED,function()
 local ok=pcall(function()
  ensure_chaos_dir()
  local f=assert(io.open(AUTO_PATH,'wb'),'无法保存自动安装设置')
  assert(f:write(automatic and '0' or '1'));assert(f:close());automatic=not automatic;auto_caption()
 end)
 if not ok then compatibility:set{text='自动安装设置未保存'} end
end)
local auto_ticks,auto_tries=0,0
local auto_timer=lvgl.Timer{period=1000,repeat_count=-1,cb=function(t)
 auto_ticks=auto_ticks+1
 if not automatic or armed or work or auto_tries>=3 or auto_ticks<3 then return end
 auto_tries=auto_tries+1;auto_ticks=-7
 work=coroutine.create(install_app)
end}
keep(auto_button);keep(auto_text);keep(auto_timer)
"""
 controls=(B/'installer-controls.lua.in').read_text('utf-8')
 if os.environ.get('CHAOS_SETTINGS_EGG')=='1':
  controls=controls.replace("preference('/data/chaos/native-entries.cfg','注入系统设置',-12,true,true)","centered(settings_view,'系统关于：连点版本 5 次',-12,version_font,0xB3B3B3)")
  controls=controls.replace("preference('/data/chaos/launcher.cfg','应用列表显示',52,true,false)","centered(settings_view,'仅保留彩蛋入口',52,version_font,0xB3B3B3)")
 auto+='\n'+controls
 src=src.replace('keep(root);keep(scheduler)',auto+'\nkeep(root);keep(scheduler)')
 # Keep the primary button blue through idle, progress, success and retry.
 import re
 src=re.sub(r'install:set\{bg_color=0x[0-9A-Fa-f]+\}', 'install:set{bg_color=0x2563EB,bg_opa=lvgl.OPA(100),border_color=0x2563EB}', src)
 src=re.sub(r'(caption:set\{text=[^\n}]*text_color=)0x[0-9A-Fa-f]+',r'\g<1>0xF2F2F2',src)
 preflight=(B/'entry-preflight.lua.in').read_text('utf-8-sig')
 src=src.replace('local function install_app()',preflight+'\nlocal function install_app()',1)
 needle="phase('连接注册接口');probe_batch();load_module()"
 assert needle in src,'missing preflight insertion point'
 src=src.replace(needle,needle+'\n    if entry_preflight then entry_preflight() end',1)
 data=src.encode('utf-8')
 if os.environ.get('CHAOS_ENTRY_DIAGNOSTIC')=='1':
  # Read-only failure diagnostics. Never adopt or overwrite an unexpected node.
  a=data.index(b'local function registration_failure(bytes)');z=data.index(b'\nend',a)+4
  diagnostic='''local function registration_failure(bytes)
  local expected=word(bytes,0x1c)
  local actual=native(fn(OFF_INSTALL_CHECK),0x0C4467B5,APP_ID)
  local valid=runtime_ptr(actual,60)
  local id=valid and (word(read(actual+0x10,4),0)&0xffff) or 0
  local page=0
  local cursor=0x200A0204
  local seen={}
  for _=1,256 do
    if not runtime_ptr(cursor,68) or seen[cursor] then break end
    seen[cursor]=true
    local item=read(cursor,68)
    if word(item,0x14)==PAGE_ID then page=cursor;break end
    cursor=word(item,0x40)
  end
  local why=not valid and 'NODE' or id~=APP_ID and 'ID' or actual~=expected and 'MOVED' or 'OK'
  mark(string.format('ENTRY_DIAG expected=%x actual=%x id=%x page=%x stage=%d bc=%d',expected,actual,id,page,word(bytes,4),word(bytes,0x5c)))
  local old_id=runtime_ptr(expected,60) and (word(read(expected+0x10,4),0)&0xffff) or 0
  return string.format('S%d B%d %s\\nR:%x\\nE:%x / %x\\nN:%x / %x\\nP:%x',word(bytes,4),word(bytes,0x5c),why,word(bytes,0x28),expected,old_id,actual,id,page)
end'''
  data=data[:a]+diagnostic.encode('utf8')+data[z:]
  data=data.replace(b'w=280,h=48,text_font=version_font',b'w=280,h=64,text_font=version_font')
  # Retain every diagnostic line on a dedicated screen instead of clipping
  # the registry evidence into the 48 px progress card.
  overlay='''local function show_entry_error(text)
  local pane=view()
  local label=lvgl.Label(pane,{text=text,w=304,h=352,text_font=version_font,text_color=0xFCA5A5,text_align=0,
    align={type=lvgl.ALIGN.TOP_LEFT,x_ofs=16,y_ofs=24}})
  label:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  local back,caption=button(pane,'返回',196,'ghost')
  back:onevent(lvgl.EVENT.SHORT_CLICKED,function()pane:set{align={type=lvgl.ALIGN.TOP_LEFT,x_ofs=3000,y_ofs=0}}end)
  keep(pane);keep(label);keep(back);keep(caption)
end
'''
  data=data.replace(b'local function system_version()',overlay.encode('utf8')+b'local function system_version()',1)
  data=data.replace(b"compatibility:set{text=message,text_color=0xFF909C}",b"compatibility:set{text=message,text_color=0xFF909C};show_entry_error(message)")
  data=data.replace(b"local RELEASE = '2.2-alpha.57-honeycomb4'",b"local RELEASE = '2.2-alpha.57-honeycomb4-entry-diag1'")
 for key,value in [(b'@@BRIDGE_PAYLOAD@@',(G/'bridge.bin').read_bytes()),
  (b'@@CHAOS_RELOCS@@',b''.join(struct.pack('<I',x) for x in c['relocations']))]:data=data.replace(key,binary_expression(value))
 image=(G/'chaos.bin').read_bytes();chunk_size=8192;spec=[]
 for old in G.glob('chaos-*.dat'):old.unlink()
 for i,at in enumerate(range(0,len(image),chunk_size)):
  plain=image[at:at+chunk_size];chunk=compress(plain);name=f'chaos-{i:02d}.dat';(G/name).write_bytes(chunk)
  spec.append('{'+lua(name)+','+str(len(chunk))+','+str(sum(chunk))+','+str(len(plain))+'}')
 reader="""local function read_payload()
  local decode=@@DECODE@@
  local chunks={}
  local bases,seen={},{}
  local function add(path)
    if type(path)~='string' or path:sub(1,1)~='/' then return end
    path=path:gsub('/main%.lua$','/')
    if path:sub(-1)~='/' then path=path..'/' end
    if not seen[path] then seen[path]=true;bases[#bases+1]=path end
  end
  add(SCRIPT_PATH)
  if type(debug)=='table' and type(debug.getinfo)=='function' then
    local ok,info=pcall(debug.getinfo,1,'S')
    if ok and type(info)=='table' and type(info.source)=='string' and info.source:sub(1,1)=='@' then
      local source=info.source:sub(2)
      if source:match('/main%.lua$') then add(source) end
    end
  end
  add('/data/app/watchface/market/990000000029/_lua/_Lua/')
  local selected=nil
  for _,e in ipairs({@@SPEC@@}) do
    local blob=nil
    local reason='安装数据缺失：'..e[1]..'\\n请删除安装器后重新传送完整 bin'
    for _,base in ipairs(selected and {selected} or bases) do
      local f=io.open(base..e[1],'rb')
      if f then
        local candidate=f:read('*a');f:close()
        if candidate and #candidate==e[2] then
          local sum=0;for j=1,#candidate do sum=sum+candidate:byte(j) end
          if sum==e[3] then blob=candidate;selected=base;break end
          reason='原生数据校验失败：'..e[1]
        else reason='原生数据长度错误：'..e[1] end
      end
    end
    assert(blob,reason)
    chunks[#chunks+1]=decode(blob,e[4])
    if coroutine.isyieldable() then coroutine.yield() end
  end
  return table.concat(chunks)
end
""".replace('@@SPEC@@',','.join(spec)).encode('utf-8')
 reader=reader.replace(b'@@DECODE@@',LZ_DECODER[:-1])
 # Independent 8KiB blocks bound Lua concatenation and yield between blocks.
 data=data.replace(b'local MODULE_BIN,CHAOS_BIN,CHAOS_RELOCS=',reader+b'local MODULE_BIN,CHAOS_BIN,CHAOS_RELOCS=',1)
 data=data.replace(b'@@CHAOS_PAYLOAD@@',b'read_payload()')
 data=data.replace(b'@@CHAOS_ICON@@',icon+b'\n'+settings_write)
 data=data.replace(b'@@PET_ASSET@@',pet_code)
 version_code=(B/'data-version.lua.in').read_text('utf-8-sig').replace('@@DATA_VERSION@@','2.2-alpha.57-honeycomb4').encode('utf8')
 asset_specs=[]
 for name,blob in [('chaos_icon.bin',raw),('chaos_settings_icon.bin',settings_raw),('spotify_cover.bin',cover_raw)]:
  asset_specs.append(b'{'+lua(name).encode()+b','+binary_expression(blob)+b'}')
 version_code=version_code.replace(b'@@DATA_ASSETS@@',b','.join(asset_specs))
 start=data.index(b'local function write_icon()');end=data.index(b'\nlocal function arm_registrar()',start)
 data=data[:start]+version_code+b'\nlocal function write_icon()\n update_program_data()\nend\n'+data[end:]
 import re
 assert not re.findall(rb'@@[A-Z_]+@@',data),'unexpanded template marker'
 (G/'main.lua').write_bytes(data)
 m={'app_id':0xe7d4,'page_id':0xe7d40000,'face_id':'990000000029','name':'N67 Chaos Installer','version':'2.2-alpha.57-honeycomb4','title':'Chaos',
  'identity':'com.chaos.manager','pages':PAGE_COUNT,'firmware':'3.1.190','icon_path':'/data/chaos/chaos_icon.bin','profile':'settings-egg' if os.environ.get('CHAOS_SETTINGS_EGG')=='1' else 'standard','hardware_tested':False,'relocations':len(c['relocations'])}
 (B/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8')
 print('Installer embedded: bridge/Rust/relocations/icon verified by encoder')
if __name__=='__main__':main()







