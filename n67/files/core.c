/* N67 File Manager. All firmware/self pointers and strings are loader-owned.
 * No globals, static string literals, or address-of-function relocations.
 * File jobs run in a separate task. Only the UI timer touches LVGL.
 * Terminal uses named RAM FIFOs and an NSH session, not shell redirection.
 */
typedef signed long long s64;
typedef unsigned long long u64;
#define FM_MAGIC 0x314D464Eu
#define FM_ROWS 44u
#define FM_LIST_ROWS 12u
#define FM_ROW_HEIGHT 60u
#define FM_PARENT_TYPE 0x100u
#define FM_PATH 512u
#define FM_EDIT 32768u
#define FM_TERM 16384u
#define FM_STATE_MAX 0x18000u
enum { M_READY, M_BUSY, M_ERROR, M_FILES, M_TERMINAL, M_BACK, M_REFRESH,
 M_MORE, M_PREV, M_NEXT, M_NEWFILE, M_NEWDIR, M_PASTE, M_PATH, M_VIEW,
 M_EDIT, M_SHELL, M_LUA, M_COPY, M_MOVE, M_RENAME, M_DELETE, M_SAVE,
 M_SAVED, M_UNSAVED, M_CONFIRM, M_BIG, M_BINARY, M_READONLY, M_CONFLICT,
 M_EMPTY, M_HEX, M_TEXT, M_INPUT, M_INTERRUPT, M_CLEAR, M_HISTORY,
 M_SEND, M_SPACE, M_BACKSPACE, M_ENTER, M_DONE, M_BANK, M_LEFT, M_RIGHT,
 M_NAME, M_DEST, M_DIR, M_FILE, M_COPIED, M_DELETED, M_RENAMED, M_CREATED,
 M_RUNNING, M_STOPPED, M_FAILED, M_START, M_END, M_CHARSET,
 M_FIFO_IN, M_FIFO_OUT, M_PROC, M_STATUS, M_PARENT, M_PART,
 M_LOWER, M_UPPER, M_SYMBOL1, M_SYMBOL2, M_CLIP_EMPTY, M_NO_SCRIPT,
 M_EOF, M_CANCEL, M_SELECTED, M_PIPE_IN, M_PIPE_OUT, M_OPEN_IN, M_OPEN_OUT,
 M_STDIO, M_CONSOLE, M_COMMAND, M_RESET, M_SWIPE, M_IMAGE, M_INFO,
 M_IMAGE_FAIL, M_IMAGE_BIG, M_JSON, M_CSV, M_CONFIG, M_MARKDOWN, M_HTML,
 M_XML, M_PNG, M_JPEG, M_BMP, M_GIF, M_LVGL, M_SOURCE, M_UPDIR, M_ROOT, M_COUNT };
enum { V_FILES, V_FILE, V_VIEW, V_EDIT, V_PROMPT, V_TERM, V_IMAGE, V_INFO };
enum { J_LIST=1, J_PAGE, J_LOAD, J_SAVE, J_COPY, J_MOVE, J_DELETE,
 J_NEWFILE, J_NEWDIR, J_FIFO, J_STOP, J_INTERRUPT, J_INSPECT, J_BITMAP };
enum { P_PATH=1, P_NEWFILE, P_NEWDIR, P_RENAME, P_MOVE, P_COMMAND };
typedef struct { u32 type; u64 size; u8 name[256]; } fm_entry_t;
typedef struct {
 /* Loader ABI: 38 words, before mutable state. */
 u32 magic, timer_create, timer_cb, event_add, event_cb, task_create, worker_cb,
 term_cb, page_back, tick_get, clear_flags, gesture_flags, press_lock, messages,
 font_create, font_name, open, close, read, write, seek, stat, rename, unlink,
 mkdir, rmdir, opendir, readdir, closedir, sync, mkfifo, files_dup2,
 current_tcb_w, nsh_main, kill, errno_ptr, state_size, abi;
 /* v3 extensions: fixed firmware ABI, never Lua object ownership. */
 u32 indev_w, gesture_event, dir_top, dir_bottom, image_create, image_src,
 image_info, image_zoom, allocate;
 u32 scroll_get_y, scroll_to_y, scroll_dir, set_parent, scroll_begin, scroll_momentum;
 u32 indev_point;
 u32 initialized, timer, view, previous, dirty, build_index, now;
 u32 objects[FM_ROWS], labels[FM_ROWS], contexts[FM_ROWS][2];
 u8 captions[FM_ROWS][256];
 u32 selected, skip, total, count, clipboard, clip_move;
 u8 cwd[FM_PATH], path[FM_PATH], clip[FM_PATH], input[FM_PATH];
 u32 prompt, input_len, input_cursor, bank, touch, editing, modified, key_repeat, repeat_at;
 u32 edit_len, cursor, original_len, original_hash, new_file;
 u32 page_offset, page_len, visible_bytes, page_history[64], page_history_n;
 u32 hex, confirm, confirm_until, message, error, small_font, key_font, detail_font;
 u32 heading, page_indicator, details[FM_LIST_ROWS];
 u8 metadata[FM_LIST_ROWS][96];
 u8 edit[FM_EDIT+1], page[515], display[4096], title[256];
 fm_entry_t entries[FM_LIST_ROWS];
 /* Immutable request until worker publishes job_state=2. */
 volatile u32 job_state, job_kind;
 u32 job_skip, job_offset, job_pid, job_ret, job_message, job_type;
 u8 request[FM_PATH], destination[FM_PATH], temp[FM_PATH], worker_name[12];
 u8 io[2048];
 /* FIFO descriptors belong to the UI task, never to a file worker. */
 s32 term_in, term_out;
 volatile u32 term_state;
 u32 term_pid, term_pending, term_send_at, term_send_len, term_len, term_scroll, term_view_bytes;
 u32 stop_requested, pending_script, history_n, history_i, ansi, discard;
 /* Owned pseudo-FS pipe devices are reused for this resident app's lifetime.
  * Never unlink an existing path belonging to another instance. */
 u32 fifo_sequence, fifo_owned;
 volatile u32 term_error, term_stage;
 u8 fifo_in[64], fifo_out[64];
 u8 terminal[FM_TERM+1], command[256], send[512], terminal_name[12], script_path[FM_PATH];
 u8 history[8][256];
 u32 gesture_context[2], swipe_block, row_hold, reset_pending, format, detected, image,
 image_width, image_height, image_ready, image_buffer, image_descriptor[3];
 u64 file_size;
 u8 image_path[FM_PATH+3];
 u32 viewport, spacer, scroll_label, scroll_context[2], scroll_view, scroll_base,
 content_lines, line_height, scroll_sync, list_window, term_follow, text_window;
 s32 list_y, text_y, term_y, press_y;
 u32 render_line, render_lines, view_anchor, anchor_pixel, row_parent;
 u32 selected_type, listing_generation, press_generation, press_action, press_type, job_view;
 u8 press_path[FM_PATH];
 u32 caret, caret_x, caret_y, editor_top, editor_lines, file_font;
 u16 glyph_widths[128];
 s32 editor_y, text_press_x, text_press_y;
 u32 caret_follow, editor_prefix, text_pressed, scroll_apply;
} fm_t;
typedef char fm_state_fits[sizeof(fm_t)<=FM_STATE_MAX?1:-1];
typedef char fm_ui_abi[sizeof(bt_ui_t)==0x88u?1:-1];

static void fm_barrier(void) {
#ifndef BT_HOST_TEST
 __asm__ volatile("dmb" ::: "memory");
#endif
}
static fm_t *fm_state(bt_ui_t *u) {
 fm_t *a=u ? (fm_t *)u->runtime:0;
 return a && a->magic==FM_MAGIC && a->abi==1u && a->state_size>=sizeof(fm_t) ? a:0;
}
u32 bt_install_check(u32 find,u32 id) {
 u32 ready=bt_registry_ready();if(ready)return ready;
 if(find!=0x0c43fa01u || id!=0xe7b2u)return 29;
 return ((u32 (*)(u32))find)(id);
}
static bt_ui_t *fm_ui(u32 *p) {
 bt_ui_t *u=p ? (bt_ui_t *)p[1]:0;
 return u && u->magic==BT_UI_MAGIC && u->page==(u32)p ? u:0;
}
static u32 fm_msg(fm_t *a,u32 n) { return a && a->messages && n<M_COUNT ? ((u32 *)a->messages)[n]:0; }
static u32 fm_len(const u8 *s) {u32 n=0; if(s) while(s[n]) n++; return n;}
static u32 fm_copy(u8 *d,u32 cap,const u8 *s) {
 u32 n=fm_len(s); if(!cap || n>=cap) return 0;
 for(u32 i=0;i<=n;i++) d[i]=s[i]; return 1;
}
static u32 fm_cat(u8 *d,u32 at,u32 cap,const u8 *s) {
 if(s) for(u32 i=0;s[i] && at+1<cap;i++) d[at++]=s[i]; d[at]=0; return at;
}
static u32 fm_num(u8 *d,u32 at,u32 cap,u32 n) {
 u8 t[10];u32 k=0;do{t[k++]=(u8)('0'+n%10);n/=10;}while(n);
 while(k && at+1<cap)d[at++]=t[--k];d[at]=0;return at;
}
static u32 fm_same(const u8 *a,const u8 *b) {u32 i=0;while(a[i] && a[i]==b[i])i++;return a[i]==b[i];}
static u32 fm_errno(fm_t *a) {return *(u32 *)((u32 (*)(void))a->errno_ptr)();}
static void fm_errno_clear(fm_t *a) {*(u32 *)((u32 (*)(void))a->errno_ptr)()=0;}
static void fm_notice(fm_t *a,u32 msg,u32 error) {a->message=msg;a->error=error;a->dirty=1;}
static u32 fm_join(u8 *out,const u8 *dir,const u8 *name) {
 u32 p=0,n=fm_len(name);if(!n || n>=FM_PATH)return 0;
 if(name[0]!='/') {if(!fm_copy(out,FM_PATH,dir))return 0;p=fm_len(out);if(p>1)out[p++]='/';}
 for(u32 i=0;i<n;i++)if(name[i]=='\n' || name[i]=='\r')return 0;
 if(p+n>=FM_PATH)return 0;
 for(u32 i=0;i<=n;i++)out[p+i]=name[i];
 /* Lexical normalization; OS still resolves symlinks. Do not truncate. */
 u8 tmp[FM_PATH];u32 w=1,i=0;tmp[0]='/';
 while(out[i]) {
  while(out[i]=='/')i++;u32 s=i;while(out[i] && out[i]!='/')i++;u32 l=i-s;if(!l)break;
  if(l==1 && out[s]=='.')continue;
  if(l==2 && out[s]=='.' && out[s+1]=='.') {while(w>1 && tmp[w-1]!='/')w--;if(w>1)w--;continue;}
  if(w>1)tmp[w++]='/';for(u32 j=0;j<l;j++)tmp[w++]=out[s+j];
 }
 tmp[w]=0;return fm_copy(out,FM_PATH,tmp);
}
static u32 fm_prev(const u8 *s,u32 p) {if(p)p--;while(p && (s[p]&0xC0)==0x80)p--;return p;}
static u32 fm_next(const u8 *s,u32 p,u32 n) {if(p<n)p++;while(p<n && (s[p]&0xC0)==0x80)p++;return p;}
static u32 fm_utf8(const u8 *s,u32 n) {
 for(u32 i=0;i<n;) {
  u32 c=s[i++],k=0,v=0,min=0;
  if(c<128) {if(c==0 || (c<32 && c!=9 && c!=10 && c!=13))return 0;continue;}
  if(c>=0xC2 && c<=0xDF){k=1;v=c&31;min=128;}
  else if(c>=0xE0 && c<=0xEF){k=2;v=c&15;min=2048;}
  else if(c>=0xF0 && c<=0xF4){k=3;v=c&7;min=65536;}else return 0;
  if(i+k>n)return 0;while(k--){c=s[i++];if((c&0xC0)!=0x80)return 0;v=(v<<6)|(c&63);}
  if(v<min || v>0x10FFFF || (v>=0xD800 && v<=0xDFFF))return 0;
 }return 1;
}
static u32 fm_insert(u8 *s,u32 *n,u32 *cursor,u32 cap,const u8 *v,u32 size) {
 if(*cursor>*n || *n+size>=cap)return 0;
 for(u32 i=*n+1;i>*cursor;i--)s[i+size-1]=s[i-1];
 for(u32 i=0;i<size;i++)s[(*cursor)++]=v[i];*n+=size;return 1;
}
static void fm_backspace(u8 *s,u32 *n,u32 *cursor) {
 if(!*cursor)return;u32 p=fm_prev(s,*cursor),d=*cursor-p;
 for(u32 i=*cursor;i<=*n;i++)s[i-d]=s[i];*n-=d;*cursor=p;
}
static u32 fm_hash(u32 h,const u8 *s,u32 n) {for(u32 i=0;i<n;i++)h=(h^s[i])*16777619u;return h;}
static s32 fm_open(fm_t *a,const u8 *p,u32 flags,u32 mode) {return ((s32 (*)(u32,u32,u32))a->open)((u32)p,flags,mode);}
static s32 fm_close(fm_t *a,s32 fd) {return ((s32 (*)(s32))a->close)(fd);}
static s32 fm_read(fm_t *a,s32 fd,u8 *p,u32 n) {return ((s32 (*)(s32,u32,u32))a->read)(fd,(u32)p,n);}
static s32 fm_write(fm_t *a,s32 fd,const u8 *p,u32 n) {return ((s32 (*)(s32,u32,u32))a->write)(fd,(u32)p,n);}
static s64 fm_seek(fm_t *a,s32 fd,s64 n,u32 whence) {return ((s64 (*)(s32,s64,u32))a->seek)(fd,n,whence);}
static s32 fm_stat(fm_t *a,const u8 *p,u32 *mode,u64 *size) {
 u32 b[24];s32 r=((s32 (*)(u32,u32))a->stat)((u32)p,(u32)b);
 if(r>=0){if(mode)*mode=b[2];if(size)*size=((u64)b[7]<<32)|b[6];}return r;
}
static u32 fm_write_all(fm_t *a,s32 fd,const u8 *p,u32 n) {
 u32 at=0;while(at<n){s32 r=fm_write(a,fd,p+at,n-at);if(r<0 && fm_errno(a)==4)continue;if(r<=0)return 0;at+=(u32)r;}return 1;
}
static u32 fm_file_hash(fm_t *a,const u8 *path,u32 *size,u32 *hash) {
 s32 fd=fm_open(a,path,1u|0x40u,0);if(fd<0)return 0;
 u32 n=0,h=2166136261u; s32 r;
 while((r=fm_read(a,fd,a->io,sizeof(a->io)))!=0) {
  if(r<0){if(fm_errno(a)==4)continue;fm_close(a,fd);return 0;}
  if(n+(u32)r>FM_EDIT){fm_close(a,fd);return 0;}n+=r;h=fm_hash(h,a->io,r);
 }
 fm_close(a,fd);*size=n;*hash=h;return 1;
}
static void fm_list_job(fm_t *a) {
 u32 dir=((u32 (*)(u32))a->opendir)((u32)a->request),n=1;
 if(!dir)return;
 a->count=0;
 if(!a->job_skip){fm_entry_t *t=&a->entries[a->count++];t->type=FM_PARENT_TYPE;t->size=0;
  t->name[0]='.';t->name[1]='.';t->name[2]=0;}
 for(;;) {
  fm_errno_clear(a);
  u8 *e=(u8 *)((u32 (*)(u32))a->readdir)(dir);if(!e)break;
  const u8 *name=e+1;
  if(name[0]=='.' && (!name[1] || (name[1]=='.' && !name[2])))continue;
  if(n>=a->job_skip && a->count<FM_LIST_ROWS) {
   fm_entry_t *t=&a->entries[a->count++];t->type=e[0];t->size=0;
   if(!fm_copy(t->name,sizeof(t->name),name)){t->name[0]=0;a->count--;}
   else {u8 path[FM_PATH];u32 mode;
    if(fm_join(path,a->request,t->name) && fm_stat(a,path,&mode,&t->size)>=0)
      t->type=e[0]==10?10u:(mode&0xF000u)==0x4000u?4u:(mode&0xF000u)==0x8000u?8u:0u;
   }
  }n++;
 }
 u32 error=fm_errno(a);((s32 (*)(u32))a->closedir)(dir);
 if(error){a->job_ret=error;return;}a->total=n;a->job_ret=0;a->job_message=n>1?M_READY:M_EMPTY;
}
static u32 fm_le32(const u8 *p) {return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
static u32 fm_be32(const u8 *p) {return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static u32 fm_extension(const u8 *path) {
 u32 at=0;for(u32 i=0;path[i];i++){if(path[i]=='/')at=0;else if(path[i]=='.')at=i+1;}
 u32 out=0,n=0;if(!at)return 0;
 while(path[at] && n<4){u32 c=path[at++];if(c>='A' && c<='Z')c+=32;out|=c<<(n++*8);}
 return path[at]?0:out;
}
static u32 fm_format(fm_t *a) {
 const u8 *p=a->page;u32 n=a->page_len,e=fm_extension(a->request);
 a->image_width=a->image_height=0;
 if(n>=24 && fm_be32(p)==0x89504e47u && fm_be32(p+4)==0x0d0a1a0au && fm_be32(p+12)==0x49484452u){
  a->image_width=fm_be32(p+16);a->image_height=fm_be32(p+20);return M_PNG;}
 if(n>=3 && p[0]==255 && p[1]==216 && p[2]==255)return M_JPEG;
 if(n>=54 && p[0]=='B' && p[1]=='M'){
  a->image_width=fm_le32(p+18);s32 h=(s32)fm_le32(p+22);a->image_height=h<0?(u32)-(s64)h:(u32)h;return M_BMP;}
 if(n>=10 && p[0]=='G' && p[1]=='I' && p[2]=='F' && p[3]=='8' && p[5]=='a'){
  a->image_width=p[6]|((u32)p[7]<<8);a->image_height=p[8]|((u32)p[9]<<8);return M_GIF;}
 if(e==0x006e6962u && n>=4){u32 h=fm_le32(p),w=(h>>10)&2047,ht=h>>21;
  if(!(h&0x3e0u) && (h&31)>=4 && (h&31)<=6 && w && ht && (u64)w*ht*4+4==a->file_size){
   a->image_width=w;a->image_height=ht;return M_LVGL;}}
 u32 text_n=n;
 if(n==512 && a->file_size>n && !fm_utf8(p,n)){
  u32 start=n-1;while(start && (p[start]&0xc0)==0x80)start--;
  u32 c=p[start],need=c>=0xc2 && c<=0xdf?2:c>=0xe0 && c<=0xef?3:c>=0xf0 && c<=0xf4?4:1;
  if(need>n-start){u32 partial=1;for(u32 i=start+1;i<n;i++)if((p[i]&0xc0)!=0x80)partial=0;
   if(partial)text_n=start;}
 }
 if(!fm_utf8(p,text_n) || (n && !text_n))return M_HEX;
 if(e==0x6e6f736au)return M_JSON;
 if(e==0x00767363u || e==0x00767374u)return M_CSV;
 if(e==0x00696e69u || e==0x00676663u || e==0x666e6f63u || e==0x00676f6cu || e==0x6c6d6f74u || e==0x6c6d6179u || e==0x006c6d79u)return M_CONFIG;
 if(e==0x0000646du)return M_MARKDOWN;
 if(e==0x6c6d7468u || e==0x006d7468u)return M_HTML;
 if(e==0x006c6d78u)return M_XML;
 return M_TEXT;
}
static void fm_inspect_job(fm_t *a) {
 u32 mode;u64 size;
 if(fm_stat(a,a->request,&mode,&size)<0)return;
 if((mode&0xf000u)!=0x8000u){a->job_message=M_READONLY;return;}
 s32 fd=fm_open(a,a->request,1u|0x40u,0);if(fd<0)return;
 u32 n=0;while(n<512){s32 r=fm_read(a,fd,a->page+n,512-n);
  if(r<0 && fm_errno(a)==4)continue;if(r<0){fm_close(a,fd);return;}if(!r)break;n+=r;}
 fm_close(a,fd);a->page[n]=0;a->page_len=n;a->file_size=size;
 a->format=fm_format(a);a->detected=1;a->image_ready=0;
 a->job_ret=0;a->job_message=M_READY;
}
static void fm_bitmap_job(fm_t *a) {
 /* Decode uncompressed 24/32-bit BMP in the file worker, fitted to the screen.
  * No LVGL call here. A single bounded buffer is reused for this resident app. */
 u8 h[54];s32 fd=fm_open(a,a->request,1u|0x40u,0);if(fd<0)return;
 u32 n=0;while(n<54){s32 r=fm_read(a,fd,h+n,54-n);if(r<0 && fm_errno(a)==4)continue;if(r<=0){fm_close(a,fd);return;}n+=r;}
 u32 w=fm_le32(h+18),offset=fm_le32(h+10),bits=h[28]|((u32)h[29]<<8),stride=((w*bits+31)/32)*4;
 s32 signed_height=(s32)fm_le32(h+22);u32 height=signed_height<0?(u32)-(s64)signed_height:(u32)signed_height;
 if(h[0]!='B' || h[1]!='M' || fm_le32(h+14)!=40 || h[26]!=1 || h[27] ||
    (bits!=24 && bits!=32) || fm_le32(h+30)!=0 || !w || !height || w>512 || height>512 ||
    offset<54 || (u64)offset+(u64)stride*height>a->file_size){fm_close(a,fd);a->job_message=M_IMAGE_FAIL;return;}
 if(!a->image_buffer)a->image_buffer=((u32 (*)(u32))a->allocate)(308u*280u*4u);
 if(!a->image_buffer){fm_close(a,fd);a->job_ret=12;return;}
 u32 out_w=w,out_h=height;
 if(out_w>308){out_h=height*308/w;out_w=308;}if(out_h>256){out_w=w*256/height;out_h=256;}
 if(!out_w)out_w=1;if(!out_h)out_h=1;
 for(u32 y=0;y<out_h;y++){
  u32 sy=y*height/out_h;if(signed_height>0)sy=height-1-sy;
  if(fm_seek(a,fd,(s64)offset+(s64)sy*stride,0)<0){fm_close(a,fd);return;}
  u32 at=0;while(at<stride){s32 r=fm_read(a,fd,a->io+at,stride-at);if(r<0 && fm_errno(a)==4)continue;
   if(r<=0){fm_close(a,fd);return;}at+=r;}
  for(u32 x=0;x<out_w;x++){u8 *pixel=a->io+(x*w/out_w)*(bits/8);
   ((u32 *)a->image_buffer)[y*out_w+x]=0xff000000u|pixel[0]|((u32)pixel[1]<<8)|((u32)pixel[2]<<16);}
 }
 fm_close(a,fd);a->image_descriptor[0]=5u|(out_w<<10)|(out_h<<21);
 a->image_descriptor[1]=out_w*out_h*4;a->image_descriptor[2]=a->image_buffer;
 a->image_ready=1;a->job_ret=0;a->job_message=M_IMAGE;
}
static void fm_load_job(fm_t *a,u32 edit) {
 u32 mode;u64 size;
 if(fm_stat(a,a->request,&mode,&size)<0)return;
 if((mode&0xF000u)!=0x8000u){a->job_message=M_READONLY;return;}
 if(edit && size>FM_EDIT){a->job_message=M_BIG;return;}
 if(!edit && size>0xffffffffu){a->job_message=M_BIG;return;}
 s32 fd=fm_open(a,a->request,1u|0x40u,0);if(fd<0)return;
 u8 *dst=a->edit;u32 cap=FM_EDIT,n=0;
 if(!edit && fm_seek(a,fd,a->job_offset,0)<0){fm_close(a,fd);return;}
 while(n<cap) {s32 r=fm_read(a,fd,dst+n,cap-n);if(r==0)break;
  if(r<0){if(fm_errno(a)==4)continue;fm_close(a,fd);return;}n+=r;}
 if(edit && n==cap){u8 extra;s32 more;do{more=fm_read(a,fd,&extra,1);}while(more<0 && fm_errno(a)==4);
  if(more!=0){fm_close(a,fd);a->job_message=more>0?M_BIG:M_ERROR;return;}}
 fm_close(a,fd);dst[n]=0;
 if(edit) {
  if(!fm_utf8(dst,n)){a->job_message=M_BINARY;return;}
  a->edit_len=n;a->cursor=0;a->original_len=n;a->original_hash=fm_hash(2166136261u,dst,n);
  a->modified=0;a->new_file=0;a->editing=1;
 }else {a->page_len=n;a->file_size=size;a->editing=0;}
 a->job_ret=0;a->job_message=n?M_READY:M_EOF;
}
static u32 fm_temp(fm_t *a) {
 u32 n=fm_len(a->destination);
 if(n+40>=FM_PATH || !fm_copy(a->temp,FM_PATH,a->destination))return 0;
 n=fm_cat(a->temp,n,FM_PATH,(u8 *)fm_msg(a,M_PART));
 fm_num(a->temp,n,FM_PATH,a->now);return 1;
}
static void fm_save_job(fm_t *a) {
 u32 mode=0666,n,h;u64 size;
 s32 exists=fm_stat(a,a->destination,&mode,&size);
 if(a->new_file) {if(exists>=0){a->job_message=M_CONFLICT;return;}if(fm_errno(a)!=2)return;}
 else if(exists<0 || (mode&0xF000u)!=0x8000u ||
  !fm_file_hash(a,a->destination,&n,&h) || n!=a->original_len || h!=a->original_hash) {
  a->job_message=M_CONFLICT;return;
 }
 if(!fm_temp(a))return;
 s32 fd=fm_open(a,a->temp,2u|4u|8u,mode&0777u);if(fd<0)return;
 u32 ok=fm_write_all(a,fd,a->edit,a->edit_len);
 if(ok && ((s32 (*)(s32))a->sync)(fd)<0)ok=0;
 if(fm_close(a,fd)<0)ok=0;
 if(ok && !a->new_file && (!fm_file_hash(a,a->destination,&n,&h) || n!=a->original_len || h!=a->original_hash)){
  ok=0;a->job_message=M_CONFLICT;
 }
 if(ok && ((s32 (*)(u32,u32))a->rename)((u32)a->temp,(u32)a->destination)>=0) {
  a->modified=0;a->new_file=0;a->original_len=a->edit_len;
  a->original_hash=fm_hash(2166136261u,a->edit,a->edit_len);a->job_ret=0;a->job_message=M_SAVED;
 }else ((s32 (*)(u32))a->unlink)((u32)a->temp);
}
static void fm_copy_job(fm_t *a) {
 u32 mode;u64 size;
 if(fm_stat(a,a->request,&mode,&size)<0 || (mode&0xF000u)!=0x8000u)return;
 if(fm_stat(a,a->destination,0,0)>=0){a->job_message=M_CONFLICT;return;}
 if(fm_errno(a)!=2 || !fm_temp(a))return;
 s32 src=fm_open(a,a->request,1u|0x40u,0);if(src<0)return;
 s32 dst=fm_open(a,a->temp,2u|4u|8u,mode&0777u);if(dst<0){fm_close(a,src);return;}
 u32 ok=1;for(;;){s32 r=fm_read(a,src,a->io,sizeof(a->io));if(!r)break;
  if(r<0){if(fm_errno(a)==4)continue;ok=0;break;}
  if(!fm_write_all(a,dst,a->io,r)){ok=0;break;}}
 fm_close(a,src);if(ok && ((s32 (*)(s32))a->sync)(dst)<0)ok=0;if(fm_close(a,dst)<0)ok=0;
 if(ok && fm_stat(a,a->destination,0,0)>=0){ok=0;a->job_message=M_CONFLICT;}
 else if(ok && fm_errno(a)!=2)ok=0;
 if(ok && ((s32 (*)(u32,u32))a->rename)((u32)a->temp,(u32)a->destination)>=0) {
  a->job_ret=0;a->job_message=M_COPIED;
 }else ((s32 (*)(u32))a->unlink)((u32)a->temp);
}
/* Directory walks are bounded to 16 levels and 511-byte paths. File I/O keeps
 * the same 2 KiB streaming buffer. Symlinks are never traversed in a walk. */
static u32 fm_remove_tree(fm_t *a,u8 *path,u32 depth,u32 dry) {
 if(depth>=16){a->job_message=M_BIG;return 0;}
 u32 len=fm_len(path),dir=((u32 (*)(u32))a->opendir)((u32)path);if(!dir)return 0;
 u32 ok=1,error=0;
 for(;;){fm_errno_clear(a);u8 *e=(u8 *)((u32 (*)(u32))a->readdir)(dir);
  if(!e){error=fm_errno(a);if(error)ok=0;break;}
  u8 *name=e+1;if(name[0]=='.' && (!name[1] || (name[1]=='.' && !name[2])))continue;
  u32 type=e[0];if(!fm_join(path,path,name)){a->job_message=M_BIG;ok=0;break;}
  if(type==4)ok=fm_remove_tree(a,path,depth+1,dry);
  else if(type==8 || type==10 || type==1 || type==2 || type==6) {
   if(!dry && ((s32 (*)(u32))a->unlink)((u32)path)<0)ok=0;
  }else {a->job_message=M_READONLY;ok=0;}
  path[len]=0;if(!ok){error=fm_errno(a);break;}
 }
 path[len]=0;((s32 (*)(u32))a->closedir)(dir);
 if(ok && !dry && ((s32 (*)(u32))a->rmdir)((u32)path)<0){ok=0;error=fm_errno(a);}
 if(error)*(u32 *)((u32 (*)(void))a->errno_ptr)()=error;return ok;
}
static u32 fm_copy_contents(fm_t *a,u32 depth) {
 if(depth>=16){a->job_message=M_BIG;return 0;}
 u32 src_len=fm_len(a->request),dst_len=fm_len(a->destination);
 u32 dir=((u32 (*)(u32))a->opendir)((u32)a->request);if(!dir)return 0;
 u32 ok=1,error=0;
 for(;;){fm_errno_clear(a);u8 *e=(u8 *)((u32 (*)(u32))a->readdir)(dir);
  if(!e){error=fm_errno(a);if(error)ok=0;break;}
  u8 *name=e+1;if(name[0]=='.' && (!name[1] || (name[1]=='.' && !name[2])))continue;
  u32 type=e[0];
  if(!fm_join(a->request,a->request,name) || !fm_join(a->destination,a->destination,name)){
   a->job_message=M_BIG;ok=0;
  }else if(type==4){u32 mode;
   if(depth+1>=16){a->job_message=M_BIG;ok=0;}
   else if(fm_stat(a,a->request,&mode,0)<0 || ((s32 (*)(u32,u32))a->mkdir)((u32)a->destination,mode&0777u)<0)ok=0;
   else ok=fm_copy_contents(a,depth+1);
  }else if(type==8){a->job_ret=1;fm_copy_job(a);ok=a->job_ret==0;}
  else {a->job_message=M_READONLY;ok=0;}
  a->request[src_len]=0;a->destination[dst_len]=0;
  if(!ok){error=fm_errno(a);break;}
 }
 a->request[src_len]=0;a->destination[dst_len]=0;((s32 (*)(u32))a->closedir)(dir);
 if(error)*(u32 *)((u32 (*)(void))a->errno_ptr)()=error;return ok;
}
static void fm_copy_tree(fm_t *a) {
 if(a->job_type==10){a->job_message=M_READONLY;return;}
 u32 mode;if(fm_stat(a,a->request,&mode,0)<0)return;
 if((mode&0xF000u)!=0x4000u){fm_copy_job(a);return;}
 u32 n=fm_len(a->request),i=0;while(i<n && a->destination[i]==a->request[i])i++;
 if((n==1 && a->request[0]=='/') || (i==n && (!a->destination[i] || a->destination[i]=='/'))){a->job_message=M_CONFLICT;return;}
 if(fm_stat(a,a->destination,0,0)>=0){a->job_message=M_CONFLICT;return;}
 if(fm_errno(a)!=2 || !fm_temp(a))return;
 u8 original[FM_PATH];fm_copy(original,FM_PATH,a->destination);
 if(((s32 (*)(u32,u32))a->mkdir)((u32)a->temp,mode&0777u)<0)return;
 fm_copy(a->destination,FM_PATH,a->temp);
 u32 ok=fm_copy_contents(a,0);u32 error=fm_errno(a);
 if(ok && ((s32 (*)(u32,u32))a->rename)((u32)a->destination,(u32)original)>=0){
  a->job_ret=0;a->job_message=M_COPIED;
 }else {
  a->job_ret=1;if(!error)error=fm_errno(a);
  /* Only a newly created staging tree is rolled back, never the source. */
  fm_remove_tree(a,a->destination,0,0);
  if(error)*(u32 *)((u32 (*)(void))a->errno_ptr)()=error;
 }
 fm_copy(a->destination,FM_PATH,original);
}
static u32 fm_digits(const u8 *s) {u32 n=0;if(!*s)return 0;while(*s){if(*s<'0'||*s>'9')return 0;n=n*10+*s++-'0';}return n;}
static u32 fm_parent(fm_t *a,u32 pid) {
 u8 path[64],buf[512];u32 p=0;
 p=fm_cat(path,p,sizeof(path),(u8 *)fm_msg(a,M_PROC));if(p+1<sizeof(path))path[p++]='/';
 p=fm_num(path,p,sizeof(path),pid);fm_cat(path,p,sizeof(path),(u8 *)fm_msg(a,M_STATUS));
 s32 fd=fm_open(a,path,1u|0x40u,0);if(fd<0)return 0;s32 n=fm_read(a,fd,buf,511);fm_close(a,fd);if(n<=0)return 0;buf[n]=0;
 u8 *tag=(u8 *)fm_msg(a,M_PARENT);u32 l=fm_len(tag);
 for(u32 i=0;i+l<(u32)n;i++){u32 j=0;while(j<l && buf[i+j]==tag[j])j++;
  if(j==l){i+=l;while(buf[i]==' ' || buf[i]=='\t')i++;u32 v=0;while(buf[i]>='0' && buf[i]<='9')v=v*10+buf[i++]-'0';return v;}}
 return 0;
}
static u32 fm_owned_shell(fm_t *a) {
 u8 path[64],buf[512];u32 p=fm_cat(path,0,sizeof(path),(u8 *)fm_msg(a,M_PROC));
 path[p++]='/';p=fm_num(path,p,sizeof(path),a->term_pid);
 fm_cat(path,p,sizeof(path),(u8 *)fm_msg(a,M_STATUS));
 s32 fd=fm_open(a,path,1u|0x40u,0);if(fd<0)return 0;
 s32 n=fm_read(a,fd,buf,511);fm_close(a,fd);if(n<=0)return 0;buf[n]=0;
 for(u32 i=0;i+5<(u32)n;i++)if((!i || buf[i-1]=='\n') &&
  buf[i]=='N' && buf[i+1]=='a' && buf[i+2]=='m' && buf[i+3]=='e' && buf[i+4]==':') {
  i+=5;while(buf[i]==' ' || buf[i]=='\t')i++;u32 j=0;
  while(buf[i+j] && buf[i+j]!='\n' && buf[i+j]!='\r' && buf[i+j]!=' ' && buf[i+j]!='\t')j++;
  if(j!=fm_len(a->terminal_name))return 0;
  for(u32 k=0;k<j;k++)if(buf[i+k]!=a->terminal_name[k])return 0;return 1;
 }return 0;
}
static void fm_stop_job(fm_t *a,u32 close_shell) {
 if(!a->term_pid || !fm_owned_shell(a)) {
  a->term_state=3;a->job_ret=0;a->job_message=M_STOPPED;return;
 }
 u32 ids[128],parents[128],count=0,owned[129],nowned=1;owned[0]=a->term_pid;
 u32 dir=((u32 (*)(u32))a->opendir)(fm_msg(a,M_PROC));
 if(dir){for(;;){u8 *e=(u8 *)((u32 (*)(u32))a->readdir)(dir);if(!e || count==128)break;
  u32 pid=fm_digits(e+1);if(pid && pid!=a->term_pid){ids[count]=pid;parents[count]=fm_parent(a,pid);count++;}}
  ((s32 (*)(u32))a->closedir)(dir);}
 for(u32 pass=0;pass<count;pass++){u32 added=0;
  for(u32 i=0;i<count;i++)if(ids[i])for(u32 j=0;j<nowned;j++)if(parents[i]==owned[j]) {
   owned[nowned++]=ids[i];ids[i]=0;added=1;break;}
  if(!added)break;
 }
 /* Only descendants of this app's shell. Recheck parent before signalling. */
 for(u32 i=nowned;i>1;i--){u32 pid=owned[i-1],parent=fm_parent(a,pid),valid=0;
  for(u32 j=0;j<nowned;j++)if(parent==owned[j])valid=1;
  if(valid)((s32 (*)(u32,u32))a->kill)(pid,15u);}
 if(close_shell && a->term_pid)((s32 (*)(u32,u32))a->kill)(a->term_pid,15u);
 a->job_ret=0;a->job_message=M_STOPPED;
}
static bt_ui_t *fm_decode(u32 argc,u32 *argv) {
 if(!argc || !argv || !argv[0])return 0;u8 *s=(u8 *)argv[0];if(s[0]!='N'||s[1]!='F')return 0;
 u32 p=0;for(u32 i=2;i<10;i++){u32 v=s[i];if(v>='0'&&v<='9')v-='0';else if(v>='a'&&v<='f')v=v-'a'+10;else return 0;p=(p<<4)|v;}
 if((s[10] && (s[10]!='t' || s[11])) || !bt_valid_ptr(p))return 0;bt_ui_t *u=(bt_ui_t *)p;return fm_state(u)?u:0;
}
static void fm_pipe_path(u8 *path,u32 owner,u32 sequence,u8 end) {
 path[0]='/';path[1]='d';path[2]='e';path[3]='v';path[4]='/';
 path[5]='n';path[6]='f';path[7]='m';
 for(u32 i=0;i<8;i++){u32 v=(owner>>((7-i)*4))&15;path[8+i]=(u8)(v<10?'0'+v:'a'+v-10);}
 path[16]='_';u32 n=fm_num(path,17,64,sequence);path[n++]=end;path[n]=0;
}
static void fm_fifo_job(bt_ui_t *u,fm_t *a) {
 if(a->fifo_owned==3){a->job_ret=0;a->job_message=M_READY;return;}
 if(a->fifo_owned==1){
  a->job_message=M_PIPE_IN;
  if(((s32 (*)(u32))a->unlink)((u32)a->fifo_in)<0){a->job_ret=fm_errno(a);return;}
  a->fifo_owned=0;
 }
 /* mkfifo registers a pipe character driver in this firmware's pseudo FS.
  * /tmp can be a mounted filesystem, where inode_reserve returns EEXIST even
  * for a missing leaf. Its actual ABI is mkfifo(path), with no mode argument. */
 for(u32 attempt=0;attempt<4;attempt++) {
  if(a->fifo_owned){a->job_message=M_PIPE_IN;a->job_ret=16;return;}
  fm_pipe_path(a->fifo_in,(u32)u,++a->fifo_sequence,'i');
  fm_pipe_path(a->fifo_out,(u32)u,a->fifo_sequence,'o');
  a->job_message=M_PIPE_IN;
  if(((s32 (*)(u32))a->mkfifo)((u32)a->fifo_in)<0){a->job_ret=fm_errno(a);if(a->job_ret==17)continue;return;}
  a->fifo_owned=1;a->job_message=M_PIPE_OUT;
  if(((s32 (*)(u32))a->mkfifo)((u32)a->fifo_out)>=0){
   a->fifo_owned=3;a->job_ret=0;a->job_message=M_READY;return;
  }
  u32 error=fm_errno(a);a->job_ret=error;
  if(((s32 (*)(u32))a->unlink)((u32)a->fifo_in)>=0)a->fifo_owned=0;
  /* Restore the useful creation error after rollback calls. */
  *(u32 *)((u32 (*)(void))a->errno_ptr)()=error;
  if(error!=17 || a->fifo_owned)return;
 }
}
u32 bt_app_worker(u32 argc,u32 *argv) {
 bt_ui_t *u=fm_decode(argc,argv);fm_t *a=fm_state(u);if(!a || a->job_state!=1)return 1;
 fm_barrier();a->job_ret=1;a->job_message=M_ERROR;fm_errno_clear(a);
 u32 kind=a->job_kind;
 if(kind==J_LIST)fm_list_job(a);
 else if(kind==J_INSPECT)fm_inspect_job(a);
 else if(kind==J_BITMAP)fm_bitmap_job(a);
 else if(kind==J_PAGE || kind==J_LOAD)fm_load_job(a,kind==J_LOAD);
 else if(kind==J_SAVE)fm_save_job(a);
 else if(kind==J_COPY)fm_copy_tree(a);
 else if(kind==J_MOVE) {
  if(fm_stat(a,a->destination,0,0)>=0)a->job_message=M_CONFLICT;
  else if(fm_errno(a)==2 && ((s32 (*)(u32,u32))a->rename)((u32)a->request,(u32)a->destination)>=0){a->job_ret=0;a->job_message=M_RENAMED;}
 }else if(kind==J_DELETE) {
  u32 mode=0;if(a->job_type==10 || fm_stat(a,a->request,&mode,0)>=0){u32 ok;
   if((mode&0xF000u)==0x4000u && a->job_type!=10)
    ok=fm_remove_tree(a,a->request,0,1) && fm_remove_tree(a,a->request,0,0);
   else ok=((s32 (*)(u32))a->unlink)((u32)a->request)>=0;
   if(ok){a->job_ret=0;a->job_message=M_DELETED;}}
 }else if(kind==J_NEWFILE) {
  s32 fd=fm_open(a,a->destination,2u|4u|8u,0666);if(fd>=0){if(fm_close(a,fd)>=0){a->job_ret=0;a->job_message=M_CREATED;}}
 }else if(kind==J_NEWDIR) {
  if(((s32 (*)(u32,u32))a->mkdir)((u32)a->destination,0777)>=0){a->job_ret=0;a->job_message=M_CREATED;}
 }else if(kind==J_FIFO)fm_fifo_job(u,a);
 else if(kind==J_STOP || kind==J_INTERRUPT)fm_stop_job(a,1);
 if(a->job_ret){u32 error=fm_errno(a);if(error)a->job_ret=error;}
 fm_barrier();a->job_state=2;return 0;
}
static void fm_name(u8 *name,u32 p) {name[0]='N';name[1]='F';for(u32 i=0;i<8;i++){u32 v=(p>>((7-i)*4))&15;name[i+2]=(u8)(v<10?'0'+v:'a'+v-10);}name[10]=0;}
static u32 fm_selected_type(fm_t *a) {return a->selected_type?a->selected_type:a->selected<a->count?a->entries[a->selected].type:0;}
static u32 fm_job(bt_ui_t *u,u32 kind,const u8 *src,const u8 *dst) {
 fm_t *a=fm_state(u);if(!a || a->job_state){if(a)fm_notice(a,M_BUSY,0);return 0;}
 if(src && !fm_copy(a->request,FM_PATH,src))return 0;
 if(dst && !fm_copy(a->destination,FM_PATH,dst))return 0;
 fm_name(a->worker_name,(u32)u);a->job_kind=kind;a->job_skip=a->skip;a->job_offset=a->page_offset;
 a->job_view=a->view;
 a->job_type=kind==J_COPY?a->clipboard:kind==J_DELETE?fm_selected_type(a):0;
 if(kind==J_LIST){a->job_type=a->list_window;a->list_window=0;a->listing_generation++;
  if(!a->job_type){a->skip=a->job_skip=0;a->list_y=0;a->scroll_sync=1;}}
 a->job_state=1;a->job_ret=0;fm_barrier();
 s32 pid=((s32 (*)(u32,u32,u32,u32,u32))a->task_create)((u32)a->worker_name,80,8192,a->worker_cb,0);
 a->job_pid=pid;if(pid<0){a->job_state=0;fm_notice(a,M_FAILED,(u32)-pid);return 0;}
 fm_notice(a,M_BUSY,0);return 1;
}
u32 bt_term_worker(u32 argc,u32 *argv) {
 bt_ui_t *u=fm_decode(argc,argv);fm_t *a=fm_state(u);if(!a)return 1;
 /* task_create clones descriptors. Open blocking ends in this task and change
  * only this task's stdio using the firmware files_dup2(current_tcb,...). */
 s32 in=fm_open(a,a->fifo_in,1,0);
 if(in<0){a->term_error=fm_errno(a);a->term_stage=M_OPEN_IN;fm_barrier();a->term_state=3;return 1;}
 s32 out=fm_open(a,a->fifo_out,2,0);
 if(out<0){a->term_error=fm_errno(a);a->term_stage=M_OPEN_OUT;fm_close(a,in);fm_barrier();a->term_state=3;return 1;}
 u32 tcb=*(volatile u32 *)a->current_tcb_w;
 s32 (*dup)(u32,s32,s32)=(s32 (*)(u32,s32,s32))a->files_dup2;
 s32 result=dup(tcb,in,0);if(result>=0)result=dup(tcb,out,1);if(result>=0)result=dup(tcb,out,2);
 if(result<0){a->term_error=(u32)-result;a->term_stage=M_STDIO;fm_barrier();a->term_state=3;return 1;}
 if(in>2)fm_close(a,in);if(out>2)fm_close(a,out);
 if(a->term_in>2)fm_close(a,a->term_in);if(a->term_out>2)fm_close(a,a->term_out);
 fm_barrier();a->term_state=2;
 /* This entry calls nsh_newconsole+nsh_session; it does not run rcS again. */
 u32 r=((u32 (*)(u32,u32))a->nsh_main)(argc,(u32)argv);
 fm_barrier();a->term_state=3;return r;
}
static void fm_terminal_spawn(bt_ui_t *u) {
 fm_t *a=fm_state(u);a->term_error=a->term_stage=0;a->ansi=0;
 a->term_in=fm_open(a,a->fifo_in,3u|0x40u,0);
 if(a->term_in<0){a->term_error=fm_errno(a);a->term_stage=M_OPEN_IN;a->term_state=3;return;}
 a->term_out=fm_open(a,a->fifo_out,3u|0x40u,0);
 if(a->term_out<0){a->term_error=fm_errno(a);a->term_stage=M_OPEN_OUT;a->term_state=3;return;}
 /* Clear bytes left by a previous console, including unconsumed commands.
  * The UI owns RDWR nonblocking descriptors before the blocking ends open. */
 u8 discard[256];for(u32 i=0;i<8;i++)if(fm_read(a,a->term_in,discard,sizeof(discard))<=0)break;
 for(u32 i=0;i<8;i++)if(fm_read(a,a->term_out,discard,sizeof(discard))<=0)break;
 fm_name(a->terminal_name,(u32)u);a->terminal_name[10]='t';a->terminal_name[11]=0;a->term_state=1;fm_barrier();
 s32 pid=((s32 (*)(u32,u32,u32,u32,u32))a->task_create)((u32)a->terminal_name,80,8192,a->term_cb,0);
 if(pid<0){a->term_error=fm_errno(a);if(!a->term_error)a->term_error=(u32)-pid;
  a->term_stage=M_CONSOLE;a->term_state=3;
 }else {a->term_pid=pid;fm_notice(a,M_RUNNING,0);}
}
static u32 fm_text_scan(fm_t *,const u8 *,u32,u32,u32);
static void fm_terminal_text(fm_t *a,const u8 *buf,u32 n) {
 for(u32 i=0;i<n;i++) {
  u8 c=buf[i];
  if(a->ansi==1){a->ansi=c=='['?2:0;continue;}
  if(a->ansi==2){if(c>=0x40 && c<=0x7e)a->ansi=0;continue;}
  if(c==27){a->ansi=1;continue;}if(c=='\r')continue;
  if(c==8 || c==127){a->term_len=fm_prev(a->terminal,a->term_len);continue;}
  if(c<32 && c!=10 && c!=9)continue;
  if(a->term_len>=FM_TERM){u32 d=1024;while(d<a->term_len && (a->terminal[d]&0xc0)==0x80)d++;
   u32 removed=fm_text_scan(a,a->terminal,d,0,0)-1;
   a->term_y-=(s32)(removed*a->line_height);if(a->term_y<0)a->term_y=0;a->scroll_sync=1;
   for(u32 j=d;j<a->term_len;j++)a->terminal[j-d]=a->terminal[j];a->term_len-=d;a->discard+=d;}
  a->terminal[a->term_len++]=c;
 }a->terminal[a->term_len]=0;a->dirty=1;
}
static u32 fm_send(fm_t *a,const u8 *s,u32 newline) {
 u32 n=fm_len(s);if(a->term_state!=2 || a->term_send_len || n+(newline?1:0)>=sizeof(a->send))return 0;
 for(u32 i=0;i<n;i++)a->send[i]=s[i];if(newline)a->send[n++]='\n';
 a->term_send_at=0;a->term_send_len=n;a->term_scroll=0;a->term_follow=1;return 1;
}
static u32 fm_quote(u8 *out,u32 at,u32 cap,const u8 *s) {
 /* NSH double quoted arguments. The firmware parser has no shell pipelines. */
 if(at+3>=cap)return 0;out[at++]='"';
 for(u32 i=0;s[i];i++){if(s[i]=='\n' || s[i]=='\r' || s[i]=='"' || s[i]=='\\' || s[i]=='$' || s[i]=='`')return 0;
  if(at+2>=cap)return 0;out[at++]=s[i];}
 out[at++]='"';out[at]=0;return at;
}
static void fm_script(fm_t *a) {
  if(!a->pending_script || a->term_state!=2 || a->term_send_len)return;
  if(a->pending_script==3){
   if(!fm_send(a,a->command,1))fm_notice(a,M_NO_SCRIPT,0);
   a->pending_script=0;return;
  }
  u32 p=0;
 u8 cmd[FM_PATH+8];cmd[p++]=a->pending_script==2?'l':'s';cmd[p++]=a->pending_script==2?'u':'h';
 if(a->pending_script==2)cmd[p++]='a';cmd[p++]=' ';
 p=fm_quote(cmd,p,sizeof(cmd),a->script_path);
 if(!p || p>255 || !fm_send(a,cmd,1))fm_notice(a,M_NO_SCRIPT,0);
 a->pending_script=0;
}
static void fm_terminal_poll(bt_ui_t *u) {
 fm_t *a=fm_state(u);u8 buf[256];
 if(a->term_out>=0)for(u32 i=0;i<8;i++){s32 n=fm_read(a,a->term_out,buf,sizeof(buf));
  if(n<=0)break;fm_terminal_text(a,buf,n);}
 if(a->term_state==2 && a->term_send_at<a->term_send_len) {
  s32 n=fm_write(a,a->term_in,a->send+a->term_send_at,a->term_send_len-a->term_send_at);
  if(n>0)a->term_send_at+=n;else if(n<0 && fm_errno(a)!=11 && fm_errno(a)!=4)fm_notice(a,M_ERROR,fm_errno(a));
  if(a->term_send_at==a->term_send_len)a->term_send_len=a->term_send_at=0;
 }
 if(a->term_state && a->term_pid && ((s32 (*)(u32,u32))a->kill)(a->term_pid,0)<0 && fm_errno(a)==3)a->term_state=3;
 if(a->term_state==3) {
  fm_barrier();u32 error=a->term_error,stage=a->term_stage;
  if(a->term_in>=0)fm_close(a,a->term_in);if(a->term_out>=0)fm_close(a,a->term_out);
  a->term_in=a->term_out=-1;a->term_state=a->term_pid=a->term_send_len=a->term_send_at=0;
  a->pending_script=0;fm_notice(a,error?stage:M_STOPPED,error);
 }
 if(a->term_state==2)fm_script(a);
}

static u32 fm_wrap(u8 *out,u32 cap,const u8 *src,u32 n,u32 lines,u32 cols) {
 u32 p=0,i=0,line=0,col=0;
 while(i<n && line<lines && p+8<cap) {
  u32 k=1,c=src[i];
  if(c>=0xC2 && c<=0xDF)k=2;else if(c>=0xE0 && c<=0xEF)k=3;else if(c>=0xF0 && c<=0xF4)k=4;
  if(i+k>n)break;
  u32 width=k>1?2:1;
  if(c=='\r'){i++;continue;}
  if(c=='\n'){out[p++]='\n';i++;line++;col=0;continue;}
  if(col+width>cols){out[p++]='\n';line++;col=0;if(line>=lines)break;}
  if(c<32 || (c&0xc0)==0x80){out[p++]='.';i++;col++;continue;}
  for(u32 j=0;j<k;j++)out[p++]=src[i++];col+=width;
 }out[p]=0;return i;
}
static u32 fm_row_slot(u32 row) {return row<6?4+row:38+row-6;}
static s32 fm_scroll_y(fm_t *a) {return a->viewport && a->scroll_get_y?((s32 (*)(u32))a->scroll_get_y)(a->viewport):0;}
static void fm_scroll_to(fm_t *a,s32 y) {
 if(a->viewport && a->scroll_to_y)((void (*)(u32,s32,u32))a->scroll_to_y)(a->viewport,y,0);
}
static u32 fm_size(u8 *,u32,u32,u64);
static u32 fm_codepoint(const u8 *s,u32 at,u32 end) {
 u32 c=s[at++],k=c<128?0:c<224?1:c<240?2:3,v=c<128?c:c&((1u<<(6-k))-1);
 while(k-- && at<end)v=(v<<6)|(s[at++]&63);return v;
}
static u32 fm_advance(fm_t *a,u32 c) {
 if(c<128 && a->glyph_widths[c])return a->glyph_widths[c];
 u32 w=c<128?10:18;
#ifndef BT_HOST_TEST
 if(bt_valid_ptr(a->small_font)) {
  u32 cb=*(u32 *)a->small_font;
  if((cb&1) && cb>=0x0c080001u && cb<0x0c7ea290u) {
   u32 d[4]={0,0,0,0};
   if(((u32 (*)(u32,u32,u32,u32))cb)(a->small_font,(u32)d,c,32)) {
    u32 advance=((u16 *)d)[2];if(advance && advance<=64)w=advance;
   }
  }
 }
#else
 w=c=='i'?5:c=='W'?16:c<128?10:18;
#endif
 if(c<128)a->glyph_widths[c]=(u16)w;return w;
}
/* Pixel widths drive BOTH content height and labels. Counting character cells
 * made wide glyphs wrap a second time in LVGL and put the last output offscreen.
 * Leave four pixels for font rounding; tabs are rendered as four spaces. */
static u32 fm_text_step(fm_t *a,const u8 *s,u32 i,u32 end,u32 *c) {
 *c=fm_codepoint(s,i,end);
 if(*c==9)return fm_advance(a,32)*4;
 if(*c<32 && *c!=10 && *c!=13)*c=46;
 return fm_advance(a,*c);
}
static u32 fm_text_scan(fm_t *a,const u8 *src,u32 n,u32 wanted,u32 locate) {
 u32 line=0,x=0;if(locate && !wanted)return 0;
 for(u32 i=0;i<n;) {
  u32 end=fm_next(src,i,n),c,w=fm_text_step(a,src,i,end,&c);
  if(c==13){i=end;continue;}
  if(c==10){i=end;line++;x=0;if(locate && line==wanted)return i;continue;}
  if(x && x+w>284){line++;x=0;if(locate && line==wanted)return i;}
  x+=w;i=end;
 }
 return locate?n:line+1;
}
static u32 fm_text_render(fm_t *a,u8 *out,u32 cap,const u8 *src,u32 n,u32 start,u32 lines) {
 u32 i=fm_text_scan(a,src,n,start,1),begin=i,p=0,line=0,x=0;
 while(i<n && line<lines && p+8<cap) {
  u32 end=fm_next(src,i,n),c,w=fm_text_step(a,src,i,end,&c);
  if(c==13){i=end;continue;}
  if(c==10){i=end;out[p++]=10;line++;x=0;continue;}
  if(x && x+w>284){out[p++]=10;line++;x=0;if(line>=lines)break;}
  if(c==9){for(u32 j=0;j<4;j++)out[p++]=32;}
  else if(c==46 && src[i]<32)out[p++]=46;
  else for(u32 j=i;j<end;j++)out[p++]=src[j];
  x+=w;i=end;
 }
 out[p]=0;return i-begin;
}
/* Native viewport scrolls the editor as well as the reader. Only a key/tap
 * requests caret following; a finger scrolling old text never snaps back. */
static void fm_editor(fm_t *a) {
 const u8 *s=a->view==V_EDIT?a->edit:a->input;
 u32 n=a->view==V_EDIT?a->edit_len:a->input_len,cur=a->view==V_EDIT?a->cursor:a->input_cursor;
 if(cur>n)cur=n;
 u32 line=0,x=0,cursor_line=0,cursor_x=0,p=0,prefix=0;
 if(a->view==V_PROMPT && a->prompt==P_COMMAND) {
  u32 start=a->term_len;while(start && a->terminal[start-1]!=10)start--;
  u32 px=0;for(u32 i=start;i<a->term_len;){u32 end=fm_next(a->terminal,i,a->term_len);
   u32 w=fm_advance(a,fm_codepoint(a->terminal,i,end));if(px+w>280)break;
   while(i<end)a->display[p++]=a->terminal[i++];px+=w;
  }if(p){a->display[p++]=10;prefix=1;}
 }
 u32 height=a->line_height?a->line_height:22;
 for(u32 i=0;i<=n;) {
  u32 end=i<n?fm_next(s,i,n):i,c=0,w=i<n?fm_text_step(a,s,i,end,&c):0;
  if(i<n && c!=10 && c!=13 && x && x+w>284){line++;x=0;}
  if(i==cur){cursor_line=line;cursor_x=x;}
  if(i==n)break;
  if(c==10){line++;x=0;}else if(c!=13)x+=w;i=end;
 }
 a->caret_x=cursor_x;a->caret_y=(cursor_line+prefix)*height;
 a->editor_prefix=prefix;a->content_lines=line+1+prefix;a->editor_lines=3;
 if(a->caret_follow){s32 cy=(s32)a->caret_y+10;
  if(cy<a->editor_y+10)a->editor_y=cy-10;
  if(cy+(s32)height>a->editor_y+78)a->editor_y=cy+(s32)height-78;
  if(a->editor_y<0)a->editor_y=0;
 }
 a->editor_top=(u32)a->editor_y/height;
 /* Keep the shell prompt as a real first line, so scroll and tap share origin. */
 if(a->render_line){p=0;}
 u32 start=a->render_line>prefix?a->render_line-prefix:0;
 fm_text_render(a,a->display+p,sizeof(a->display)-p,s,n,start,16);
}
static void fm_render_body(fm_t *a) {
 u32 p=0;
 if(a->view==V_IMAGE) {
  p=fm_cat(a->display,p,sizeof(a->display),(u8 *)fm_msg(a,a->format));a->display[p++]=' ';
  p=fm_num(a->display,p,sizeof(a->display),a->image_width);a->display[p++]='x';
  p=fm_num(a->display,p,sizeof(a->display),a->image_height);a->display[p++]='\n';
  fm_size(a->display,p,sizeof(a->display),a->file_size);
 }else if(a->view==V_INFO) {
  p=fm_cat(a->display,p,sizeof(a->display),(u8 *)fm_msg(a,a->format));a->display[p++]='\n';
  p=fm_size(a->display,p,sizeof(a->display),a->file_size);a->display[p++]='\n';
  if(a->image_width && a->image_height){p=fm_num(a->display,p,sizeof(a->display),a->image_width);
   a->display[p++]=' ';a->display[p++]='x';a->display[p++]=' ';p=fm_num(a->display,p,sizeof(a->display),a->image_height);a->display[p++]='\n';}
  if(a->view==V_INFO){a->display[p++]='\n';p=fm_cat(a->display,p,sizeof(a->display),(u8 *)fm_msg(a,
   a->format>=M_PNG && a->format<=M_LVGL?M_IMAGE:M_SOURCE));a->display[p++]='\n';
   fm_wrap(a->display+p,sizeof(a->display)-p,a->path,fm_len(a->path),5,28);
  }else a->display[p]=0;
 }else if(a->view==V_VIEW) {
  if(!a->hex){a->visible_bytes=fm_text_render(a,a->display,sizeof(a->display),a->edit,a->page_len,a->render_line,16);}
  else {
   u32 begin=a->render_line*6,n=a->page_len>begin?a->page_len-begin:0;if(n>96)n=96;a->visible_bytes=n;
   for(u32 i=begin;i<begin+n;i+=6) {
    for(u32 j=0;j<8;j++){u32 v=(a->page_offset+i)>>((7-j)*4);v&=15;a->display[p++]=(u8)(v<10?'0'+v:'A'+v-10);}
    a->display[p++]=' ';
    for(u32 j=i;j<i+6 && j<begin+n;j++){u32 v=a->edit[j];a->display[p++]=(u8)((v>>4)<10?'0'+(v>>4):'A'+(v>>4)-10);
     a->display[p++]=(u8)((v&15)<10?'0'+(v&15):'A'+(v&15)-10);a->display[p++]=' ';}
    a->display[p++]='\n';
   }a->display[p]=0;
  }
 }else if(a->view==V_TERM) {
  a->term_view_bytes=fm_text_render(a,a->display,sizeof(a->display),a->terminal,a->term_len,a->render_line,16);
 }else if(a->view==V_EDIT || a->view==V_PROMPT) {
  fm_editor(a);
 }
}
enum { S_BUTTON, S_BODY, S_ROW, S_KEY, S_GHOST, S_PRIMARY, S_DANGER, S_ACTIVE };
static void fm_prop(bt_ui_t *u,u32 o,u32 prop,u32 value) {
 ((void (*)(u32,u32,u32,u32))u->set_prop)(o,prop,value,0);
}
static void fm_draw(bt_ui_t *u,u32 i,u32 action,s32 x,s32 y,u32 w,u32 h,const u8 *text,u32 style) {
 fm_t *a=fm_state(u);u32 o=a->objects[i],l=a->labels[i];if(!o || !l)return;
 a->contexts[i][1]=action;
 ((void (*)(u32,u32))u->clear_flag)(o,1u|2u|a->clear_flags);
 if(action)((void (*)(u32,u32))u->add_flag)(o,2u|a->press_lock);
 ((void (*)(u32,u32,u32))u->set_size)(o,w,h);
 ((void (*)(u32,u32,u32,u32))u->align)(o,1u,(u32)x,(u32)y);
 u32 bg=0xFF292C34u,fg=0xFFF2F2F2u,border=0xFF263340u,font=style==S_KEY?a->key_font:style==S_ROW?a->file_font:a->small_font;
 if(style==S_BODY)bg=0xFF292C34u;
 if(style==S_ROW)bg=0xFF292C34u;
 if(style==S_KEY)bg=0xFF292C34u;
 if(style==S_GHOST){bg=0xFF101216u;fg=0xFFD0D5DDu;font=a->key_font;}
 if(style==S_PRIMARY){bg=0xFF0A84FFu;fg=0xFFF2F4F8u;border=bg;}
 if(style==S_DANGER){bg=0xFF2C1B25u;fg=0xFFFF909Cu;border=0xFF52303Du;}
 if(style==S_ACTIVE){bg=0xFF0A84FFu;fg=0xFFF2F2F2u;border=bg;}
 fm_prop(u,o,0x20,bg);fm_prop(u,o,0x21,255);
 fm_prop(u,o,0x0B,style==S_KEY?6:style==S_BODY?12:10);
 fm_prop(u,o,0x30,border);fm_prop(u,o,0x32,style==S_DANGER?1:0);
 u32 left=style==S_BODY || style==S_ROW,pad=style==S_BODY?10:style==S_ROW?10:2;
 u32 label_h=left?(style==S_ROW?30:h>pad*2?h-pad*2:h):font==a->key_font?28:26;
 ((void (*)(u32,u32,u32))u->set_size)(l,w>pad*2?w-pad*2:w,label_h);
 ((void (*)(u32,u32,u32,u32))u->align)(l,left?1u:9u,left?pad:0,left?style==S_ROW?1u:pad:0);
 fm_prop(u,l,0x5B,left?0:2);fm_prop(u,l,0x55,fg);fm_prop(u,l,0x58,0);
 if(font)fm_prop(u,l,0x57,font);
 ((void (*)(u32,u32))u->label_set_text)(l,(u32)text);
}
static void fm_button(bt_ui_t *u,u32 i,u32 action,s32 x,s32 y,u32 w,u32 h,u32 msg) {
 fm_t *a=fm_state(u);u32 style=S_BUTTON;
 if(action<=4 || action==10 || action==11 || action==30 || action==31 || action==42 || action==43)style=S_GHOST;
 if((action==2 && a->view!=V_TERM && !(a->view==V_PROMPT && a->prompt==P_COMMAND)) ||
    (action==3 && (a->view==V_TERM || (a->view==V_PROMPT && a->prompt==P_COMMAND))))style=S_ACTIVE;
 if(action==56 || action==40 || (action==20 && a->view==V_FILE))style=S_PRIMARY;
 if(action==27 || action==41)style=S_DANGER;
 fm_draw(u,i,action,x,y,w,h,(u8 *)fm_msg(a,msg),style);
}
static u32 fm_short(u8 *out,u32 cap,const u8 *text,u32 cells,u32 tail) {
 u32 n=fm_len(text),at=tail?n:0,used=0;
 while(tail?at!=0:at<n){u32 next=tail?fm_prev(text,at):fm_next(text,at,n);
  u32 width=(tail?at-next:next-at)>1?2:1;if(used+width>cells)break;used+=width;at=next;
 }
 if((tail && !at) || (!tail && at==n)){fm_copy(out,cap,text);return n;}
 u32 p=0;if(tail){out[p++]='.';out[p++]='.';out[p++]='.';p=fm_cat(out,p,cap,text+at);}
 else{for(u32 i=0;i<at && p+4<cap;i++)out[p++]=text[i];out[p++]='.';out[p++]='.';out[p++]='.';out[p]=0;}
 return p;
}
static u32 fm_size(u8 *out,u32 at,u32 cap,u64 bytes) {
 u32 unit=0;u64 div=1;while(bytes/div>=1024 && unit<3){unit++;div*=1024;}
 at=fm_num(out,at,cap,(u32)(bytes/div));
 if(unit && bytes/div<10 && at+2<cap){out[at++]='.';out[at++]=(u8)('0'+(bytes%div)*10/div);}
 if(at+3<cap){out[at++]=' ';if(unit)out[at++]=unit==1?'K':unit==2?'M':'G';out[at++]='B';}out[at]=0;return at;
}
static void fm_image_show(bt_ui_t *u) {
 fm_t *a=fm_state(u);if(!a->image_ready || a->job_state)return;
 if(!a->image){a->image=((u32 (*)(u32))a->image_create)(u->root);if(!a->image){fm_notice(a,M_IMAGE_FAIL,12);return;}
  ((void (*)(u32,u32))u->clear_flag)(a->image,2u|a->clear_flags);
  ((void (*)(u32,u32))u->add_flag)(a->image,a->gesture_flags);}
 u32 source=a->format==M_BMP?(u32)a->image_descriptor:(u32)a->image_path;
 ((void (*)(u32,u32))a->image_src)(a->image,source);
 u32 w=a->format==M_BMP?(a->image_descriptor[0]>>10)&2047:a->image_width;
 u32 h=a->format==M_BMP?a->image_descriptor[0]>>21:a->image_height;
 u32 zoom=256;if(w>308)zoom=308*256/w;if(h*zoom/256>280)zoom=280*256/h;
 if(h*zoom/256>256)zoom=256*256/h;
 if(!zoom)zoom=1;((void (*)(u32,u32))a->image_zoom)(a->image,zoom);
 ((void (*)(u32,u32,u32,u32))u->align)(a->image,1,(u32)(14+(308-(s32)w)/2),(u32)(164+(256-(s32)h)/2));
 ((void (*)(u32,u32))u->clear_flag)(a->image,1u);
}
static void fm_image_prepare(fm_t *a) {
 a->image_ready=0;
 if(!a->file_size || a->file_size>1048576u || a->format==M_GIF){fm_notice(a,M_IMAGE_FAIL,0);a->view=V_INFO;return;}
 /* The firmware header packs only 11 bits per dimension. Reject oversized
  * IHDR values BEFORE they can be truncated into apparently small images. */
 if(a->format==M_PNG && (!a->image_width || !a->image_height || a->image_width>1024 ||
  a->image_height>1024 || a->image_width*a->image_height>262144u)){
  fm_notice(a,M_IMAGE_BIG,0);a->view=V_INFO;return;
 }
 /* N67 lv_fs_posix registers driver letter /, not the desktop S: convention. */
 if(!fm_copy(a->image_path,sizeof(a->image_path),a->path)){a->view=V_INFO;fm_notice(a,M_IMAGE_FAIL,36);return;}
 u32 header=0;u32 ok=((u32 (*)(u32,u32))a->image_info)((u32)a->image_path,(u32)&header);
 if(ok!=1 || !header){fm_notice(a,M_IMAGE_FAIL,0);a->view=V_INFO;return;}
 u32 w=(header>>10)&2047,h=header>>21;
 if(!w || !h || w>1024 || h>1024 || w*h>262144u){fm_notice(a,M_IMAGE_BIG,0);a->view=V_INFO;return;}
 a->image_width=w;a->image_height=h;a->image_ready=1;fm_notice(a,M_IMAGE,0);
}
static void fm_scroll_setup(bt_ui_t *u) {
 fm_t *a=fm_state(u);u32 files=a->view==V_FILES,term=a->view==V_TERM,editor=a->view==V_EDIT || a->view==V_PROMPT;
 u32 unit=files?FM_ROW_HEIGHT:a->line_height, height=editor?88:term?270:304;
 if(editor)fm_editor(a);
 u32 total=editor?a->content_lines:files?a->total:term?fm_text_scan(a,a->terminal,a->term_len,0,0):
  a->hex?(a->page_len+5)/6:fm_text_scan(a,a->edit,a->page_len,0,0);
 if(!unit)unit=22;if(!total)total=1;a->content_lines=total;
 s32 *position=editor?&a->editor_y:files?&a->list_y:term?&a->term_y:&a->text_y;
 s32 maximum=(s32)(total*unit+(files?0:editor?20:10))-(s32)height;if(maximum<0)maximum=0;
 if(term && a->term_follow)*position=maximum;
 if(*position<0)*position=0;if(*position>maximum)*position=maximum;
 u32 top=(u32)*position/unit,span=files?600:1000;
 if(span*unit>30000)span=30000/unit;
 u32 sync=a->scroll_sync || a->scroll_view!=a->view+1;
 if(sync)a->scroll_base=top>100?top-100:0;
 else if(top<a->scroll_base || (a->scroll_base && top<a->scroll_base+30) || top>a->scroll_base+span-30){
  a->scroll_base=top>100?top-100:0;sync=1;
 }
 u32 extent=total-a->scroll_base;if(extent>span)extent=span;
 ((void (*)(u32,u32))u->clear_flag)(a->viewport,1u);
 ((void (*)(u32,u32,u32))u->set_size)(a->viewport,308,height);
 ((void (*)(u32,u32,u32,u32))u->align)(a->viewport,1,14,116);
 ((void (*)(u32,u32,u32))u->set_size)(a->spacer,1,extent*unit+(files?0:editor?20:10));
 ((void (*)(u32,u32,u32,u32))u->align)(a->spacer,1,0,0);
 a->render_line=top>2?top-2:0;if(a->render_line<a->scroll_base)a->render_line=a->scroll_base;
 a->scroll_view=a->view+1;a->scroll_sync=0;
 a->scroll_apply=sync || (term && a->term_follow) || (editor && a->caret_follow);
 if(editor)a->caret_follow=0;
}
static void fm_scroll_body(bt_ui_t *u) {
 fm_t *a=fm_state(u);fm_render_body(a);u32 l=a->scroll_label;
 ((void (*)(u32,u32))u->clear_flag)(l,1u);
 u32 lines=a->content_lines-a->render_line;if(lines>17)lines=17;
 ((void (*)(u32,u32,u32))u->set_size)(l,288,a->line_height*lines);
 ((void (*)(u32,u32,u32,u32))u->align)(l,1,10,(a->render_line-a->scroll_base)*a->line_height+(a->view==V_EDIT || a->view==V_PROMPT?10:0));
 ((void (*)(u32,u32))u->label_set_text)(l,(u32)a->display);
}
static void fm_layout(bt_ui_t *u) {
 fm_t *a=fm_state(u);for(u32 i=0;i<FM_ROWS;i++) {
  a->contexts[i][1]=0;if(a->objects[i])((void (*)(u32,u32))u->add_flag)(a->objects[i],1u);
 }
 if(a->image)((void (*)(u32,u32))u->add_flag)(a->image,1u);
 u32 scrolling=a->view==V_FILES || a->view==V_VIEW || a->view==V_TERM || a->view==V_EDIT || a->view==V_PROMPT;
 if(a->viewport && !scrolling)((void (*)(u32,u32))u->add_flag)(a->viewport,1u);
 if(a->scroll_label && a->view!=V_VIEW && a->view!=V_TERM && a->view!=V_EDIT && a->view!=V_PROMPT)((void (*)(u32,u32))u->add_flag)(a->scroll_label,1u);
 for(u32 i=0;i<FM_LIST_ROWS;i++)if(a->details[i])((void (*)(u32,u32))u->add_flag)(a->details[i],1);
 u32 parent=a->view==V_FILES?a->viewport:u->root;
 if(a->row_parent!=parent){for(u32 i=0;i<FM_LIST_ROWS;i++)
  if(a->objects[fm_row_slot(i)])((void (*)(u32,u32))a->set_parent)(a->objects[fm_row_slot(i)],parent);
  a->row_parent=parent;}
 fm_button(u,0,1,14,12,48,44,M_BACK);fm_button(u,1,2,70,12,96,44,M_FILES);
 fm_button(u,2,3,170,12,96,44,M_TERMINAL);fm_button(u,3,4,274,12,48,44,M_REFRESH);
 if(a->caret)((void (*)(u32,u32))u->add_flag)(a->caret,1u);
 if(a->job_state==1 && (a->job_kind==J_LOAD || a->job_kind==J_INSPECT || a->job_kind==J_PAGE || a->job_kind==J_BITMAP) && a->view!=V_TERM) {
  if(a->viewport)((void (*)(u32,u32))u->add_flag)(a->viewport,1u);
  fm_draw(u,4,0,14,116,308,88,(u8 *)fm_msg(a,M_BUSY),S_BODY);return;
 }
 if(a->view==V_FILES) {
  fm_scroll_setup(u);
  for(u32 i=0;i<a->count;i++) {
   if(a->skip+i<a->scroll_base || a->skip+i>=a->scroll_base+600)continue;
   u32 slot=fm_row_slot(i);fm_entry_t *entry=&a->entries[i];fm_short(a->captions[slot],256,entry->type==FM_PARENT_TYPE?(u8 *)fm_msg(a,M_UPDIR):entry->name,25,0);
   fm_draw(u,slot,100+i,0,((s32)a->skip+(s32)i-(s32)a->scroll_base)*FM_ROW_HEIGHT,308,56,a->captions[slot],S_ROW);
   u8 *meta=a->metadata[i];u32 p=fm_cat(meta,0,96,(u8 *)fm_msg(a,entry->type==FM_PARENT_TYPE?M_ROOT:entry->type==4?M_DIR:M_FILE));
   if(entry->type==FM_PARENT_TYPE && a->cwd[1]){u8 parent[FM_PATH],up[3]={46,46,0};
    if(fm_join(parent,a->cwd,up))p=fm_short(meta,96,parent,28,1);
   }
   if(entry->type!=4 && entry->type!=FM_PARENT_TYPE){meta[p++]=' ';meta[p++]=' ';fm_size(meta,p,96,entry->size);}
   u32 label=a->details[i];if(label){
    ((void (*)(u32,u32))u->clear_flag)(label,1u);
    ((void (*)(u32,u32,u32))u->set_size)(label,288,20);
    ((void (*)(u32,u32,u32,u32))u->align)(label,1,10,32);
    fm_prop(u,label,0x55,(entry->type==4 || entry->type==FM_PARENT_TYPE)?0xFF8AB4F8u:0xFF7F92A5u);
    ((void (*)(u32,u32))u->label_set_text)(label,(u32)meta);
   }
  }
  fm_button(u,12,12,14,430,72,44,M_NEWFILE);fm_button(u,13,13,92,430,72,44,M_NEWDIR);
  fm_button(u,14,14,172,430,72,44,M_PASTE);fm_button(u,15,15,250,430,72,44,M_PATH);
 }else if(a->view==V_FILE) {
  u32 regular=fm_selected_type(a)==8;
  if(regular){fm_button(u,4,20,14,124,150,64,M_VIEW);fm_button(u,5,21,172,124,150,64,M_EDIT);}
  fm_button(u,8,24,14,200,150,64,M_COPY);fm_button(u,9,25,172,200,150,64,M_MOVE);
  if(regular){fm_button(u,6,22,14,276,150,64,M_SHELL);fm_button(u,7,23,172,276,150,64,M_LUA);}
  fm_button(u,12,26,14,392,150,64,M_RENAME);fm_button(u,13,27,172,392,150,64,M_DELETE);
 }else if(a->view==V_IMAGE || a->view==V_INFO) {
  fm_render_body(a);fm_draw(u,4,0,14,116,308,a->view==V_INFO?302:40,a->display,S_BODY);
  if(a->view==V_IMAGE)fm_image_show(u);
  fm_button(u,12,33,14,430,98,44,M_HEX);fm_button(u,13,34,120,430,98,44,a->view==V_INFO?M_VIEW:M_INFO);
  fm_button(u,14,24,224,430,98,44,M_COPY);
 }else if(a->view==V_VIEW || a->view==V_TERM) {
  fm_scroll_setup(u);fm_scroll_body(u);
  if(a->view==V_VIEW) {
   fm_button(u,12,32,14,430,72,44,a->hex?M_TEXT:M_HEX);
   fm_button(u,13,21,92,430,72,44,M_EDIT);fm_button(u,14,34,172,430,72,44,M_INFO);
   fm_button(u,15,24,250,430,72,44,M_COPY);
  }else {
   fm_button(u,10,44,14,392,98,30,M_RESET);fm_button(u,14,42,120,392,98,30,M_CLEAR);
   fm_button(u,15,43,224,392,98,30,M_HISTORY);
   fm_button(u,12,40,14,430,202,44,M_COMMAND);fm_button(u,13,41,224,430,98,44,M_INTERRUPT);
  }
 }else {
  fm_scroll_setup(u);fm_scroll_body(u);
  u8 *keys=(u8 *)fm_msg(a,M_LOWER+a->bank);u32 n=fm_len(keys);
  for(u32 i=0;i<26 && i<n;i++) {
   a->captions[5+i][0]=keys[i];a->captions[5+i][1]=0;
   u32 row=i<7?0:i<14?1:i<20?2:3,col=i<7?i:i<14?i-7:i<20?i-14:i-20;
   s32 x=(row<2?14:36)+col*44;
   fm_draw(u,5+i,200+i,x,212+row*42,40,40,a->captions[5+i],S_KEY);
  }
  u8 *bank=a->captions[31];bank[0]=a->bank==0?'a':a->bank==1?'A':a->bank==2?'1':'#';
  bank[1]=a->bank==0?'b':a->bank==1?'B':a->bank==2?'2':'+';
  bank[2]=a->bank==0?'c':a->bank==1?'C':a->bank==2?'3':'=';bank[3]=0;
  fm_draw(u,31,50,14,384,56,40,bank,S_GHOST);fm_button(u,32,51,76,384,110,40,M_SPACE);
  fm_button(u,33,52,192,384,62,40,M_BACKSPACE);fm_button(u,34,
   a->view==V_PROMPT && a->prompt==P_COMMAND?57:53,260,384,62,40,
   a->view==V_EDIT?M_ENTER:a->prompt==P_COMMAND?M_CLEAR:M_DONE);
  fm_button(u,35,54,14,430,52,44,M_LEFT);fm_button(u,36,55,74,430,52,44,M_RIGHT);
  fm_button(u,37,56,134,430,188,44,a->view==V_EDIT?M_SAVE:a->prompt==P_COMMAND?M_SEND:M_DONE);
  fm_prop(u,a->labels[33],0x57,a->key_font);fm_prop(u,a->labels[34],0x57,a->key_font);
  if(a->caret && a->caret_y+a->line_height>(u32)a->editor_y && a->caret_y<(u32)a->editor_y+88){
   ((void (*)(u32,u32,u32))u->set_size)(a->caret,3,20);
   ((void (*)(u32,u32,u32,u32))u->align)(a->caret,1,10+a->caret_x,10+a->caret_y-a->scroll_base*a->line_height);
   ((void (*)(u32,u32))u->clear_flag)(a->caret,1u);
  }
 }
 if(a->scroll_apply && scrolling){s32 y=a->view==V_FILES?a->list_y:a->view==V_TERM?a->term_y:
  a->view==V_EDIT || a->view==V_PROMPT?a->editor_y:a->text_y;
  fm_scroll_to(a,y-(s32)(a->scroll_base*(a->view==V_FILES?FM_ROW_HEIGHT:a->line_height)));
 }a->scroll_apply=0;if(a->view==V_EDIT || a->view==V_PROMPT)a->caret_follow=0;
}
static void bt_ui_show(bt_ui_t *u,bt_cfg_t *c) {
 (void)c;fm_t *a=fm_state(u);if(!a || u->status!=2 || !u->label || u->build!=100 || !a->dirty)return;
 if(a->job_state!=1 || a->view!=V_FILES)fm_layout(u);
 const u8 *path=a->view==V_FILES?a->cwd:a->view==V_TERM?(u8 *)fm_msg(a,M_TERMINAL):
  a->view==V_PROMPT?(u8 *)fm_msg(a,a->prompt==P_COMMAND?M_COMMAND:a->prompt==P_PATH?M_PATH:
   a->prompt==P_NEWFILE?M_NEWFILE:a->prompt==P_NEWDIR?M_NEWDIR:a->prompt==P_MOVE?M_DEST:M_RENAME):a->path;
 fm_short(a->title,sizeof(a->title),path,28,1);
 if(a->heading)((void (*)(u32,u32))u->label_set_text)(a->heading,(u32)a->title);
 /* Keep a separate status label so a long pathname cannot cover the error. */
 u8 tmp[256];u32 p=0;
 p=fm_cat(tmp,p,sizeof(tmp),(u8 *)fm_msg(a,a->confirm?M_CONFIRM:a->job_state?M_BUSY:a->message));
 if(a->detected && a->view==V_VIEW && !a->error && !a->confirm && !a->job_state){
  tmp[p++]=' ';p=fm_cat(tmp,p,sizeof(tmp),(u8 *)fm_msg(a,a->format));}
 if(a->error){if(p+1<sizeof(tmp))tmp[p++]=' ';p=fm_num(tmp,p,sizeof(tmp),a->error);}
 if(a->modified && p+2<sizeof(tmp)){tmp[p++]=' ';tmp[p++]='*';}
 tmp[p]=0;fm_prop(u,u->label,0x55,a->error?0xFFFF909Cu:a->confirm?0xFFFFCE83u:0xFFB3B3B3u);
 ((void (*)(u32,u32,u32))u->set_size)(u->label,a->view==V_FILES?224:308,22);
 if(a->page_indicator){
  if(a->view==V_FILES){u8 pages[32];u32 at=fm_num(pages,0,32,a->total?(u32)a->list_y/FM_ROW_HEIGHT+1:0);pages[at++]=' ';pages[at++]='/';pages[at++]=' ';
   fm_num(pages,at,32,a->total);((void (*)(u32,u32))u->clear_flag)(a->page_indicator,1);
   ((void (*)(u32,u32))u->label_set_text)(a->page_indicator,(u32)pages);
  }else ((void (*)(u32,u32))u->add_flag)(a->page_indicator,1);
 }
 ((void (*)(u32,u32))u->label_set_text)(u->label,(u32)tmp);a->dirty=0;u->shows++;
}
static u32 bt_ui_step(bt_ui_t *u,bt_cfg_t *c) {
 (void)c;fm_t *a=fm_state(u);if(!a || u->status!=2)return u?u->build:0;
 u->root=u->page?((u32 *)u->page)[11]:u->root;if(!u->root)return u->build;
 if(u->build==100){bt_ui_show(u,0);return 100;}
 if(u->build==8)return 8;
 if(!u->build) {
  if(!u->font)u->font=((u32 (*)(u32,u32,u32))a->font_create)(a->font_name,22,400);
  if(!a->small_font)a->small_font=((u32 (*)(u32,u32,u32))a->font_create)(a->font_name,18,400);
  if(!a->key_font)a->key_font=((u32 (*)(u32,u32,u32))a->font_create)(a->font_name,20,400);
  if(!a->detail_font)a->detail_font=((u32 (*)(u32,u32,u32))a->font_create)(a->font_name,14,400);
  if(!a->file_font)a->file_font=((u32 (*)(u32,u32,u32))a->font_create)(a->font_name,22,400);
  ((void (*)(u32,u32))u->clear_flag)(u->root,a->clear_flags);
  for(u32 i=0x10;i<0x14;i++)((void (*)(u32,u32,u32,u32))u->set_prop)(u->root,i,0,0);
  ((void (*)(u32,u32,u32,u32))u->set_prop)(u->root,0x20,0xFF101216u,0);
  ((void (*)(u32,u32,u32,u32))u->set_prop)(u->root,0x21,255,0);
  if(u->font)((void (*)(u32,u32,u32,u32))u->set_prop)(u->root,0x57,u->font,0);
  u->label=((u32 (*)(u32))u->label_create)(u->root);
  if(!u->label){u->build=8;u->last_ret=105;return 8;}
  ((void (*)(u32,u32))u->label_set_text)(u->label,(u32)fm_msg(a,M_BUSY));
  ((void (*)(u32,u32,u32))u->set_size)(u->label,308,22);
  ((void (*)(u32,u32,u32,u32))u->align)(u->label,1,14,88);
  ((void (*)(u32,u32))u->clear_flag)(u->label,2u|a->clear_flags);
  fm_prop(u,u->label,0x55,0xFFB3B3B3u);fm_prop(u,u->label,0x57,a->small_font);
  a->heading=((u32 (*)(u32))u->label_create)(u->root);
  a->page_indicator=((u32 (*)(u32))u->label_create)(u->root);
  if(!a->heading || !a->page_indicator){u->build=8;u->last_ret=105;return 8;}
  ((void (*)(u32,u32))u->label_set_text)(a->heading,(u32)a->cwd);
  ((void (*)(u32,u32))u->label_set_text)(a->page_indicator,(u32)"");
  ((void (*)(u32,u32,u32))u->set_size)(a->heading,308,26);
  ((void (*)(u32,u32,u32,u32))u->align)(a->heading,1,14,60);
  ((void (*)(u32,u32,u32))u->set_size)(a->page_indicator,76,22);
  ((void (*)(u32,u32,u32,u32))u->align)(a->page_indicator,1,246,88);
  fm_prop(u,a->heading,0x55,0xFFF2F2F2u);fm_prop(u,a->heading,0x57,a->small_font);
  fm_prop(u,a->page_indicator,0x55,0xFFB3B3B3u);fm_prop(u,a->page_indicator,0x57,a->small_font);
  fm_prop(u,a->page_indicator,0x5B,2);
  ((void (*)(u32,u32))u->clear_flag)(a->heading,2u|a->clear_flags);
  ((void (*)(u32,u32))u->clear_flag)(a->page_indicator,2u|a->clear_flags);
  a->gesture_context[0]=(u32)u;a->gesture_context[1]=900;
  if(!((u32 (*)(u32,u32,u32,u32))a->event_add)(u->root,a->event_cb,0,(u32)a->gesture_context)){
   u->build=8;u->last_ret=106;return 8;}
  a->viewport=((u32 (*)(u32))u->obj_create)(u->root);
  a->spacer=a->viewport?((u32 (*)(u32))u->obj_create)(a->viewport):0;
  a->scroll_label=a->viewport?((u32 (*)(u32))u->label_create)(a->viewport):0;
  if(!a->viewport || !a->spacer || !a->scroll_label){u->build=8;u->last_ret=105;return 8;}
  for(u32 p=0x10;p<0x14;p++){fm_prop(u,a->viewport,p,0);fm_prop(u,a->spacer,p,0);}
  fm_prop(u,a->viewport,0x20,0xFF101216u);fm_prop(u,a->viewport,0x21,255);
  fm_prop(u,a->viewport,0x32,0);fm_prop(u,a->viewport,0x0B,10);
  fm_prop(u,a->spacer,0x21,0);fm_prop(u,a->spacer,0x32,0);
  ((void (*)(u32,u32))u->clear_flag)(a->spacer,2u|a->clear_flags);
  ((void (*)(u32,u32))u->clear_flag)(a->scroll_label,2u|a->clear_flags);
  ((void (*)(u32,u32))u->add_flag)(a->viewport,2u|a->clear_flags|a->scroll_momentum|a->gesture_flags|1u);
  ((void (*)(u32,u32))u->add_flag)(a->scroll_label,a->gesture_flags|1u);
  ((void (*)(u32,u32))a->scroll_dir)(a->viewport,a->dir_top|a->dir_bottom);
  fm_prop(u,a->scroll_label,0x57,a->small_font);fm_prop(u,a->scroll_label,0x55,0xFFF2F2F2u);
  /* N67 style table: 0x58 is LETTER space; 0x59 is LINE space. Explicit
   * zero letter spacing keeps the caret, wrapping and rendered glyphs aligned. */
  fm_prop(u,a->scroll_label,0x58,0);fm_prop(u,a->scroll_label,0x59,2);a->line_height=22;
#ifndef BT_HOST_TEST
  if(bt_valid_ptr(a->small_font)){u32 h=((u16 *)a->small_font)[4];if(h>=10 && h<=38)a->line_height=h+2;}
#endif
  a->scroll_context[0]=(u32)u;a->scroll_context[1]=901;
  if(!((u32 (*)(u32,u32,u32,u32))a->event_add)(a->viewport,a->event_cb,0,(u32)a->scroll_context)){
   u->build=8;u->last_ret=106;return 8;}
  a->scroll_view=0;a->scroll_sync=1;
  a->build_index=0;u->build=20;
 }
 if(a->build_index<FM_ROWS) {
  u32 i=a->build_index++,o=((u32 (*)(u32))0x0c43da65u)(u->root);
  if(!o){u->build=8;u->last_ret=105;return 8;}
  a->objects[i]=o;u32 l=((u32 (*)(u32))u->label_create)(o);
  if(!l){u->build=8;u->last_ret=105;return 8;}a->labels[i]=l;
  for(u32 p=0x10;p<0x14;p++)((void (*)(u32,u32,u32,u32))u->set_prop)(o,p,0,0);
  ((void (*)(u32,u32,u32,u32))u->set_prop)(o,0x21,255,0);
  ((void (*)(u32,u32,u32,u32))u->set_prop)(o,0x32,0,0);
  ((void (*)(u32,u32,u32,u32))u->set_prop)(l,0x55,0xFFFFFFFFu,0);
  ((void (*)(u32,u32))u->clear_flag)(o,a->clear_flags);
  ((void (*)(u32,u32))u->clear_flag)(l,2u|a->clear_flags);
  ((void (*)(u32,u32))u->add_flag)(o,a->gesture_flags);
  ((void (*)(u32,u32))u->add_flag)(l,a->gesture_flags);
  if((i>=4 && i<10) || i>=38){u32 detail=((u32 (*)(u32))u->label_create)(o);a->details[i<10?i-4:i-38+6]=detail;
   if(!detail){u->build=8;u->last_ret=105;return 8;}
   ((void (*)(u32,u32))u->clear_flag)(detail,2u|a->clear_flags);
   ((void (*)(u32,u32))u->add_flag)(detail,a->gesture_flags|1u);
   fm_prop(u,detail,0x57,a->detail_font);fm_prop(u,detail,0x55,0xFFB3B3B3u);
  }
  a->contexts[i][0]=(u32)u;
  if(!((u32 (*)(u32,u32,u32,u32))a->event_add)(o,a->event_cb,0,(u32)a->contexts[i])){u->build=8;u->last_ret=106;return 8;}
  ((void (*)(u32,u32))u->add_flag)(o,1u);return 20+i;
 }
 if(!a->caret){a->caret=((u32 (*)(u32))u->obj_create)(a->viewport);
  if(!a->caret){u->build=8;u->last_ret=105;return 8;}
  ((void (*)(u32,u32))u->clear_flag)(a->caret,2u|a->clear_flags);
  fm_prop(u,a->caret,0x20,0xFF0A84FFu);fm_prop(u,a->caret,0x21,255);fm_prop(u,a->caret,0x32,0);
 }
 a->row_parent=u->root;u->build=100;a->dirty=1;bt_ui_show(u,0);return 100;
}
static void fm_prompt(fm_t *a,u32 type,const u8 *initial) {
 a->previous=a->view;a->view=V_PROMPT;a->prompt=type;a->bank=0;
 a->touch=a->key_repeat=a->editor_top=0;a->editor_y=0;a->caret_follow=a->scroll_sync=1;
 fm_copy(a->input,sizeof(a->input),initial);a->input_len=fm_len(a->input);a->input_cursor=a->input_len;
 fm_notice(a,type==P_PATH?M_PATH:type==P_COMMAND?M_INPUT:type==P_MOVE?M_DEST:M_NAME,0);
}
static u32 fm_confirm(fm_t *a,u32 action) {
 if(a->confirm==action && (s32)(a->confirm_until-a->now)>0){a->confirm=0;return 1;}
 a->confirm=action;a->confirm_until=a->now+4000;fm_notice(a,M_CONFIRM,0);return 0;
}
static void fm_back(bt_ui_t *u) {
 fm_t *a=fm_state(u);
 if(a->view==V_EDIT && a->modified && !fm_confirm(a,1))return;
 if(a->view==V_EDIT)a->modified=0;
 if(a->view==V_PROMPT){a->view=a->previous;fm_notice(a,M_READY,0);return;}
 if(a->view!=V_FILES){a->view=V_FILES;fm_notice(a,M_READY,0);return;}
 if(a->cwd[1]) {u32 n=fm_len(a->cwd);while(n>1 && a->cwd[n-1]!='/')n--;if(n>1)n--;a->cwd[n]=0;a->skip=0;fm_job(u,J_LIST,a->cwd,0);}
 else if(a->page_back)((void (*)(void))a->page_back)();
}
static void fm_accept(bt_ui_t *u) {
 fm_t *a=fm_state(u);u8 dest[FM_PATH];u32 type=a->prompt;
 if(type==P_COMMAND){if(a->input_len>255 || !fm_send(a,a->input,1)){fm_notice(a,M_BUSY,0);return;}
  u32 i=a->history_n%8;fm_copy(a->history[i],256,a->input);a->history_n++;a->history_i=a->history_n;
  fm_copy(a->command,256,a->input);a->input[0]=0;a->input_len=a->input_cursor=0;
  a->view=V_TERM;fm_notice(a,M_RUNNING,0);return;}
 if(!fm_join(dest,a->cwd,a->input)){fm_notice(a,M_ERROR,36);return;}
 if(type==P_PATH){fm_copy(a->cwd,FM_PATH,dest);a->skip=0;a->view=V_FILES;fm_job(u,J_LIST,a->cwd,0);return;}
 u32 kind=type==P_NEWFILE?J_NEWFILE:type==P_NEWDIR?J_NEWDIR:J_MOVE;
 if(fm_job(u,kind,a->path,dest))a->view=V_FILES;
}
static void fm_action(bt_ui_t *u,u32 action,u32 long_press) {
 fm_t *a=fm_state(u);if(!a)return;
 if(a->view==V_EDIT && a->modified && (action==2 || action==3)){
  if(!fm_confirm(a,action))return;a->modified=0;
 }
 if(action==3){a->view=V_TERM;fm_notice(a,M_TERMINAL,0);if(!a->term_state && !a->job_state)fm_job(u,J_FIFO,0,0);return;}
 if(action==41){if(a->term_pid && fm_job(u,J_INTERRUPT,0,0))a->term_pending=1;return;}
 if(action==44){if(a->job_state){fm_notice(a,M_BUSY,0);return;}
  a->term_y=0;a->term_follow=1;a->scroll_sync=1;
  a->term_pending=1;a->reset_pending=1;a->pending_script=0;a->script_path[0]=0;
  a->term_send_at=a->term_send_len=0;a->command[0]=a->input[0]=0;a->input_len=a->input_cursor=0;
  a->history_n=a->history_i=a->ansi=a->discard=a->term_len=a->term_scroll=0;a->terminal[0]=0;
  for(u32 i=0;i<8;i++)a->history[i][0]=0;
  if(a->term_pid){if(!fm_job(u,J_INTERRUPT,0,0))a->term_pending=a->reset_pending=0;}
  else if(!a->term_state){a->reset_pending=a->term_pending=0;fm_job(u,J_FIFO,0,0);}
  fm_notice(a,M_RESET,0);return;}
 if(action==42){a->term_len=a->term_scroll=0;a->term_y=0;a->term_follow=1;a->scroll_sync=1;a->terminal[0]=0;fm_notice(a,M_TERMINAL,0);return;}
 if(a->job_state){fm_notice(a,M_BUSY,0);return;}
 if(action==1){fm_back(u);return;}
 if(action==2){a->view=V_FILES;fm_notice(a,M_READY,0);return;}
 if(action==4){if(a->view==V_FILES)fm_job(u,J_LIST,a->cwd,0);else if(a->view==V_VIEW)fm_job(u,J_PAGE,a->path,0);return;}
 if(action>=100 && action<100+FM_LIST_ROWS) {
  u32 i=action-100;if(i>=a->count)return;
  if(a->entries[i].type==FM_PARENT_TYPE){
   if(a->cwd[1])fm_back(u);else fm_notice(a,M_ROOT,0);return;
  }
  if(!fm_join(a->path,a->cwd,a->entries[i].name))return;
  a->selected=i;a->selected_type=a->entries[i].type;a->page_offset=0;a->page_history_n=0;
  if(a->entries[i].type==4 && !long_press){fm_copy(a->cwd,FM_PATH,a->path);a->skip=0;fm_job(u,J_LIST,a->cwd,0);}
  else {a->view=V_FILE;fm_notice(a,M_SELECTED,0);}return;
 }
 if(action==12 || action==13){u8 empty[1]={0};fm_prompt(a,action==12?P_NEWFILE:P_NEWDIR,empty);return;}
 if(action==14){if(!a->clipboard){fm_notice(a,M_CLIP_EMPTY,0);return;}u8 dest[FM_PATH];u32 n=fm_len(a->clip);while(n && a->clip[n-1]!='/')n--;
  if(fm_join(dest,a->cwd,a->clip+n))fm_job(u,a->clip_move?J_MOVE:J_COPY,a->clip,dest);return;}
 if(action==15){fm_prompt(a,P_PATH,a->cwd);return;}
 if(action==20){a->view=V_VIEW;a->hex=0;a->page_offset=0;a->page_history_n=0;a->detected=0;a->page_len=0;a->edit[0]=0;a->image_ready=0;a->text_y=0;a->scroll_sync=1;
  fm_job(u,J_INSPECT,a->path,0);return;}
 if(action==21){u32 prior=a->view;a->view=V_EDIT;a->editing=a->edit_len=a->cursor=a->editor_top=0;
  a->edit[0]=0;a->modified=0;a->bank=0;a->editor_y=0;a->caret_follow=a->scroll_sync=1;if(!fm_job(u,J_LOAD,a->path,0))a->view=prior;return;}
 if(action==22 || action==23){fm_copy(a->script_path,FM_PATH,a->path);a->pending_script=action==23?2:1;a->view=V_TERM;fm_notice(a,M_RUNNING,0);
  if(!a->term_state)fm_job(u,J_FIFO,0,0);else fm_script(a);return;}
 if(action==24){fm_copy(a->clip,FM_PATH,a->path);a->clipboard=fm_selected_type(a);
  if(!a->clipboard)a->clipboard=1;a->clip_move=0;fm_notice(a,M_COPIED,0);return;}
 if(action==25){u8 empty[1]={0};fm_prompt(a,P_MOVE,empty);return;}
 if(action==26){u32 n=fm_len(a->path);while(n && a->path[n-1]!='/')n--;fm_prompt(a,P_RENAME,a->path+n);return;}
 if(action==27){if(fm_confirm(a,27))fm_job(u,J_DELETE,a->path,0);return;}
 if(action==32){a->hex=!a->hex;a->text_y=0;a->scroll_sync=1;fm_notice(a,M_READY,0);return;}
 if(action==33){a->view=V_VIEW;a->hex=1;a->page_offset=a->page_history_n=0;a->text_y=0;a->scroll_sync=1;fm_job(u,J_PAGE,a->path,0);return;}
 if(action==34){if(a->view==V_INFO){a->view=a->image_ready?V_IMAGE:V_VIEW;
   if(a->format>=M_PNG && a->format<=M_LVGL && !a->image_ready)a->hex=1;
   if(!a->image_ready)fm_job(u,J_PAGE,a->path,0);
  }else a->view=V_INFO;fm_notice(a,M_INFO,0);return;}
 if(action==40){if(a->term_state!=2){if(!a->term_state)fm_job(u,J_FIFO,0,0);return;}
  u8 empty[1]={0};fm_prompt(a,P_COMMAND,empty);return;}
 if(action==43){if(!a->history_n)return;if(a->history_i)a->history_i--;u32 oldest=a->history_n>8?a->history_n-8:0;
  if(a->history_i<oldest)a->history_i=a->history_n-1;fm_prompt(a,P_COMMAND,a->history[a->history_i%8]);return;}
 if(a->view!=V_EDIT && a->view!=V_PROMPT)return;
 u8 *s=a->view==V_EDIT?a->edit:a->input;
 u32 *len=a->view==V_EDIT?&a->edit_len:&a->input_len,*cur=a->view==V_EDIT?&a->cursor:&a->input_cursor;
 u32 cap=a->view==V_EDIT?FM_EDIT+1:a->prompt==P_COMMAND?256:FM_PATH;
 if(action==50)a->bank=(a->bank+1)%4;
 else if(action==57 && a->view==V_PROMPT){s[0]=0;*len=*cur=0;}
 else if(action==54)*cur=fm_prev(s,*cur);
 else if(action==55)*cur=fm_next(s,*cur,*len);
 else if(action==52){fm_backspace(s,len,cur);if(a->view==V_EDIT)a->modified=1;}
 else if(action==56){if(a->view==V_EDIT)fm_job(u,J_SAVE,a->path,a->path);else fm_accept(u);return;}
 else if(action==53 && a->view==V_PROMPT){fm_accept(u);return;}
 else {
  u8 ch=action==51?' ':action==53?'\n':0;
  if(action>=200 && action<226){u8 *bank=(u8 *)fm_msg(a,M_LOWER+a->bank);u32 i=action-200;if(i<fm_len(bank))ch=bank[i];}
  if(ch){if(!fm_insert(s,len,cur,cap,&ch,1)){fm_notice(a,M_BIG,0);return;}if(a->view==V_EDIT)a->modified=1;}
 }a->caret_follow=1;fm_notice(a,M_READY,0);
}
static u32 fm_touch_point(fm_t *a,s32 *x,s32 *y) {
 if(!a->indev_w || !a->indev_point)return 0;
 u32 dev=*(u32 *)a->indev_w;if(!dev)return 0;s16 p[2]={-1,-1};
 ((void (*)(u32,s16 *))a->indev_point)(dev,p);
 if(p[0]<0 || p[1]<0)return 0;*x=p[0];*y=p[1];return 1;
}
static void fm_text_tap(fm_t *a,s32 px,s32 py) {
 s32 vx=14,vy=116;
#ifndef BT_HOST_TEST
 /* Verified N67 lv_obj_t absolute x1/y1 coordinates. */
 if(!bt_valid_ptr(a->viewport))return;
 vx=((s16 *)a->viewport)[10];vy=((s16 *)a->viewport)[11];
#endif
 if(px<vx || px>=vx+308 || py<vy || py>=vy+88)return;
 s32 tx=px-vx-10,ty=py-vy-10+fm_scroll_y(a)+(s32)(a->scroll_base*a->line_height);
 if(tx<0)tx=0;if(ty<0)ty=0;
 u32 target=(u32)ty/a->line_height;
 if(target<a->editor_prefix)target=0;else target-=a->editor_prefix;
 const u8 *s=a->view==V_EDIT?a->edit:a->input;
 u32 n=a->view==V_EDIT?a->edit_len:a->input_len,line=0,x=0,pos=n;
 for(u32 i=0;i<n;) {
  u32 end=fm_next(s,i,n),c,w=fm_text_step(a,s,i,end,&c);
  if(c==13){i=end;continue;}
  if(c!=10 && x && x+w>284){if(line==target){pos=i;break;}line++;x=0;}
  if(line==target){if(c==10 || tx<(s32)(x+w/2)){pos=i;break;}}
  if(c==10){line++;x=0;}else x+=w;i=end;
 }
 if(a->view==V_EDIT)a->cursor=pos;else a->input_cursor=pos;
 a->caret_follow=1;fm_notice(a,M_READY,0);
}
void bt_app_event(u32 *e) {
 if(!e || !e[3])return;u32 *ctx=(u32 *)e[3];bt_ui_t *u=(bt_ui_t *)ctx[0];fm_t *a=fm_state(u);
 if(!a || u->status!=2)return;u32 code=((u8 *)e)[8],action=ctx[1];
 if(code==1){a->swipe_block=a->row_hold=0;a->press_y=fm_scroll_y(a);a->press_action=action;
  a->press_generation=a->listing_generation;
  if(action>=100 && action<100+FM_LIST_ROWS && action-100<a->count){u32 i=action-100;
   a->press_type=a->entries[i].type;fm_join(a->press_path,a->cwd,a->entries[i].name);
  }
 }
 if(action==901 && code==a->scroll_begin){a->swipe_block=1;a->touch=a->key_repeat=a->row_hold=a->text_pressed=0;return;}
 if(action==901 && (a->view==V_EDIT || a->view==V_PROMPT) && !a->job_state){
  if(code==1)a->text_pressed=fm_touch_point(a,&a->text_press_x,&a->text_press_y);
  else if(code==3)a->text_pressed=0;
  else if(code==2 || code==7){s32 px,py;
   if(a->text_pressed && fm_touch_point(a,&px,&py)){
    s32 dx=px-a->text_press_x,dy=py-a->text_press_y,moved=fm_scroll_y(a)-a->press_y;
    if(dx>6 || dx< -6 || dy>6 || dy< -6 || moved>4 || moved< -4)a->text_pressed=0;
    else if(code==7 && !a->swipe_block)fm_text_tap(a,px,py);
   }if(code==7)a->text_pressed=0;
  }return;
 }
 if(action==900 || action==901)return;
 /* A pressed Enter can submit and hide itself before RELEASED arrives. Clear
  * the hold even when layout has already removed the sender's action. */
 if(code==3 || code==8){a->touch=a->key_repeat=0;if(code==3)a->row_hold=0;return;}
 if(a->swipe_block)return;
 if(!action)return;
 a->now=((u32 (*)(void))a->tick_get)();
 if(action>=200 || (action>=50 && action<=55)) {
  if(code==1 && !a->touch){a->touch=action;a->key_repeat=0;fm_action(u,action,0);}
  else if(code==5 && (a->view==V_EDIT || a->view==V_PROMPT)) {
   if(action==52){a->key_repeat=1;a->repeat_at=a->now;}
   else if(action==54 || action==55){u32 *cursor=a->view==V_EDIT?&a->cursor:&a->input_cursor;
    *cursor=action==54?0:a->view==V_EDIT?a->edit_len:a->input_len;a->caret_follow=1;fm_notice(a,M_READY,0);}
  }else if(code==3 || code==8){a->touch=a->key_repeat=0;}return;
 }
 /* Wait until CLICKED to change layout: replacing a held row's context during
  * LONG_PRESSED would make its release activate a different menu button. */
 if(code==5 && action>=100 && action<100+FM_LIST_ROWS)a->row_hold=a->touch=action;
 else if(code==7){s32 moved=fm_scroll_y(a)-a->press_y;
  if(action>=100 && action<100+FM_LIST_ROWS){
   if(moved>4 || moved< -4 || (a->press_action && (a->press_action!=action || a->press_generation!=a->listing_generation))){a->row_hold=a->touch=0;return;}
   u32 i=action-100;u8 path[FM_PATH];
   if(a->press_action && (i>=a->count || a->press_type!=a->entries[i].type || !fm_join(path,a->cwd,a->entries[i].name) || !fm_same(path,a->press_path)))return;
  }
  u32 held=a->row_hold==action || a->touch==action;a->touch=a->row_hold=0;fm_action(u,action,held);}
 else if(code==3 || code==8)a->touch=0;
}
static void fm_scroll_poll(bt_ui_t *u) {
 fm_t *a=fm_state(u);if(!a->viewport || u->build!=100 || a->scroll_view!=a->view+1 || a->scroll_sync)return;
 if(a->view!=V_FILES && a->view!=V_VIEW && a->view!=V_TERM && a->view!=V_EDIT && a->view!=V_PROMPT)return;
 u32 unit=a->view==V_FILES?FM_ROW_HEIGHT:a->line_height;
 s32 y=fm_scroll_y(a)+(s32)(a->scroll_base*unit);if(y<0)y=0;
 s32 *position=a->view==V_FILES?&a->list_y:a->view==V_TERM?&a->term_y:a->view==V_EDIT || a->view==V_PROMPT?&a->editor_y:&a->text_y;
 if(y!=*position){if((u32)y/unit!=(u32)*position/unit)a->dirty=1;*position=y;}
 if(a->view==V_TERM){a->term_follow=(u32)y+270+4>=a->content_lines*unit+10;return;}
 if(a->view==V_EDIT || a->view==V_PROMPT){a->caret_follow=0;a->editor_top=(u32)y/unit;return;}
 if(a->job_state || a->error)return;
 u32 top=(u32)y/unit;
 if(a->view==V_FILES){
  if(top<a->skip || (top+7>a->skip+a->count && a->skip+a->count<a->total)){
   a->skip=top>2?top-2:0;a->list_window=1;fm_job(u,J_LIST,a->cwd,0);
  }return;
 }
 /* Keep overlapping byte windows for files larger than the resident buffer.
  * Reposition around the same visible byte and sub-line pixel after I/O. */
 u32 next=a->page_offset;
 if(top<2 && next)next=next>FM_EDIT/2?next-FM_EDIT/2:0;
 else if(top+18>=a->content_lines && (u64)next+a->page_len<a->file_size){
  u32 line=top>5?top-5:0;next+=a->hex?line*6:fm_text_scan(a,a->edit,a->page_len,line,1);
 }
 if(next!=a->page_offset){
  a->view_anchor=a->page_offset+(a->hex?top*6:fm_text_scan(a,a->edit,a->page_len,top,1));
  a->anchor_pixel=(u32)y%unit;a->page_offset=next;a->text_window=1;fm_job(u,J_PAGE,a->path,0);
 }
}
void bt_app_tick(u32 *timer) {
 if(!timer)return;bt_ui_t *u=(bt_ui_t *)timer[3];fm_t *a=fm_state(u);if(!a)return;
 a->now=((u32 (*)(void))a->tick_get)();
 if(u->status==2 && a->touch==52 && a->key_repeat && (s32)(a->now-a->repeat_at)>=100){
  a->repeat_at=a->now;fm_action(u,52,0);
 }
 if(a->confirm && (s32)(a->now-a->confirm_until)>=0){a->confirm=0;a->dirty=1;}
 if(u->status==2)fm_scroll_poll(u);
 fm_terminal_poll(u);
 if(a->job_state==2) {
  fm_barrier();u32 kind=a->job_kind,ret=a->job_ret;
  fm_notice(a,a->job_message,ret);a->job_state=0;
  if(!ret && kind==J_FIFO){if(u->status==2)fm_terminal_spawn(u);else a->pending_script=0;}
  if(ret && kind==J_FIFO)a->pending_script=0;
  if(ret && kind==J_LOAD){if(a->view==a->job_view)a->view=V_FILE;a->editing=a->edit_len=0;a->edit[0]=0;}
  if(ret && kind==J_LIST)a->count=0;
  if(ret && kind==J_PAGE){a->page_len=a->text_window=0;a->text_y=0;a->scroll_sync=1;}
  if(!ret && kind==J_INSPECT && u->status==2 && a->view==a->job_view){
   if(a->format>=M_PNG && a->format<=M_LVGL){a->view=V_IMAGE;
    if(a->format==M_BMP)fm_job(u,J_BITMAP,a->path,0);else fm_image_prepare(a);
   }else {a->view=V_VIEW;a->hex=a->format==M_HEX;fm_job(u,J_PAGE,a->path,0);}
  }
  if(!ret && kind==J_PAGE){
   if(a->text_window){u32 byte=a->view_anchor>a->job_offset?a->view_anchor-a->job_offset:0;
    if(byte>a->page_len)byte=a->page_len;
    u32 line=a->hex?byte/6:fm_text_scan(a,a->edit,byte,0,0)-1;
    a->text_y=(s32)(line*a->line_height+a->anchor_pixel);a->text_window=0;
   }a->scroll_sync=1;
  }
  if(ret && (kind==J_INSPECT || kind==J_BITMAP) && a->view==a->job_view){a->view=V_INFO;}
  if(!ret && (kind==J_NEWFILE || kind==J_NEWDIR || kind==J_COPY || kind==J_MOVE || kind==J_DELETE)) {
   if(kind==J_MOVE){if(fm_same(a->path,a->request))fm_copy(a->path,FM_PATH,a->destination);
    if(a->clipboard && fm_same(a->clip,a->request))fm_copy(a->clip,FM_PATH,a->destination);}
   if(kind==J_DELETE && fm_same(a->clip,a->request)){a->clipboard=0;a->clip[0]=0;}
   if(a->view!=V_TERM){a->view=V_FILES;fm_job(u,J_LIST,a->cwd,0);}
  }
  if(kind==J_STOP)a->stop_requested=0;
 }
 if(a->stop_requested && !a->job_state){if(a->term_pid)fm_job(u,J_STOP,0,0);else a->stop_requested=0;}
 /* NSH can execute a shell script inside the console task itself. Interrupt
  * restarts our console too, so such a script cannot monopolize the session. */
 if(a->term_pending && !a->term_state && !a->job_state && u->status==2 && !a->stop_requested){
  if(a->reset_pending){a->terminal[0]=0;a->term_len=a->term_scroll=a->ansi=0;a->reset_pending=0;}
  a->term_pending=0;fm_job(u,J_FIFO,0,0);
 }
 if(u->status==2)bt_ui_step(u,0);
 /* Pause the independent UI timer after background cleanup. The registrar
  * retains its own timer and does not own this timer or its context. */
 else if(a->timer && !a->job_state && !a->term_state && !a->stop_requested)
  ((u8 *)a->timer)[0x14]|=1u;
}
u32 bt_pg_signal(u32 *p,u32 code,u32 arg) {bt_ui_t *u=fm_ui(p);if(u){u->sigs++;u->last_sig=code;u->last_sig_arg=arg;}return 0;}
u32 bt_pg_create(u32 *p,u32 parent) {
 bt_ui_t *u=fm_ui(p);fm_t *a=fm_state(u);if(!a)return 0xFFFFFFFFu;
 u->creates++;u->root=parent?parent:p[11];u->parent=u->root;u->label=0;u->build=0;u->status=1;
 a->caret=a->heading=a->page_indicator=a->image=a->viewport=a->spacer=a->scroll_label=0;for(u32 i=0;i<FM_LIST_ROWS;i++)a->details[i]=0;
 a->text_pressed=0;a->scroll_view=0;a->scroll_sync=1;
 for(u32 i=0;i<FM_ROWS;i++)a->objects[i]=a->labels[i]=0;a->dirty=1;
 if(u->reg){bt_reg_t *r=(bt_reg_t *)u->reg;r->ui=(u32)u;r->cfg=u->cfg;}return 0;
}
u32 bt_pg_resume(u32 *p) {
 bt_ui_t *u=fm_ui(p);fm_t *a=fm_state(u);if(!a)return 0;
 u->resumes++;u->status=2;a->touch=a->swipe_block=0;a->dirty=1;
 if(!a->term_pid && a->job_kind!=J_STOP)a->stop_requested=0;
 if(!a->initialized){a->initialized=1;a->term_in=a->term_out=-1;a->message=M_READY;a->term_follow=1;
  a->cwd[0]='/';a->cwd[1]='d';a->cwd[2]='a';a->cwd[3]='t';a->cwd[4]='a';a->cwd[5]=0;fm_job(u,J_LIST,a->cwd,0);}
 if(!a->timer)a->timer=((u32 (*)(u32,u32,u32))a->timer_create)(a->timer_cb,50,(u32)u);
 else ((u8 *)a->timer)[0x14]&=(u8)~1u;
 if(!a->timer){u->last_ret=209;fm_notice(a,M_ERROR,209);}
 /* Finish the bounded object tree on the UI thread before returning. File
  * jobs remain asynchronous; initial paint no longer needs 44 timer rounds. */
 for(u32 step=0;step<FM_ROWS+2 && u->build!=100 && u->build!=8;step++)bt_ui_step(u,0);
 if(u->build==8 && u->label){u8 message[64];fm_copy(message,sizeof(message),(u8 *)"UI error ");
  fm_num(message,9,sizeof(message),u->last_ret);
  ((void (*)(u32,u32))u->label_set_text)(u->label,(u32)message);}
 return 0;
}
u32 bt_pg_pause(u32 *p) {bt_ui_t *u=fm_ui(p);fm_t *a=fm_state(u);if(a){u->pauses++;u->status=3;a->stop_requested=1;a->pending_script=a->term_pending=a->reset_pending=0;}return 0;}
u32 bt_pg_destroy(u32 *p) {
 bt_ui_t *u=fm_ui(p);fm_t *a=fm_state(u);if(!a)return 0;
 u->destroys++;u->status=4;a->stop_requested=1;a->pending_script=a->term_pending=a->reset_pending=0;
 /* Manager owns root and children. A running worker retains only resident data. */
 u->root=u->label=u->parent=u->build=0;
 a->caret=a->heading=a->page_indicator=a->image=a->viewport=a->spacer=a->scroll_label=0;for(u32 i=0;i<FM_LIST_ROWS;i++)a->details[i]=0;
 for(u32 i=0;i<FM_ROWS;i++)a->objects[i]=a->labels[i]=0;
 if(u->reg){bt_reg_t *r=(bt_reg_t *)u->reg;r->ui=r->cfg=0;}return 0;
}
