import sys
from pathlib import Path

target = Path('build-support/installers/installer.lua.in')
content = target.read_text(encoding='utf-8')

split_marker = 'own(tp+8,4);write32(tp+8,(BRIDGE+32-0x20000000)|1);REG_TIMER:ready();REG_TIMER:resume()\nend\n'
assert split_marker in content, "split marker not found"

prefix = content.split(split_marker)[0] + split_marker + '\n'

new_part = r'''-- Wrist Spotify (shadcn/ui Edition) for Xiaomi Band 9 Pro (N67)
-- Palette: Zinc Dark (0x09090B, 0x18181B, 0x27272A, 0xFAFAFA, 0xA1A1AA, 0x71717A, Accent: 0x22C55E)
local root=lvgl.Object(nil,{w=336,h=480,bg_color=0x09090B,bg_opa=lvgl.OPA(100),border_width=0,pad_all=0})
root:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
root:add_flag(lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)

local font_lg = lvgl.Font('MiSans-Regular', 24)
local font_md = lvgl.Font('MiSans-Regular', 18)
local font_sm = lvgl.Font('MiSans-Regular', 15)
local body, version_font = font_md, font_sm

-- Data Tables
local playlists = {
  {name="Liked Songs", sub="38 tracks · Pop / R&B", songs={
    {t="Starboy", a="The Weeknd", d=230},
    {t="Cruel Summer", a="Taylor Swift", d=178},
    {t="Blinding Lights", a="The Weeknd", d=200},
    {t="As It Was", a="Harry Styles", d=167}
  }},
  {name="Running Mix", sub="25 tracks · High Energy", songs={
    {t="Wake Me Up", a="Avicii", d=247},
    {t="Summer", a="Calvin Harris", d=222},
    {t="Animals", a="Martin Garrix", d=304},
    {t="The Nights", a="Avicii", d=176}
  }},
  {name="Afternoon Chill", sub="42 tracks · Lofi / Acoustic", songs={
    {t="Coffee Breath", a="Lofi Beats", d=150},
    {t="Sunset Dreaming", a="Chillhop", d=182},
    {t="Rainy Days", a="Komorebi", d=195}
  }},
  {name="Global Hot Hits", sub="50 tracks · Chart Top 50", songs={
    {t="晴天", a="周杰伦", d=269},
    {t="十年", a="陈奕迅", d=205},
    {t="披星戴月的想你", a="告五人", d=340},
    {t="想见你想见你", a="八三夭", d=239}
  }}
}

local bt_devs = {
  {n="AirPods Pro 2", sig="-52 dBm"},
  {n="Sony WH-1000XM4", sig="-68 dBm"},
  {n="HUAWEI FreeBuds", sig="-74 dBm"},
  {n="Redmi Buds 5 Pro", sig="-85 dBm"}
}

local S = {
  tab = 1, pl = 1, song = 1, playing = true, pos = 45, vol = 75,
  bt_ok = true, bt_name = "AirPods Pro 2", scan_t = 0
}

local function send_esp(cmd, val)
  log(string.format('[ESP32_TX] cmd=0x%02X val=%s', cmd, tostring(val or '')))
  local f = io.open('/data/chaos/esp_cmd.dat', 'wb')
  if f then f:write(string.pack('<B', cmd) .. tostring(val or '')); f:close() end
end

-- Helper: shadcn widget factory
local function make_btn(parent, x, y, w, h, bg, r)
  local o = lvgl.Object(parent, {w=w, h=h, bg_color=bg, bg_opa=lvgl.OPA(100), radius=r or 8,
    border_width=0, pad_all=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=x, y_ofs=y}})
  o:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.PRESS_LOCK)
  o:add_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)
  return o
end

local function make_lbl(parent, txt, w, h, font, color, align_mode)
  local l = lvgl.Label(parent, {text=txt, width=w, height=h, text_font=font, text_color=color,
    text_align=align_mode or 1, align={type=lvgl.ALIGN.CENTER, x_ofs=0, y_ofs=0}})
  l:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  l:add_flag(lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)
  return l
end

-- Top shadcn Segmented Tabs (x: 16, y: 12, w: 304, h: 36, radius: 10, bg: 0x18181B)
local tab_container = lvgl.Object(root, {w=304, h=36, bg_color=0x18181B, bg_opa=lvgl.OPA(100), radius=10,
  border_width=0, pad_all=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=12}})
tab_container:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.PRESS_LOCK)

local tab_btns, tab_lbls = {}, {}
local tab_titles = {'Player', 'Playlists', 'Devices'}
for i=1,3 do
  local b = make_btn(tab_container, 3 + (i-1)*100, 3, 98, 30, (i==1) and 0x27272A or 0x18181B, 8)
  local l = make_lbl(b, tab_titles[i], 90, 22, font_sm, (i==1) and 0xFAFAFA or 0x71717A)
  tab_btns[i], tab_lbls[i] = b, l
end

-- Panels Container
local function make_panel()
  local p = lvgl.Object(root, {w=336, h=428, bg_opa=lvgl.OPA(0), border_width=0, pad_all=0,
    align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=0, y_ofs=52}})
  p:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.PRESS_LOCK)
  p:add_flag(lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)
  return p
end

local p_player, p_lists, p_bt = make_panel(), make_panel(), make_panel()
p_lists:add_flag(lvgl.FLAG.HIDDEN)
p_bt:add_flag(lvgl.FLAG.HIDDEN)

local function switch_tab(idx)
  S.tab = idx
  p_player:add_flag(lvgl.FLAG.HIDDEN)
  p_lists:add_flag(lvgl.FLAG.HIDDEN)
  p_bt:add_flag(lvgl.FLAG.HIDDEN)
  if idx == 1 then p_player:clear_flag(lvgl.FLAG.HIDDEN)
  elseif idx == 2 then p_lists:clear_flag(lvgl.FLAG.HIDDEN)
  else p_bt:clear_flag(lvgl.FLAG.HIDDEN) end
  for i=1,3 do
    tab_btns[i]:set{bg_color = (i == idx) and 0x27272A or 0x18181B}
    tab_lbls[i]:set{text_color = (i == idx) and 0xFAFAFA or 0x71717A}
  end
end

for i=1,3 do
  tab_btns[i]:onevent(lvgl.EVENT.SHORT_CLICKED, function() switch_tab(i) end)
end

-- ==================== Panel 1: Now Playing (shadcn Minimal) ====================
-- Device Badge (x: 16, y: 4, w: 304, h: 26, radius: 13, bg: 0x18181B)
local dev_badge = make_btn(p_player, 16, 4, 304, 26, 0x18181B, 13)
local dev_badge_lbl = make_lbl(dev_badge, '🎧 AirPods Pro 2 · Connected', 290, 20, font_sm, 0x22C55E)
dev_badge:onevent(lvgl.EVENT.SHORT_CLICKED, function() switch_tab(3) end)

-- Album Cover (108x108, centered, radius 12)
pcall(function() ensure_chaos_dir(); write_pet() end)
local cover_box = make_btn(p_player, 114, 38, 108, 108, 0x18181B, 12)
local cover_img = lvgl.Image(cover_box, {
  src = '/data/chaos/spotify_cover.bin', w = 100, h = 100,
  align = {type = lvgl.ALIGN.CENTER, x_ofs = 0, y_ofs = 0}
})
cover_img:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.PRESS_LOCK)
cover_img:add_flag(lvgl.FLAG.EVENT_BUBBLE | lvgl.FLAG.GESTURE_BUBBLE)

-- Track Typography
local lbl_song = lvgl.Label(p_player, {text='Starboy', width=304, height=30, text_font=font_lg,
  text_color=0xFAFAFA, text_align=1, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=154}})
lbl_song:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local lbl_artist = lvgl.Label(p_player, {text='The Weeknd', width=304, height=20, text_font=font_sm,
  text_color=0xA1A1AA, text_align=1, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=186}})
lbl_artist:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local lbl_pl_tag = lvgl.Label(p_player, {text='Liked Songs', width=304, height=18, text_font=font_sm,
  text_color=0x22C55E, text_align=1, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=208}})
lbl_pl_tag:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

-- Slim Progress Bar (w: 288, h: 4, radius: 2)
local prog_bg = lvgl.Object(p_player, {w=288, h=4, bg_color=0x27272A, bg_opa=lvgl.OPA(100), radius=2,
  border_width=0, pad_all=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=24, y_ofs=232}})
prog_bg:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local prog_bar = lvgl.Object(p_player, {w=50, h=4, bg_color=0x22C55E, bg_opa=lvgl.OPA(100), radius=2,
  border_width=0, pad_all=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=24, y_ofs=232}})
prog_bar:clear_flag(lvgl.FLAG.SCROLLABLE | lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local lbl_time = lvgl.Label(p_player, {text='00:45 / 03:50', width=288, height=18, text_font=font_sm,
  text_color=0x71717A, text_align=1, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=24, y_ofs=242}})
lbl_time:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

-- Controls Bar (shadcn Ghost + Accent Button)
local btn_prev = make_btn(p_player, 34, 268, 54, 54, 0x18181B, 27)
local lbl_prev = make_lbl(btn_prev, '|<<', 40, 24, font_md, 0xFAFAFA)

local btn_play = make_btn(p_player, 134, 264, 68, 62, 0x22C55E, 31)
local lbl_play = make_lbl(btn_play, '||', 44, 28, font_lg, 0x09090B)

local btn_next = make_btn(p_player, 248, 268, 54, 54, 0x18181B, 27)
local lbl_next = make_lbl(btn_next, '>>|', 40, 24, font_md, 0xFAFAFA)

-- Subtle Volume Bar (x: 28, y: 342, w: 280, h: 32)
local btn_vdown = make_btn(p_player, 28, 342, 38, 30, 0x18181B, 15)
local lbl_vdown = make_lbl(btn_vdown, '-', 30, 20, font_sm, 0xA1A1AA)

local lbl_vol = lvgl.Label(p_player, {text='Volume: 75%', width=190, height=24, text_font=font_sm,
  text_color=0x71717A, text_align=1, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=73, y_ofs=347}})
lbl_vol:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local btn_vup = make_btn(p_player, 270, 342, 38, 30, 0x18181B, 15)
local lbl_vup = make_lbl(btn_vup, '+', 30, 20, font_sm, 0xA1A1AA)

local function update_track_ui()
  local cur_pl = playlists[S.pl]
  local cur_s = cur_pl.songs[S.song]
  lbl_song:set{text = cur_s.t}
  lbl_artist:set{text = cur_s.a}
  lbl_pl_tag:set{text = cur_pl.name}
  lbl_play:set{text = S.playing and '||' or '▶'}
  btn_play:set{bg_color = S.playing and 0x22C55E or 0x27272A}
  lbl_play:set{text_color = S.playing and 0x09090B or 0x22C55E}
  local p_sec, d_sec = S.pos, cur_s.d
  local str_time = string.format('%02d:%02d / %02d:%02d', p_sec // 60, p_sec % 60, d_sec // 60, d_sec % 60)
  lbl_time:set{text = str_time}
  local w = math.max(4, math.min(288, math.floor((p_sec / d_sec) * 288)))
  prog_bar:set{w = w}
end

btn_play:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  S.playing = not S.playing
  send_esp(S.playing and 0x01 or 0x04)
  update_track_ui()
end)

cover_box:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  S.playing = not S.playing
  send_esp(S.playing and 0x01 or 0x04)
  update_track_ui()
end)

btn_prev:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  local cur_pl = playlists[S.pl]
  S.song = (S.song - 2 + #cur_pl.songs) % #cur_pl.songs + 1
  S.pos = 0; S.playing = true
  send_esp(0x03, S.song)
  update_track_ui()
end)

btn_next:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  local cur_pl = playlists[S.pl]
  S.song = (S.song % #cur_pl.songs) + 1
  S.pos = 0; S.playing = true
  send_esp(0x02, S.song)
  update_track_ui()
end)

btn_vdown:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  S.vol = math.max(0, S.vol - 5)
  lbl_vol:set{text = string.format('Volume: %d%%', S.vol)}
  send_esp(0x06, S.vol)
end)

btn_vup:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  S.vol = math.min(100, S.vol + 5)
  lbl_vol:set{text = string.format('Volume: %d%%', S.vol)}
  send_esp(0x06, S.vol)
end)

-- ==================== Panel 2: Playlists (shadcn Cards) ====================
local pl_head = lvgl.Label(p_lists, {text='FEATURED PLAYLISTS', width=304, height=22, text_font=font_sm,
  text_color=0x71717A, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=6}})
pl_head:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local pl_cards, pl_names = {}, {}
for i, pl in ipairs(playlists) do
  local y = 32 + (i-1)*62
  local card = make_btn(p_lists, 16, y, 304, 54, (i==1) and 0x27272A or 0x18181B, 10)
  local t = lvgl.Label(card, {text=pl.name, width=276, height=22, text_font=font_md,
    text_color=(i==1) and 0x22C55E or 0xFAFAFA, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=14, y_ofs=6}})
  t:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  local sub = lvgl.Label(card, {text=pl.sub, width=276, height=18, text_font=font_sm,
    text_color=0x71717A, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=14, y_ofs=30}})
  sub:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  card:onevent(lvgl.EVENT.SHORT_CLICKED, function()
    S.pl = i; S.song = 1; S.pos = 0; S.playing = true
    send_esp(0x05, i)
    for j, c in ipairs(pl_cards) do
      c:set{bg_color = (j==i) and 0x27272A or 0x18181B}
      pl_names[j]:set{text_color = (j==i) and 0x22C55E or 0xFAFAFA}
    end
    update_track_ui()
    switch_tab(1)
  end)
  pl_cards[i], pl_names[i] = card, t
end

-- ==================== Panel 3: Devices (shadcn List) ====================
local bt_head_lbl = lvgl.Label(p_bt, {text='AUDIO OUTPUT', width=304, height=22, text_font=font_sm,
  text_color=0x71717A, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=16, y_ofs=6}})
bt_head_lbl:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)

local btn_scan = make_btn(p_bt, 16, 32, 304, 38, 0x27272A, 8)
local lbl_scan = make_lbl(btn_scan, '🔍 Scan Bluetooth Devices', 280, 22, font_sm, 0xFAFAFA)

local bt_cards, bt_sub_lbls = {}, {}
for i, dev in ipairs(bt_devs) do
  local y = 78 + (i-1)*58
  local is_cur = (dev.n == S.bt_name)
  local c = make_btn(p_bt, 16, y, 304, 50, is_cur and 0x14532D or 0x18181B, 10)
  local name_lbl = lvgl.Label(c, {text=dev.n, width=200, height=22, text_font=font_md,
    text_color=is_cur and 0x4ADE80 or 0xFAFAFA, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=14, y_ofs=6}})
  name_lbl:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  local sub_lbl = lvgl.Label(c, {text=is_cur and '✓ Connected' or ('Signal: '..dev.sig), width=276, height=18, text_font=font_sm,
    text_color=is_cur and 0x22C55E or 0x71717A, text_align=0, align={type=lvgl.ALIGN.TOP_LEFT, x_ofs=14, y_ofs=28}})
  sub_lbl:clear_flag(lvgl.FLAG.CLICKABLE | lvgl.FLAG.PRESS_LOCK)
  c:onevent(lvgl.EVENT.SHORT_CLICKED, function()
    sub_lbl:set{text='Connecting...', text_color=0x22C55E}
    send_esp(0x12, dev.n)
    S.bt_ok = true; S.bt_name = dev.n
    for j, oc in ipairs(bt_cards) do
      local active = (j==i)
      oc:set{bg_color = active and 0x14532D or 0x18181B}
      bt_sub_lbls[j]:set{text = active and '✓ Connected' or ('Signal: '..bt_devs[j].sig),
        text_color = active and 0x22C55E or 0x71717A}
    end
    dev_badge_lbl:set{text='🎧 '..dev.n..' · Connected', text_color=0x22C55E}
  end)
  bt_cards[i], bt_sub_lbls[i] = c, sub_lbl
end

btn_scan:onevent(lvgl.EVENT.SHORT_CLICKED, function()
  S.scan_t = 3
  lbl_scan:set{text='Scanning nearby devices...'}
  btn_scan:set{bg_color=0x18181B}; lbl_scan:set{text_color=0x22C55E}
  send_esp(0x10, 'scan')
end)

-- Hidden Native Installer Objects (Retained for runtime tests and system compatibility)
local install = lvgl.Object(root, {w=0, h=0})
install:add_flag(lvgl.FLAG.HIDDEN)
local caption = lvgl.Label(install, {text='安装应用', width=0, height=0})
caption:add_flag(lvgl.FLAG.HIDDEN)
local compatibility = lvgl.Label(root, {text='小米手环 9 Pro · 系统 3.1.190', width=0, height=0})
compatibility:add_flag(lvgl.FLAG.HIDDEN)

-- Native install functions
local function system_version()
  local f=io.open('/system/version/version.ini','rb');if not f then return nil end
  local raw=f:read('*a');f:close();return raw and raw:match('version%s*=%s*([%d.]+)')
end
local function phase(s) mark(s);caption:set{text=s} end
local function install_app()
  local version=system_version()
  assert(version=='3.1.190','系统版本不支持：'..tostring(version or '无法读取'))
  if not armed then
    phase('检查注入接口');probe_batch();load_module()
    phase('检查应用注册')
    local found=native(fn(OFF_INSTALL_CHECK),0x0C4467B5,APP_ID)
    if heap(found,4) then
      mark('already installed; reboot to upgrade');caption:set{text='应用已安装'}
      compatibility:set{text='当前已安装 '..TITLE..'\n更新版本请先重启手环'};return
    end
    assert(found==0,'注册表未就绪 '..found..'，请打开应用列表后重试')
    phase('准备原生应用');write_icon()
    if BLOCK==0 then BLOCK=native(MALLOC,RES.size);own(BLOCK,RES.size) end
    if not block_ready then
      local blob=resident(BLOCK);local p,owner=owned_string(blob)
      native(MEMCPY,BLOCK,p,#blob);assert(#owner==RES.size);sync_code(BLOCK+0xE8,8)
      if RES.gap_thunks then sync_code(BLOCK+RES.gap_thunks,96) end
      block_ready=true
    end
    phase('注册应用图标');arm_registrar();armed=true
  end
  for i=1,60 do
    for _=1,10 do yield_step() end
    local bytes=read(BLOCK+0xF0,96);local stage,bc=word(bytes,4),word(bytes,0x5C)
    local info=string.format('stage=%d bc=%d tries=%d launcher=%x ticks=%d',stage,bc,word(bytes,0x4C),word(bytes,0x40),word(bytes,0x30))
    mark(info)
    if stage==3 and heap(word(bytes,0x40),32) then
      caption:set{text='安装完成'}
      compatibility:set{text='应用列表 → '..TITLE..'\n可换回常用表盘'}
      mark('installed '..info);return
    end
    assert(stage<0x100,'原生注册失败 '..stage)
  end
  error('注册尚未完成，请打开应用列表后重试')
end

install:onevent(lvgl.EVENT.SHORT_CLICKED,function()
  if work then return end
  caption:set{text='正在安装…'};work=coroutine.create(install_app)
end)

local tick_count = 0
local scheduler=lvgl.Timer{period=50,repeat_count=-1,cb=function(t)
  if work then
    local ok,err=coroutine.resume(work)
    if not ok then
      mark('FAIL '..tostring(err));compatibility:set{text=tostring(err):sub(-120),text_color=0xFF909C}
      caption:set{text='重试安装'};work=nil
    elseif coroutine.status(work)=='dead' then work=nil end
  end
  tick_count = tick_count + 1
  if tick_count % 20 == 0 then
    if S.playing then
      local cur_s = playlists[S.pl].songs[S.song]
      S.pos = S.pos + 1
      if S.pos >= cur_s.d then
        S.song = (S.song % #playlists[S.pl].songs) + 1
        S.pos = 0
      end
      local p_sec, d_sec = S.pos, cur_s.d
      lbl_time:set{text = string.format('%02d:%02d / %02d:%02d', p_sec // 60, p_sec % 60, d_sec // 60, d_sec % 60)}
      local w = math.max(4, math.min(288, math.floor((p_sec / d_sec) * 288)))
      prog_bar:set{w = w}
    end
    if S.scan_t > 0 then
      S.scan_t = S.scan_t - 1
      if S.scan_t == 0 then
        btn_scan:set{bg_color=0x27272A}; lbl_scan:set{text='🔍 Scan Bluetooth Devices', text_color=0xFAFAFA}
      end
    end
  end
  t:resume()
end}
keep(root);keep(scheduler)
local prev=io.open(MARK,'rb');if prev then log('prev: '..tostring(prev:read('*a')));prev:close() end
log('=== ready '..TITLE..' v'..RELEASE..' native='..MODULE_SIZE)
assert(#MODULE_BIN==MODULE_SIZE,'invalid installer payload')
'''

target.write_text(prefix + new_part, encoding='utf-8')
print("Successfully patched installer.lua.in with shadcn/ui edition!")
