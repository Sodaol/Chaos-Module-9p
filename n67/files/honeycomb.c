/* Chaos honeycomb on N67, derived from the Bubble45 launcher adapter.
 * Platform addresses and injection infrastructure derived from Chaos (AGPL-3.0).
 */
typedef unsigned int u32; typedef unsigned short u16; typedef unsigned char u8;
typedef signed int i32; typedef signed short i16;
#define RD(a) (*(volatile u32 *)(a))
#define FN(a,t) ((t)(a))
#define MAX_APPS 192u
#define GRID_CLASS 0x2c69e840u
#define HC_INPUT_CHAIN (256u | 512u | 65536u | 131072u)
static int hc_ptr(u32 p){return !(p&3u)&&((p>=0x20000000u&&p<0x20100000u)||(p>=0x3c000020u&&p<0x3f000000u));}
static int hc_strptr(u32 p){return (p>=0x20000000u&&p<0x20100000u)||(p>=0x2c080000u&&p<0x2c800000u)||(p>=0x3c000020u&&p<0x3f000000u);}
static void hc_flag(u32 o,u32 bits,int on){FN(on?0xc23ba45u:0xc23babbu,void(*)(u32,u32))(o,bits);}
static void hc_prop(u32 o,u32 p,u32 v){FN(0xc242e8bu,void(*)(u32,u32,u32,u32))(o,p,v,0);}
static void hc_size(u32 o,i32 w,i32 h){FN(0xc23af59u,void(*)(u32,i32,i32))(o,w,h);}
static void hc_align(u32 o,u32 a,i32 x,i32 y){FN(0xc23afe3u,void(*)(u32,u32,i32,i32))(o,a,x,y);}
static u32 hc_event(u32 o,u32 cb,u32 filter,u32 ud){return FN(0xc241159u,u32(*)(u32,u32,u32,u32))(o,cb,filter,ud);}
static u32 hc_event_once(u32 o,u32 cb,u32 filter,u32 ud){
 u32 spec=RD(o+8u);if(hc_ptr(spec)){u32 list=RD(spec+12u),n=*(volatile u8 *)(spec+26u)&63u;
  if(n&&hc_ptr(list))for(u32 i=0;i<n;i++)if(RD(list+12u*i)==cb&&RD(list+12u*i+4u)==ud&&RD(list+12u*i+8u)==filter)return 1;
 }
 return hc_event(o,cb,filter,ud);
}
static u32 hc_object(u32 p){return FN(0xc23f09du,u32(*)(u32))(p);}
static void hc_erase(u32 o){FN(0xc242785u,void(*)(u32))(o);}
static void hc_plain(u32 o){for(u32 p=0x10;p<=0x13;p++)hc_prop(o,p,0);hc_prop(o,0x32,0);hc_prop(o,0x35,0);hc_prop(o,0x39,0);hc_prop(o,0x21,0);hc_flag(o,8192|16,0);}
typedef struct {
 u32 id, icon, cell, circle, image, source_edge, diameter;
 i32 x, y;
 u32 visible;
} hc_Item;
typedef struct {
 u32 overlay, grid, hidden, hash, count, built;
 u32 dirty, edit_requested, suspended_grid;
 u32 refresh_timer, motion_timer, last_scan, active_page, enabled;
 u32 pressed_item, rescale_pending, entry_page;
 u32 exit_pending, allow_back;
 i32 width, height, origin_x, origin_y;
 hc_Item items[MAX_APPS];
} hc_State;
static hc_State hc_S;
static hc_State *hc_state(void) { return (hc_State *)((u32)&hc_S + 0x20000000u); }
extern u32 chaos_honeycomb_input(u32 code, i32 x, i32 y, u32 count);
extern void chaos_honeycomb_frame(u32 index, i32 out[4]);
u32 chaos_honeycomb_overlay(void) { return hc_state()->hidden ? hc_state()->overlay : 0; }

static int hc_childof(u32 root,u32 o){for(u32 i=0;i<32u&&hc_ptr(o);i++){if(o==root)return 1;o=RD(o+4u);}return 0;}
static void hc_retire(hc_State *s) {
 u32 overlay = s->overlay;
 s->overlay = 0;
 if (s->hidden && hc_ptr(s->grid) && RD(s->grid) == GRID_CLASS) hc_flag(s->grid, 1, 0);
 s->hidden = 0;
 s->grid = 0;
 s->built = 0;
 s->hash = 0;
 s->edit_requested = 0;
 s->pressed_item = 0;
 s->rescale_pending = 0;
 s->exit_pending = 0;
 if (hc_ptr(overlay)) hc_erase(overlay);
}

static int hc_scan(hc_State *s, u32 *signature, u32 store);
static void hc_update_frames(hc_State *s);

static u32 hc_now(void) { return FN(0xc1610b9u, u32(*)(void))(); }

static void hc_motion(u32 timer) {
 hc_State *s = hc_state();
 if (s->hidden && s->overlay && *(volatile u8 *)0x200ca379u == 2 &&
     FN(0xc44a5adu, u32(*)(u32))(0xffffffffu) == s->active_page) {
  if (s->exit_pending) {
   s->exit_pending = 0;
   s->allow_back = 1;
   FN(0xc4490b9u, void(*)(void))();
   s->allow_back = 0;
   return;
  }
  s->dirty |= chaos_honeycomb_input(11, 0, 0, s->count);
  if (s->dirty || (s->rescale_pending && !chaos_honeycomb_input(13, 0, 0, s->count))) {
   s->dirty = 0;
   hc_update_frames(s);
   return;
  }
 }
 *(volatile u8 *)(timer + 0x14u) |= 1u;
}

static void hc_wake_motion(hc_State *s) {
 if (!s->motion_timer)
  s->motion_timer = FN(0xc25a289u, u32(*)(u32,u32,u32))((u32)hc_motion, 16, 0);
 if (hc_ptr(s->motion_timer))
  *(volatile u8 *)(s->motion_timer + 0x14u) &= (u8)~1u;
}


/* One fixed touch surface owns the whole gesture. Moving icon objects never
 * participate in input hit testing or in the system scroll/gesture chain.
 */
static u32 hc_hit_item(hc_State *s, i32 x, i32 y) {
 for (u32 i = s->built; i > 0; --i) {
  const hc_Item *item = &s->items[i - 1];
  if (!item->visible || !item->diameter) continue;
  i32 radius = (i32)item->diameter / 2;
  i32 dx = x - item->x - radius;
  i32 dy = y - item->y - radius;
  if (dx < -radius || dx > radius || dy < -radius || dy > radius) continue;
  if (dx * dx + dy * dy <= radius * radius) return i;
 }
 return 0;
}

static void hc_ui_event(u32 e) {
 if (!hc_ptr(e)) return;
 hc_State *s = hc_state();
 u32 object_id = RD(e + 4u);
 u32 code = *(volatile u8 *)(e + 8u) & 127u;
 if (code == 35u) {
  if (object_id == s->overlay) { s->overlay = 0; s->built = 0; }
  if (object_id == s->grid) { s->grid = 0; s->hidden = 0; }
  if (object_id == s->suspended_grid) s->suspended_grid = 0;
  return;
 }
 if (!s->hidden || object_id != s->overlay || !hc_ptr(object_id)) return;
 if (code == 5u && s->pressed_item &&
     chaos_honeycomb_input(7, 0, 0, s->count)) {
  s->edit_requested = 1;
  s->pressed_item = 0;
  chaos_honeycomb_input(3, 0, 0, s->count);
  return;
 }
 if (code == 7u) {
  u32 pressed = s->pressed_item;
  s->pressed_item = 0;
  if (!pressed || pressed > s->built || s->edit_requested ||
      !chaos_honeycomb_input(7, 0, 0, s->count)) return;
  u32 hash;
  if (!hc_scan(s, &hash, 0) || hash != s->hash) return;
  /* Stock click consumes current_target and the app ID. */
  u32 saved_data = RD(e + 12u);
  RD(e + 4u) = s->items[pressed - 1].cell;
  RD(e + 12u) = s->items[pressed - 1].id;
  FN(0xc2a1dd5u, void(*)(u32))(e);
  RD(e + 4u) = object_id;
  RD(e + 12u) = saved_data;
  return;
 }
 if (code == 3u || code == 8u) {
  s->exit_pending = chaos_honeycomb_input(code, 0, 0, s->count);
  if (code == 3u) s->pressed_item = 0;
  hc_wake_motion(s);
  return;
 }
 if (code != 1u && code != 2u) return;
 u32 indev = RD(0x200bf388u);
 if (!hc_ptr(indev)) {
  s->pressed_item = 0;
  chaos_honeycomb_input(3, 0, 0, s->count);
  return;
 }
 i16 point[2];
 FN(0xc239f93u, void(*)(u32, i16 *))(indev, point);
 i32 x = point[0] - s->origin_x;
 i32 y = point[1] - s->origin_y;
 if (code == 1u) { s->exit_pending = 0; s->pressed_item = hc_hit_item(s, x, y); }
 s->dirty |= chaos_honeycomb_input(code, x * 336 / s->width, y * 480 / s->height, s->count);
 if (s->dirty) hc_wake_motion(s);
}

/* Scan the already ordered visible desktop chain. No apps.json/order writes. */
static int hc_scan(hc_State *s,u32 *signature,u32 store){
 if(RD(0x200a3938u)!=24u)return 0;
 u32 node=RD(0x200a393cu),prev=0,n=0,h=2166136261u;
 while(node){
  if(n>=MAX_APPS||!hc_ptr(node)||!hc_ptr(node+28u)||RD(node+24u)!=prev)return 0;
  u32 id=*(volatile u16 *)node,icon=RD(node+12u);
  if(!id||!hc_strptr(icon))return 0;
  u32 j;for(j=0;j<256u;j++){if(!hc_strptr(icon+j))return 0;if(!*(volatile u8 *)(icon+j))break;}
  if(j==0u||j==256u)return 0;
  h=(h^id)*16777619u;h=(h^node)*16777619u;h=(h^icon)*16777619u;
  if(store){s->items[n].id=id;s->items[n].icon=icon;}
  n++;prev=node;node=RD(node+28u);
 }
 if(!n||RD(0x200a3940u)!=prev)return 0;
 if(store)s->count=n;*signature=h;return 1;
}
static void hc_set_diameter(hc_Item *item,u32 diameter){
 if(item->diameter==diameter)return;
 item->diameter=diameter;
 hc_size(item->circle,diameter,diameter);
 hc_prop(item->circle,0x0b,diameter/2u);
 if(item->source_edge){
  u32 zoom=diameter*256u/item->source_edge;
  *(volatile u16 *)(item->image+0x36u)=zoom?zoom:1u;
  FN(0xc23e981u,void(*)(u32))(item->image);
  FN(0xc23b38bu,void(*)(u32))(item->image);
 }
}

static void hc_update_frames(hc_State *s) {
 u32 defer_scale = chaos_honeycomb_input(13, 0, 0, s->count);
 s->rescale_pending = defer_scale;
 for (u32 i = 0; i < s->built; ++i) {
  hc_Item *item = &s->items[i];
  i32 f[4];
  chaos_honeycomb_frame(i, f);
  if (item->visible != (u32)f[3]) {
   hc_flag(item->cell, 1, !f[3]);
   item->visible = (u32)f[3];
  }
  if (!f[3]) continue;
  u32 diameter = (u32)f[2] * (u32)s->width / 336u;
  diameter = (diameter + 2u) & ~3u;
  if (!diameter) diameter = 4;
  if (defer_scale && item->diameter) diameter = item->diameter;
  i32 x = f[0] * s->width / 336 - (i32)diameter / 2;
  i32 y = f[1] * s->height / 480 - (i32)diameter / 2;
  if (item->diameter != diameter) hc_size(item->cell, diameter, diameter);
  if (item->x != x || item->y != y) {
   hc_align(item->cell, 1, x, y);
   item->x = x;
   item->y = y;
  }
  hc_set_diameter(item, diameter);
 }
}

static int hc_add_icon(hc_State *s,u32 index){
 hc_Item *item=&s->items[index];
 u32 cell=hc_object(s->overlay);
 if(!cell)return 0;
 hc_plain(cell);
 hc_flag(cell, 2u | HC_INPUT_CHAIN, 0);

 u32 circle=hc_object(cell);
 if(!circle){hc_erase(cell);return 0;}
 hc_plain(circle);
 hc_flag(circle,2,0);
 hc_prop(circle,0x17,1); /* Clip only the outer corners of the scaled image. */
 hc_align(circle,9,0,0);
 u32 image=FN(0xc25eba1u,u32(*)(u32))(circle);
 if(!image){hc_erase(cell);return 0;}
 FN(0xc2617d9u,void(*)(u32,u32))(image,item->icon);
 u32 width=*(volatile u16 *)(image+0x2cu);
 u32 height=*(volatile u16 *)(image+0x2eu);
 item->cell=cell;
 item->circle=circle;
 item->image=image;
 item->source_edge=width>height?width:height;
 item->diameter=0;
 hc_align(image,9,0,0);
 hc_flag(image,2|16|8192,0);
 item->x = item->y = -32768;
 item->visible = 1;
 return 1;
}

void chaos_honeycomb_update(u32 enabled);

/* N67 lv_disp_drv_register stores the native refresh timer at disp+4.
 * Replace its callback only while the timer and its display are a verified pair.
 */
static void hc_before_refresh(u32 timer) {
 if (hc_state()->enabled) {
  chaos_honeycomb_update(1);
 } else if (hc_ptr(timer) && RD(timer + 8u) == ((u32)hc_before_refresh | 1u)) {
  RD(timer + 8u) = 0xc2467a1u;
 }
 FN(0xc2467a1u, void(*)(u32))(timer);
}

static void hc_bind_refresh(hc_State *s, u32 enabled) {
 u32 display = RD(0x200b3750u);
 u32 timer = hc_ptr(display) ? RD(display + 4u) : 0;
 if (!hc_ptr(timer) || RD(timer + 12u) != display) return;
 u32 callback = (u32)hc_before_refresh | 1u;
 if (enabled && RD(timer + 8u) == 0xc2467a1u) {
  RD(timer + 8u) = callback;
  s->refresh_timer = timer;
 } else if (!enabled && timer == s->refresh_timer && RD(timer + 8u) == callback) {
  RD(timer + 8u) = 0xc2467a1u;
  s->refresh_timer = 0;
 }
}

static void hc_update(u32 enabled, u32 entry_page, u32 entry_root) {
 hc_State *s = hc_state();
 if (!enabled) {
  if (s->refresh_timer) hc_bind_refresh(s, 0);
  if (s->overlay || s->grid) hc_retire(s);
  s->suspended_grid = 0;
  return;
 }
 if (*(volatile u8 *)0x200ca379u != 2) return;
 hc_bind_refresh(s, 1);
 u32 top = entry_page ? entry_page : FN(0xc44a5adu, u32(*)(u32))(0xffffffffu);
 if (!hc_ptr(top) || RD(top + 0x14u) != 0x100000u) {
  s->suspended_grid = 0;
  return;
 }
 u32 root = entry_root ? entry_root : RD(top + 0x2cu);
 u32 grid = RD(0x200cb4c0u);
 if (!hc_ptr(root) || !hc_ptr(grid) || !hc_ptr(grid + 0x894u) || RD(grid) != GRID_CLASS ||
     !hc_childof(root, grid) || RD(grid + 0x880u) != 1u) {
  if (s->overlay || s->grid) hc_retire(s);
  s->suspended_grid = 0;
  return;
 }
 u32 manager = RD(0x200cacd0u);
 /* The incoming launcher owns the root saved by its stock on_create.
  * The watchface-visible byte may still describe the outgoing face.
  */
 u32 native_entry = entry_page || root == RD(0x200cae00u);
 u32 face_visible = !native_entry && hc_ptr(manager) && hc_ptr(manager + 0x6cu) &&
                    !*(volatile u8 *)(manager + 0x6cu) &&
                    *(volatile u8 *)(manager + 0x6du);
 if (face_visible) {
  if (s->hidden) {
   if (hc_ptr(s->overlay)) hc_flag(s->overlay, 1, 1);
   if (hc_ptr(s->grid) && RD(s->grid) == GRID_CLASS) hc_flag(s->grid, 1, 0);
   s->hidden = 0;
   chaos_honeycomb_input(3, 0, 0, s->count);
  }
  s->suspended_grid = 0;
 }
 s->active_page = face_visible ? 0 : top;
 if (s->edit_requested) {
  s->suspended_grid = grid;
  hc_retire(s);
  return;
 }
 if (s->suspended_grid == grid) {
  if (RD(grid + 0x1cu) & 1u) s->suspended_grid = 0;
  return;
 }
 if ((s->grid && s->grid != grid) || (!s->overlay && s->hidden)) hc_retire(s);
 if (s->overlay && s->hidden && !(RD(grid + 0x1cu) & 1u)) hc_flag(grid, 1, 1);
 if (s->overlay && s->built == s->count && hc_now() - s->last_scan >= 500u &&
     !chaos_honeycomb_input(13, 0, 0, s->count)) {
  u32 hash;
  s->last_scan = hc_now();
  if (!hc_scan(s, &hash, 0) || hash != s->hash) hc_retire(s);
 }
 if (!s->overlay) {
  u32 hash;
  if ((!face_visible && (RD(grid + 0x1cu) & 1u)) || !hc_scan(s, &hash, 1)) return;
  i32 x = *(volatile i16 *)(grid + 0x14u);
  i32 y = *(volatile i16 *)(grid + 0x16u);
  i32 w = (i32)*(volatile i16 *)(grid + 0x18u) - x + 1;
  i32 h = (i32)*(volatile i16 *)(grid + 0x1au) - y + 1;
  u32 parent = RD(grid + 4u);
  if (w < 240 || w > 336 || h < 240 || h > 480 || !hc_ptr(parent)) return;
  u32 overlay = hc_object(parent);
  if (!overlay) return;
  s->overlay = overlay;
  s->grid = grid;
  s->width = w;
  s->height = h;
  s->origin_x = x;
  s->origin_y = y;
  s->hash = hash;
  s->built = 0;
  s->last_scan = hc_now();
  chaos_honeycomb_input(0, 0, 0, s->count);
  hc_plain(overlay);
  hc_size(overlay, w, h);
  hc_prop(overlay, 0x20, 0xff000000u);
  hc_prop(overlay, 0x21, 255);
  FN(0xc23c8b9u, void(*)(u32,u32,u32,i32,i32))(overlay, grid, 1, 0, 0);
  hc_flag(overlay, HC_INPUT_CHAIN, 0);
  hc_flag(overlay, 1u | 2u | 8192u, 1);
  if (!hc_event(overlay, (u32)hc_ui_event, 0, 0) ||
      !hc_event_once(grid, (u32)hc_ui_event, 35, 0)) {
   hc_retire(s);
   return;
  }
 }
 u32 first = s->built;
 u32 batch = first == 0 && !face_visible ? 19u : 6u;
 if (first < s->count && (!s->hidden || !chaos_honeycomb_input(13, 0, 0, s->count))) {
  u32 hash;
  if (first && (!hc_scan(s, &hash, 0) || hash != s->hash)) {
   hc_retire(s);
   return;
  }
  for (u32 work = 0; work < batch && s->built < s->count; ++work) {
   if (!hc_add_icon(s, s->built)) {
    hc_retire(s);
    s->suspended_grid = grid;
    return;
   }
   ++s->built;
  }
 }
 if (first != s->built) hc_update_frames(s);
 if (!face_visible && !s->hidden && s->built) {
  hc_flag(s->grid, 1, 1);
  s->hidden = 1;
  hc_flag(s->overlay, 1, 0);
 }
 if (s->hidden && !s->motion_timer) {
  s->dirty |= chaos_honeycomb_input(11, 0, 0, s->count);
  if (s->dirty) {
   s->dirty = 0;
   hc_update_frames(s);
  }
 }
}

/* The N67 launcher descriptor's on_create slot is writable. Resolve the live
 * descriptor by key and verify the exact stock callback before replacing it.
 */
static void hc_prepare_entry(u32 page, u32 root) {
 hc_State *s = hc_state();
 if (s->enabled && page == s->entry_page && hc_ptr(root) &&
     root == RD(0x200cae00u)) {
  FN(0xc23c881u, void(*)(u32))(root);
  hc_update(1, page, root);
 }
}

static u32 hc_launcher_create(u32 page, u32 root, u32 data) {
 u32 result = FN(0xc2a31d5u, u32(*)(u32,u32,u32))(page, root, data);
 hc_prepare_entry(page, root);
 return result;
}

static u32 hc_launcher_resume(u32 page) {
 u32 result = FN(0xc29eff9u, u32(*)(u32))(page);
 if (hc_ptr(page) && page == hc_state()->entry_page)
  hc_prepare_entry(page, RD(page + 0x2cu));
 return result;
}

/* N67 page-manager swipe dispatch passes msg+4 to descriptor+0x64.
 * A nonzero result at 0xc44d738 consumes the request before it pops a page.
 * msg+0xc (request+8) == 0x36 is the stock animated swipe-back request.
 */
static u32 hc_launcher_back(u32 page, u32 request) {
 hc_State *s = hc_state();
 if (s->enabled && s->hidden && hc_ptr(s->overlay) &&
     page == s->entry_page && page == s->active_page &&
     hc_ptr(request) && hc_ptr(request + 8u) &&
     *(volatile u8 *)(request + 8u) == 0x36u &&
     !s->allow_back) return 1;
 return FN(0xc2a4f55u, u32(*)(u32,u32))(page, request);
}

static void hc_bind_entry(hc_State *s, u32 enabled) {
 if (enabled && s->entry_page) return;
 if (!enabled && !s->entry_page) return;
 u32 page = FN(0xc448749u, u32(*)(u32))(0x100000u);
 if (!hc_ptr(page) || !hc_ptr(page + 0x64u) || RD(page + 0x14u) != 0x100000u) return;
 u32 callback = (u32)hc_launcher_create | 1u;
 u32 resume = (u32)hc_launcher_resume | 1u;
 u32 back = (u32)hc_launcher_back | 1u;
 if (enabled && RD(page + 0x48u) == 0xc2a31d5u) {
  s->entry_page = page;
  RD(page + 0x48u) = callback;
  if (RD(page + 0x4cu) == 0xc29eff9u) RD(page + 0x4cu) = resume;
  if (RD(page + 0x64u) == 0xc2a4f55u) RD(page + 0x64u) = back;
 } else if (!enabled && page == s->entry_page) {
  if (RD(page + 0x48u) == callback) RD(page + 0x48u) = 0xc2a31d5u;
  if (RD(page + 0x4cu) == resume) RD(page + 0x4cu) = 0xc29eff9u;
  if (RD(page + 0x64u) == back) RD(page + 0x64u) = 0xc2a4f55u;
  s->entry_page = 0;
 }
}

void chaos_honeycomb_update(u32 enabled) {
 hc_State *s = hc_state();
 s->enabled = enabled;
 hc_bind_entry(s, enabled);
 hc_update(enabled, 0, 0);
}
