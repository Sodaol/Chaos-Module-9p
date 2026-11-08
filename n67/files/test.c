/* Execute the actual core with 32-bit pointers and a hostile in-memory FS. */
#define BT_HOST_TEST 1
#include "platform_n67.c.in"
#include "core.c"
#define CHECK(x) do {if(!(x))return __LINE__;} while(0)
typedef struct {u8 path[512],data[40000];u32 mode,n,used;} node_t;
typedef struct {s32 node;u32 at,flags;} fd_t;
static node_t nodes[16];static fd_t fds[32];
static fm_t a;static bt_ui_t u;static u32 page_node[28],timer_words[6],messages[M_COUNT];
static u32 err,write_fail,sync_fail,rename_fail,read_eintr,read_chunk,write_chunk;
static u32 external_change;static u8 last_text[256];
static u32 spawned,fail_spawn,now,objects,labels,text_calls,ui_bad,fail_object,fail_event;
static u32 killed[16],kill_n,alive,dup_calls,fake_tcb;
static u32 fifo_calls,fifo_fail_at,open_calls,open_fail_at,dup_fail_at;
static u8 dir_entry[257];static u32 dir_index;
static struct {u8 prefix[512];u32 index,used,proc;} dirs[16];
static u32 size_was[64],height_was[64];
typedef struct {u32 id,parent,kind,flags,x,y,w,h,align,bg,opacity,fg,font,radius,border,border_color,text_align,letter_space,line_space;u8 text[1024];} ui_record_t;
static ui_record_t records[128];static u32 record_n;
static u8 catalog[4096];
static u8 indev[80];static u32 indev_ptr;static u32 bitmap[308*280];
static u32 decoder_bad,decoder_header,decode_calls,image_source,image_zoom_value,decoder_real_file,clamp_scroll;
static s32 scroll_y_value;static u32 scroll_set_calls,scroll_direction;
static ui_record_t *record(u32 id){for(u32 i=0;i<record_n;i++)if(records[i].id==id)return &records[i];return 0;}
static void record_add(u32 id,u32 parent,u32 kind){ui_record_t *r=&records[record_n++];r->id=id;r->parent=parent;r->kind=kind;r->opacity=255;r->fg=0xFFDCE5EE;r->font=18;}
static u8 *s(const char *v){return (u8 *)v;}
static void zero(void *p,u32 n){for(u32 i=0;i<n;i++)((u8 *)p)[i]=0;}
static s32 find(const u8 *path){for(u32 i=0;i<16;i++)if(nodes[i].used && fm_same(nodes[i].path,path))return i;return -1;}
static s32 add(const u8 *path,u32 mode,const u8 *data){for(u32 i=0;i<16;i++)if(!nodes[i].used){
 nodes[i].used=1;nodes[i].mode=mode;fm_copy(nodes[i].path,512,path);
 nodes[i].n=data?fm_len(data):0;if(data)fm_copy(nodes[i].data,40000,data);return i;}return -1;}
static u32 errno_mock(void){return (u32)&err;}
static s32 open_mock(u32 p,u32 f,u32 mode){s32 n=find((u8 *)p);
 open_calls++;if(open_fail_at==open_calls){err=13;return -1;}
 if(n>=0 && (f&4) && (f&8)){err=17;return -1;}
 if(n<0){if(!(f&4)){err=2;return -1;}n=add((u8 *)p,0x8000|mode,0);}
 if(n<0){err=28;return -1;}if(f&32)nodes[n].n=0;
 for(u32 i=3;i<32;i++)if(fds[i].node<0){fds[i].node=n;fds[i].at=(f&16)?nodes[n].n:0;fds[i].flags=f;return i;}
 err=24;return -1;
}
static s32 close_mock(s32 fd){if(fd<3||fd>=32||fds[fd].node<0){err=9;return -1;}fds[fd].node=-1;return 0;}
static s32 read_mock(s32 fd,u32 p,u32 cap){if(fd<3||fd>=32||fds[fd].node<0){err=9;return -1;}
 if(read_eintr){read_eintr--;err=4;return -1;}
 node_t *n=&nodes[fds[fd].node];u32 count=n->n-fds[fd].at;if(count>cap)count=cap;
 if(read_chunk && count>read_chunk)count=read_chunk;
 if(!count && ((n->mode&0xF000)==0x1000 || (n->mode&0xF000)==0x2000)){err=11;return -1;}
 for(u32 i=0;i<count;i++)((u8 *)p)[i]=n->data[fds[fd].at++];return count;
}
static s32 write_mock(s32 fd,u32 p,u32 count){if(write_fail){err=28;return -1;}
 if(fd<3||fd>=32||fds[fd].node<0){err=9;return -1;}
 if(write_chunk && count>write_chunk)count=write_chunk;
 node_t *n=&nodes[fds[fd].node];if(fds[fd].at+count>40000){err=28;return -1;}
 for(u32 i=0;i<count;i++)n->data[fds[fd].at++]=((u8 *)p)[i];
 if(fds[fd].at>n->n)n->n=fds[fd].at;n->data[n->n]=0;return count;
}
static s64 seek_mock(s32 fd,s64 off,u32 whence){if(whence || off<0 || fd<3 || fds[fd].node<0){err=22;return -1;}
 fds[fd].at=off;return off;}
static s32 stat_mock(u32 p,u32 out){s32 n=find((u8 *)p);if(n<0){err=2;return -1;}
 u32 *b=(u32 *)out;zero(b,96);b[2]=nodes[n].mode;b[6]=nodes[n].n;return 0;}
static s32 unlink_mock(u32 p){s32 n=find((u8 *)p);if(n<0){err=2;return -1;}nodes[n].used=0;return 0;}
static s32 rename_mock(u32 p,u32 q){s32 n=find((u8 *)p);if(n<0){err=2;return -1;}
 if(rename_fail==1 || (rename_fail==2 && (nodes[n].mode&0xF000)==0x4000)){err=5;return -1;}
 u8 original[512];fm_copy(original,512,(u8 *)p);u32 len=fm_len(original);
 s32 old=find((u8 *)q);if(old>=0)nodes[old].used=0;
 if((nodes[n].mode&0xF000)==0x4000)for(u32 i=0;i<16;i++)if(nodes[i].used && i!=(u32)n){
  u32 j=0;while(j<len && nodes[i].path[j]==original[j])j++;
  if(j==len && nodes[i].path[len]=='/'){u8 path[512];u32 at=fm_cat(path,0,512,(u8 *)q);
   fm_cat(path,at,512,nodes[i].path+len);fm_copy(nodes[i].path,512,path);}}
 fm_copy(nodes[n].path,512,(u8 *)q);return 0;}
static s32 sync_mock(s32 fd){(void)fd;if(sync_fail){err=5;return -1;}
 if(external_change){s32 i=find(s("/data/x"));fm_copy(nodes[i].data,40000,s("changed"));nodes[i].n=7;}return 0;}
static s32 mkdir_mock(u32 p,u32 mode){if(find((u8 *)p)>=0){err=17;return -1;}return add((u8 *)p,0x4000|mode,0)>=0?0:-1;}
static s32 fifo_mock(u32 p){fifo_calls++;u8 *path=(u8 *)p;
 if((path[1]=='t' && path[2]=='m' && path[3]=='p') || find(path)>=0){err=17;return -1;}
 if(fifo_fail_at==fifo_calls){err=28;return -1;}
 if(add(path,0x21B6,0)<0){err=12;return -1;}return 0;}
static s32 dup_mock(u32 tcb,s32 from,s32 to){(void)from;(void)to;dup_calls++;if(tcb!=fake_tcb)return -22;
 return dup_calls==dup_fail_at?-9:0;}
static u32 nsh_mock(u32 argc,u32 argv){(void)argc;(void)argv;return 0;}
static u32 opendir_mock(u32 p){s32 n=find((u8 *)p);
 if(!fm_same((u8 *)p,s("/data")) && !fm_same((u8 *)p,s("/proc")) && (n<0 || (nodes[n].mode&0xF000)!=0x4000)){err=2;return 0;}
 for(u32 i=0;i<16;i++)if(!dirs[i].used){dirs[i].used=1;dirs[i].index=0;dirs[i].proc=fm_same((u8 *)p,s("/proc"));
  fm_copy(dirs[i].prefix,512,(u8 *)p);u32 len=fm_len(dirs[i].prefix);dirs[i].prefix[len++]='/';dirs[i].prefix[len]=0;return i+1;}
 err=24;return 0;}
static u32 readdir_mock(u32 dir){u32 d=dir-1;while(dirs[d].index<16){node_t *n=&nodes[dirs[d].index++];u8 *base=dirs[d].prefix;u32 len=fm_len(base);
 if(!n->used)continue;u32 i=0;while(i<len && base[i]==n->path[i])i++;if(i!=len)continue;
 u8 *name=n->path+len;if(!*name)continue;
 if(dirs[d].proc){u32 k=0;while(name[k] && name[k]!='/')k++;for(u32 j=0;j<k;j++)dir_entry[1+j]=name[j];dir_entry[1+k]=0;}
 else {u32 k=0;while(name[k] && name[k]!='/')k++;if(name[k])continue;fm_copy(dir_entry+1,256,name);}
 u32 type=n->mode&0xF000;dir_entry[0]=type==0x4000?4:type==0x8000?8:type==0xA000?10:0;return (u32)dir_entry;
 }err=0;return 0;}
static s32 closedir_mock(u32 dir){dirs[dir-1].used=0;return 0;}
static s32 task_mock(u32 name,u32 pri,u32 stack,u32 cb,u32 args){(void)name;(void)pri;(void)stack;(void)cb;(void)args;
 spawned++;if(fail_spawn){err=12;return -1;}return 42;}
static s32 kill_mock(u32 pid,u32 sig){if(!sig){if(alive)return 0;err=3;return -1;}if(kill_n<16)killed[kill_n++]=pid;return 0;}
static u32 tick_mock(void){return now;}
static u32 object_mock(u32 parent){if(!parent)ui_bad++;if(fail_object)return 0;u32 id=1000+objects++;record_add(id,parent,0);return id;}
static u32 label_mock(u32 parent){if(!parent)ui_bad++;u32 id=2000+labels++;record_add(id,parent,1);return id;}
static void prop_mock(u32 o,u32 p,u32 v,u32 sel){(void)sel;ui_record_t *r=record(o);if(!r)return;
 if(p==0x20)r->bg=v;if(p==0x21)r->opacity=v;if(p==0x55)r->fg=v;if(p==0x57)r->font=v;
 if(p==0x58)r->letter_space=v;if(p==0x59)r->line_space=v;
 if(p==0x0B)r->radius=v;if(p==0x32)r->border=v;if(p==0x30)r->border_color=v;if(p==0x5B)r->text_align=v;}
static void add_flag_mock(u32 o,u32 flags){ui_record_t *r=record(o);if(r)r->flags|=flags;}
static void clear_flag_mock(u32 o,u32 flags){ui_record_t *r=record(o);if(r)r->flags&=~flags;}
static void align_mock(u32 o,u32 align,u32 x,u32 y){ui_record_t *r=record(o);if(r){r->align=align;r->x=x;r->y=y;}}
static void size_mock(u32 o,u32 w,u32 h){if(o>=1000 && o<1064){size_was[o-1000]=w;height_was[o-1000]=h;}
 ui_record_t *r=record(o);if(r){r->w=w;r->h=h;}}
static void text_mock(u32 l,u32 p){if(!l || !p)ui_bad++;text_calls++;if(p)fm_copy(last_text,256,(u8 *)p);
 ui_record_t *r=record(l);if(r && p)fm_copy(r->text,sizeof(r->text),(u8 *)p);}
static u32 event_mock(u32 o,u32 cb,u32 code,u32 ctx){(void)o;(void)cb;(void)code;
 if(((u32 *)ctx)[0]!=(u32)&u)ui_bad++;return !fail_event;}
static u32 font_mock(u32 name,u32 size,u32 style){(void)name;(void)style;return size;}
/* Independent label layout model: font height 20 at size 18, glyph advances
 * from the fixture, plus the ACTUAL style writes captured above. Do not use
 * fm_advance/line_height here: v5's hidden letter spacing must make this fail. */
static u32 draw_width(u32 c){return c=='i'?5:c=='W'?16:c<128?10:18;}
static u32 draw_position(ui_record_t *r,u32 wanted,u32 *px,u32 *py){
 u32 x=0,y=0,glyph=0,n=fm_len(r->text),unit=r->font+2+r->line_space;
 for(u32 i=0;i<=n;){u32 end=i<n?fm_next(r->text,i,n):i,c=i<n?fm_codepoint(r->text,i,end):0;
  u32 w=draw_width(c);
  if(i<n && c==10){x=0;y+=unit;i=end;continue;}
  if(i<n && c!=10 && x && x+w>r->w){x=0;y+=unit;}
  if(glyph==wanted){*px=x;*py=y;return 1;}
  if(i==n)break;
  x+=w+r->letter_space;glyph++;i=end;
 }return 0;
}
static u32 draw_height(ui_record_t *r){
 u32 x=0,rows=1,n=fm_len(r->text);
 for(u32 i=0;i<n;){u32 end=fm_next(r->text,i,n),c=fm_codepoint(r->text,i,end),w=draw_width(c);
  if(c==10){x=0;rows++;}else{if(x && x+w>r->w){rows++;x=0;}x+=w+r->letter_space;}i=end;
 }return (rows-1)*(r->font+2+r->line_space)+r->font+2;
}
static u32 allocate_mock(u32 n){return n<=sizeof(bitmap)?(u32)bitmap:0;}
static u32 image_mock(u32 parent){u32 id=object_mock(parent);record(id)->kind=2;return id;}
static void image_src_mock(u32 obj,u32 src){(void)obj;image_source=src;}
static void image_zoom_mock(u32 obj,u32 zoom){(void)obj;image_zoom_value=zoom;}
static u32 image_info_mock(u32 src,u32 header){decode_calls++;
 if(decoder_real_file){const u8 *path=(u8 *)src;
  /* Mirror target lv_fs: first character is its registered driver letter /.
   * Target PNG info reads 24 bytes, signature, big-endian IHDR dimensions. */
  s32 node=path[0]=='/'?find(path):-1;if(node<0 || nodes[node].n<24)return 0;
  u8 *p=nodes[node].data;if(p[0]!=137 || p[1]!='P' || p[2]!='N' || p[3]!='G')return 0;
  u32 w=fm_be32(p+16),h=fm_be32(p+20);*(u32 *)header=5|(w<<10)|(h<<21);return 1;
 }*(u32 *)header=decoder_header;return decoder_bad?0:1;}
static u32 timer_mock(u32 cb,u32 period,u32 context){(void)cb;CHECK(period==50 && context==(u32)&u);timer_words[3]=context;return (u32)timer_words;}
static s32 scroll_get_mock(u32 o){(void)o;return scroll_y_value;}
static void scroll_to_mock(u32 o,s32 y,u32 anim){(void)anim;
 if(clamp_scroll){ui_record_t *v=record(o),*sp=record(a.spacer);s32 max=(s32)sp->h-(s32)v->h;
  if(max<0)max=0;if(y>max)y=max;if(y<0)y=0;}
 scroll_y_value=y;scroll_set_calls++;}
static void point_mock(u32 dev,s16 *p){p[0]=((s16 *)dev)[4];p[1]=((s16 *)dev)[5];}
static void scroll_dir_mock(u32 o,u32 dir){(void)o;scroll_direction=dir;}
static void parent_mock(u32 o,u32 parent){ui_record_t *r=record(o);if(r)r->parent=parent;}
static void reset(void){zero(&a,sizeof(a));zero(&u,sizeof(u));zero(nodes,sizeof(nodes));zero(fds,sizeof(fds));zero(dirs,sizeof(dirs));zero(page_node,sizeof(page_node));zero(timer_words,sizeof(timer_words));
 zero(records,sizeof(records));record_n=0;record_add(100,0,0);records[0].w=336;records[0].h=480;
 fifo_calls=fifo_fail_at=open_calls=open_fail_at=dup_calls=dup_fail_at=0;fake_tcb=77;
 for(u32 i=0;i<32;i++)fds[i].node=-1;for(u32 i=0;i<M_COUNT;i++)messages[i]=(u32)s("ready");
 messages[M_PART]=(u32)s(".nfm.part.");messages[M_FIFO_IN]=(u32)s("/tmp/nfm.in");messages[M_FIFO_OUT]=(u32)s("/tmp/nfm.out");
 messages[M_PROC]=(u32)s("/proc");messages[M_STATUS]=(u32)s("/status");messages[M_PARENT]=(u32)s("Parent:");
 messages[M_LOWER]=(u32)s("qwertyuiopasdfghjklzxcvbnm");messages[M_UPPER]=(u32)s("QWERTYUIOPASDFGHJKLZXCVBNM");
 messages[M_SYMBOL1]=(u32)s("1234567890-=[]\\;',./!@#$%^");messages[M_SYMBOL2]=(u32)s("&*()_+{}|:\"<>?`~=");
 a.magic=FM_MAGIC;a.abi=1;a.state_size=sizeof(a);a.messages=(u32)messages;
 a.open=(u32)open_mock;a.close=(u32)close_mock;a.read=(u32)read_mock;a.write=(u32)write_mock;
 a.seek=(u32)seek_mock;a.stat=(u32)stat_mock;a.rename=(u32)rename_mock;a.unlink=(u32)unlink_mock;
 a.mkdir=(u32)mkdir_mock;a.rmdir=(u32)unlink_mock;a.sync=(u32)sync_mock;
 a.mkfifo=(u32)fifo_mock;a.files_dup2=(u32)dup_mock;a.current_tcb_w=(u32)&fake_tcb;a.nsh_main=(u32)nsh_mock;
 a.opendir=(u32)opendir_mock;a.readdir=(u32)readdir_mock;a.closedir=(u32)closedir_mock;
 a.errno_ptr=(u32)errno_mock;a.task_create=(u32)task_mock;a.kill=(u32)kill_mock;a.tick_get=(u32)tick_mock;
 a.timer_create=(u32)timer_mock;a.event_add=(u32)event_mock;a.font_create=(u32)font_mock;
 a.clear_flags=16;a.gesture_flags=65536;a.press_lock=8192;
 a.indev_w=(u32)&indev_ptr;indev_ptr=(u32)indev;zero(indev,sizeof(indev));
 a.gesture_event=21;a.dir_top=4;a.dir_bottom=8;a.allocate=(u32)allocate_mock;
 a.scroll_get_y=(u32)scroll_get_mock;a.scroll_to_y=(u32)scroll_to_mock;a.scroll_dir=(u32)scroll_dir_mock;
 a.set_parent=(u32)parent_mock;a.scroll_begin=22;a.scroll_momentum=32;
 a.line_height=22;a.term_follow=1;scroll_y_value=scroll_set_calls=scroll_direction=0;
 a.image_create=(u32)image_mock;a.image_src=(u32)image_src_mock;a.image_info=(u32)image_info_mock;a.image_zoom=(u32)image_zoom_mock;
 decoder_bad=decode_calls=image_source=image_zoom_value=decoder_real_file=clamp_scroll=0;decoder_header=5|(200<<10)|(200<<21);
 a.indev_point=(u32)point_mock;
 a.term_in=a.term_out=-1;u.runtime=(u32)&a;u.magic=BT_UI_MAGIC;u.page=(u32)page_node;
 u.status=2;page_node[1]=(u32)&u;page_node[11]=100;u.root=100;
 u.obj_create=(u32)object_mock;u.label_create=(u32)label_mock;u.label_set_text=(u32)text_mock;
 u.set_size=(u32)size_mock;u.set_prop=(u32)prop_mock;u.clear_flag=(u32)clear_flag_mock;u.add_flag=(u32)add_flag_mock;u.align=(u32)align_mock;
 fm_copy(a.cwd,512,s("/data"));now=123456;err=write_fail=sync_fail=rename_fail=read_eintr=read_chunk=write_chunk=0;
 spawned=fail_spawn=objects=labels=text_calls=ui_bad=fail_object=fail_event=kill_n=external_change=0;alive=1;
}
static void req(u32 job,const char *src,const char *dst){a.job_kind=job;a.job_state=1;
 if(src)fm_copy(a.request,512,s(src));if(dst)fm_copy(a.destination,512,s(dst));
 fm_name(a.worker_name,(u32)&u);u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);}
static u32 changed(const char *path,const char *value){s32 n=find(s(path));return n>=0 && fm_same(nodes[n].data,s(value));}
static u32 open_fds(void){u32 n=0;for(u32 i=3;i<32;i++)if(fds[i].node>=0)n++;return n;}
u32 test_state_size(void){return sizeof(a);}
u32 test_debug(u32 v){return v==6?a.cursor:v==7?(u32)a.editor_y:v==8?(u32)scroll_y_value:v==9?a.editor_prefix:v==0?a.job_ret:v==1?a.job_message:v==2?err:v==3?(u32)nodes:v==4?(u32)a.request:(u32)a.destination;}
u32 run_test(u32 which){reset();
 if(which==0){u8 out[512];CHECK(fm_join(out,s("/data/a"),s("../b/./c")));CHECK(fm_same(out,s("/data/b/c")));
  CHECK(fm_join(out,s("/data"),s("../../..")));CHECK(fm_same(out,s("/")));CHECK(!fm_join(out,s("/"),s("bad\nfile")));}
 if(which==1){CHECK(fm_utf8(s("a\xE4\xB8\xAD\n"),5));CHECK(!fm_utf8(s("\xC0\x80"),2));CHECK(!fm_utf8(s("\xED\xA0\x80"),3));
  CHECK(!fm_utf8(s("\xF4\x90\x80\x80"),4));CHECK(!fm_utf8(s("\xE4\xB8"),2));CHECK(!fm_utf8(s("a\0b"),3));}
 if(which==2){u8 b[12];fm_copy(b,12,s("a\xE4\xB8\xAD"));u32 n=4,c=4;fm_backspace(b,&n,&c);CHECK(n==1 && c==1 && b[0]=='a');
  CHECK(fm_insert(b,&n,&c,12,s("b"),1));CHECK(fm_same(b,s("ab")));CHECK(!fm_insert(b,&n,&c,3,s("c"),1));}
 if(which==3){add(s("/data/x"),0x81A4,s("hello\n"));read_chunk=2;read_eintr=1;req(J_LOAD,"/data/x",0);
  CHECK(a.job_ret==0 && a.editing && a.edit_len==6 && !open_fds());}
 if(which==4){s32 i=add(s("/data/x"),0x81A4,0);nodes[i].n=32769;req(J_LOAD,"/data/x",0);CHECK(a.job_ret && a.job_message==M_BIG);}
 if(which==5){s32 i=add(s("/data/x"),0x81A4,s("abc"));nodes[i].data[1]=0;req(J_LOAD,"/data/x",0);CHECK(a.job_ret && a.job_message==M_BINARY);}
 if(which>=6 && which<=10){add(s("/data/x"),0x81A4,s("old"));req(J_LOAD,"/data/x",0);CHECK(!a.job_ret);
  fm_copy(a.edit,FM_EDIT+1,s("new script\n"));a.edit_len=11;a.modified=1;write_chunk=2;
  if(which==7)write_fail=1;if(which==8)sync_fail=1;if(which==9)rename_fail=1;
  if(which==10){s32 i=find(s("/data/x"));fm_copy(nodes[i].data,40000,s("changed"));nodes[i].n=7;}
  req(J_SAVE,"/data/x","/data/x");CHECK(!open_fds());
  if(which==6){CHECK(!a.job_ret && changed("/data/x","new script\n") && !a.modified);}
  else {CHECK(a.job_ret && a.modified);CHECK(changed("/data/x",which==10?"changed":"old"));}
  for(u32 i=0;i<16;i++)if(nodes[i].used)CHECK(fm_same(nodes[i].path,s("/data/x")));
 }
 if(which==11){add(s("/data/x"),0x81A4,s("stream content"));read_chunk=3;write_chunk=2;req(J_COPY,"/data/x","/data/y");
  CHECK(!a.job_ret && changed("/data/y","stream content") && changed("/data/x","stream content") && !open_fds());}
 if(which==12){add(s("/data/x"),0x81A4,s("src"));add(s("/data/y"),0x81A4,s("keep"));req(J_COPY,"/data/x","/data/y");
  CHECK(a.job_ret && a.job_message==M_CONFLICT && changed("/data/y","keep"));}
 if(which==13){add(s("/data/x"),0x81A4,s("x"));req(J_MOVE,"/data/x","/data/y");CHECK(!a.job_ret && find(s("/data/x"))<0 && changed("/data/y","x"));}
 if(which==14){req(J_NEWFILE,0,"/data/new");CHECK(!a.job_ret && find(s("/data/new"))>=0);req(J_NEWFILE,0,"/data/new");CHECK(a.job_ret==17);}
 if(which==15){req(J_NEWDIR,0,"/data/sub");CHECK(!a.job_ret);req(J_DELETE,"/data/sub",0);CHECK(!a.job_ret && find(s("/data/sub"))<0);}
 if(which==16){for(u32 i=0;i<9;i++){u8 p[32];fm_copy(p,32,s("/data/f"));fm_num(p,7,32,i);add(p,0x81A4,s("x"));}
  a.job_skip=6;req(J_LIST,"/data",0);CHECK(!a.job_ret && a.total==10 && a.count==4 && a.entries[0].name[1]=='5');}
 if(which==17){CHECK(fm_job(&u,J_LIST,a.cwd,0));CHECK(a.job_state==1 && spawned==1);CHECK(!fm_job(&u,J_LOAD,a.cwd,0));CHECK(spawned==1);}
 if(which==18){fail_spawn=1;CHECK(!fm_job(&u,J_LIST,a.cwd,0));CHECK(!a.job_state && a.message==M_FAILED);}
 if(which==19){a.term_state=2;CHECK(fm_send(&a,s("echo test"),1));CHECK(a.term_send_len==10 && a.send[9]=='\n');
  a.pending_script=1;fm_copy(a.script_path,512,s("/data/a.sh"));fm_script(&a);CHECK(fm_same(a.send,s("echo test\n")) && a.pending_script==1);}
 if(which==20){a.term_state=2;a.pending_script=2;fm_copy(a.script_path,512,s("/data/a b.lua"));fm_copy(a.path,512,s("/data/wrong"));
  fm_script(&a);CHECK(fm_same(a.send,s("lua \"/data/a b.lua\"\n")));}
 if(which==21){a.term_state=2;a.pending_script=1;fm_copy(a.script_path,512,s("/data/\"bad"));fm_script(&a);CHECK(!a.term_send_len && a.message==M_NO_SCRIPT);}
 if(which==22){s32 i=add(s("/tmp/nfm.in"),0x1000,0);add(s("/tmp/nfm.out"),0x1000,s("OK\n"));
  a.term_state=2;a.term_pid=42;a.term_in=open_mock(messages[M_FIFO_IN],0x43,0);a.term_out=open_mock(messages[M_FIFO_OUT],0x43,0);
  CHECK(fm_send(&a,s("pwd"),1));write_chunk=1;
  for(u32 j=0;j<5;j++)fm_terminal_poll(&u);CHECK(!a.term_send_len && fm_same(nodes[i].data,s("pwd\n")) && fm_same(a.terminal,s("OK\n")));}
 if(which==23){add(s("/tmp/nfm.in"),0x1000,0);add(s("/tmp/nfm.out"),0x1000,0);a.term_state=2;a.term_pid=42;
  a.term_in=open_mock(messages[M_FIFO_IN],0x43,0);a.term_out=open_mock(messages[M_FIFO_OUT],0x43,0);alive=0;fm_terminal_poll(&u);
  CHECK(!a.term_state && !open_fds());}
 if(which==24){for(u32 i=0;i<20;i++){for(u32 j=0;j<1024;j++)a.io[j]='x';fm_terminal_text(&a,a.io,1024);}CHECK(a.term_len<=FM_TERM && a.discard>0 && !a.terminal[a.term_len]);}
 if(which==25){a.term_pid=10;fm_copy(a.terminal_name,12,s("NF00000100t"));add(s("/proc/10/status"),0x81A4,s("Name: other\nParent: 1\n"));
  fm_stop_job(&a,1);CHECK(kill_n==0 && a.term_state==3);}
 if(which==26){a.term_pid=10;fm_copy(a.terminal_name,12,s("NF00000100t"));
  add(s("/proc/10/status"),0x81A4,s("Name: NF00000100t\nParent: 1\n"));
  add(s("/proc/11/status"),0x81A4,s("Name: lua\nParent: 10\n"));
  add(s("/proc/12/status"),0x81A4,s("Name: child\nParent: 11\n"));
  add(s("/proc/13/status"),0x81A4,s("Name: system\nParent: 1\n"));
  fm_stop_job(&a,0);CHECK(kill_n==2 && killed[0]==12 && killed[1]==11);
  kill_n=0;fm_stop_job(&a,1);CHECK(kill_n==3 && killed[2]==10);}
 if(which==27){bt_pg_create(page_node,100);u.status=2;
  for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
  CHECK(u.build==100 && objects==47 && labels==60 && !ui_bad && text_calls>0);
  for(u32 i=0;i<FM_ROWS;i++)CHECK(a.contexts[i][0]==(u32)&u);
  a.view=V_EDIT;a.dirty=1;bt_ui_show(&u,0);
  CHECK(record(a.objects[37])->w==188 && record(a.objects[37])->h==44);
 }
 if(which==28){fail_event=1;bt_pg_create(page_node,100);u.status=2;bt_ui_step(&u,0);CHECK(u.build==8 && u.last_ret==106);}
 if(which==29){a.initialized=1;bt_pg_create(page_node,100);bt_pg_resume(page_node);CHECK(a.timer && u.status==2);
  bt_pg_pause(page_node);bt_app_tick(timer_words);CHECK(timer_words[5]&1);
  bt_pg_resume(page_node);CHECK(!(timer_words[5]&1));bt_pg_destroy(page_node);CHECK(!u.root && !u.label && !a.objects[0]);}
 if(which==30){a.view=V_EDIT;a.modified=1;fm_action(&u,2,0);CHECK(a.view==V_EDIT && a.confirm==2);
  fm_action(&u,2,0);CHECK(a.view==V_FILES && !a.modified);}
 if(which==31){a.view=V_FILES;a.count=1;a.entries[0].type=4;fm_copy(a.entries[0].name,256,s("dir"));
  u32 ctx[2]={(u32)&u,100},e[4]={0,0,5,(u32)ctx};bt_app_event(e);CHECK(a.view==V_FILES && a.touch==100);
  e[2]=7;bt_app_event(e);CHECK(a.view==V_FILE && a.touch==0 && !a.job_state);}
 if(which==32){a.view=V_EDIT;a.contexts[0][0]=(u32)&u;a.contexts[0][1]=200;
  u32 e[4]={0,0,1,(u32)a.contexts[0]};bt_app_event(e);e[2]=7;bt_app_event(e);e[2]=8;bt_app_event(e);
  CHECK(a.edit_len==1 && a.edit[0]=='q' && !a.touch);}
 if(which==33){u8 out[128];u32 n=fm_wrap(out,128,s("abc\nabcdef\nX"),12,2,3);CHECK(n==7 && fm_same(out,s("abc\nabc\n")));}
 if(which==34){a.view=V_EDIT;a.edit_len=8;a.cursor=4;fm_copy(a.edit,FM_EDIT+1,s("12345678"));
  u32 ctx[2]={(u32)&u,55},e[4]={0,0,1,(u32)ctx};bt_app_event(e);e[2]=5;bt_app_event(e);CHECK(a.cursor==8);
  e[2]=8;bt_app_event(e);ctx[1]=54;e[2]=1;bt_app_event(e);e[2]=5;bt_app_event(e);CHECK(a.cursor==0);}
 if(which==35){a.view=V_EDIT;a.edit_len=a.cursor=8;fm_copy(a.edit,FM_EDIT+1,s("12345678"));
  u32 ctx[2]={(u32)&u,52},e[4]={0,0,1,(u32)ctx};bt_app_event(e);e[2]=5;bt_app_event(e);
  timer_words[3]=(u32)&u;now+=101;bt_app_tick(timer_words);CHECK(a.edit_len==6);
  e[2]=8;bt_app_event(e);now+=200;bt_app_tick(timer_words);CHECK(a.edit_len==6);}
 if(which>=36 && which<=38){add(s("/data/src"),0x41ED,0);add(s("/data/src/a"),0x81A4,s("one"));
  add(s("/data/src/sub"),0x41ED,0);add(s("/data/src/sub/b"),0x81A4,s("two"));
  if(which==37)write_fail=1;if(which==38)rename_fail=2;
  req(J_COPY,"/data/src","/data/dst");CHECK(changed("/data/src/a","one") && changed("/data/src/sub/b","two") && !open_fds());
  if(which==36)CHECK(!a.job_ret && changed("/data/dst/a","one") && changed("/data/dst/sub/b","two"));
  else {CHECK(a.job_ret && find(s("/data/dst"))<0);for(u32 i=0;i<16;i++)if(nodes[i].used)CHECK(nodes[i].path[6]=='s');}
  for(u32 i=0;i<16;i++)CHECK(!dirs[i].used);
 }
 if(which==39){add(s("/data/src"),0x41ED,0);add(s("/data/src/a"),0x81A4,s("one"));req(J_COPY,"/data/src","/data/src/dst");
  CHECK(a.job_ret && a.job_message==M_CONFLICT && find(s("/data/src/dst"))<0);}
 if(which==40){add(s("/data/src"),0x41ED,0);add(s("/data/src/a"),0x81A4,s("one"));add(s("/data/src/sub"),0x41ED,0);
  add(s("/data/src/sub/b"),0x81A4,s("two"));req(J_DELETE,"/data/src",0);CHECK(!a.job_ret);
  for(u32 i=0;i<16;i++)CHECK(!nodes[i].used && !dirs[i].used);}
 if(which==41){s32 i=add(s("/data/dangling"),0xA1FF,0);a.job_type=10;req(J_DELETE,"/data/dangling",0);
  CHECK(!a.job_ret && !nodes[i].used);}
 if(which==42){add(s("/data/src"),0x41ED,0);add(s("/data/src/link"),0xA1FF,0);req(J_COPY,"/data/src","/data/dst");
  CHECK(a.job_ret && a.job_message==M_READONLY && find(s("/data/dst"))<0 && find(s("/data/src/link"))>=0);}
 if(which==43){add(s("/data/src"),0x41ED,0);add(s("/data/src/a"),0x81A4,s("keep"));add(s("/data/src/device"),0x31FF,0);
  req(J_DELETE,"/data/src",0);CHECK(a.job_ret && changed("/data/src/a","keep") && find(s("/data/src"))>=0);}
 if(which==44){a.view=V_TERM;fm_copy(a.terminal,FM_TERM+1,s("0\n1\n2\n3\n4\n5\n6\n7\n8\n9\nA\nB\nap>"));a.term_len=fm_len(a.terminal);
  a.render_line=0;fm_render_body(&a);CHECK(a.display[0]=='0');
  a.render_line=3;fm_render_body(&a);CHECK(a.display[0]=='3' && a.term_view_bytes>0);}
 if(which==45){a.view=V_VIEW;a.hex=1;a.page_len=512;fm_render_body(&a);CHECK(a.visible_bytes==96);
  u32 lines=0;for(u32 i=0;a.display[i];i++)if(a.display[i]=='\n')lines++;CHECK(lines==16);}
 if(which==46){a.term_pid=10;a.term_state=2;fm_copy(a.terminal_name,12,s("NF00000100t"));
  add(s("/proc/10/status"),0x81A4,s("Name: NF00000100t\nParent: 1\n"));
  fm_action(&u,41,0);CHECK(a.term_pending && a.job_kind==J_INTERRUPT);
  u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);CHECK(kill_n==1 && killed[0]==10);
  a.term_state=3;timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(!a.term_pending && a.job_state==1 && a.job_kind==J_FIFO);}
 if(which==47){a.initialized=1;a.term_pending=1;bt_pg_pause(page_node);CHECK(!a.term_pending);
  a.term_pending=1;bt_pg_destroy(page_node);CHECK(!a.term_pending);}
 if(which==48){fm_copy(a.cwd,512,s("/data/very/long/\xE4\xB8\xAD\xE6\x96\x87/file/path/abcdefghijklmnopqrstuvw.txt"));
  u.build=100;u.label=2000;a.dirty=1;a.error=28;bt_ui_show(&u,0);
  u32 i=0,cells=0;while(a.title[i]){u32 j=fm_next(a.title,i,fm_len(a.title));cells+=j-i>1?2:1;i=j;}
  CHECK(cells<=31 && fm_utf8(a.title,i));CHECK(fm_same(last_text,s("ready 28")));}
 if(which==49){add(s("/data/x"),0x81A4,s("old"));req(J_LOAD,"/data/x",0);fm_copy(a.edit,FM_EDIT+1,s("new"));
  a.edit_len=3;a.modified=1;external_change=1;req(J_SAVE,"/data/x","/data/x");
  CHECK(a.job_ret && a.job_message==M_CONFLICT && changed("/data/x","changed"));}
 if(which==50){a.count=1;a.entries[0].type=10;fm_copy(a.path,512,s("/data/link"));fm_action(&u,24,0);
  CHECK(a.clipboard==10);CHECK(fm_job(&u,J_COPY,a.clip,s("/data/copy")));CHECK(a.job_type==10);
  u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);CHECK(a.job_ret && a.job_message==M_READONLY && find(s("/data/copy"))<0);}
 if(which==51){CHECK(fifo_mock((u32)s("/tmp/missing"))<0 && err==17);req(J_FIFO,0,0);
  CHECK(!a.job_ret && a.fifo_owned==3 && a.fifo_in[1]=='d' && find(a.fifo_in)>=0 && find(a.fifo_out)>=0);}
 if(which==52){for(u32 i=0;i<20;i++)req(J_FIFO,0,0);CHECK(fifo_calls==2 && a.fifo_owned==3 && !open_fds());}
 if(which==53){u8 path[64];fm_pipe_path(path,(u32)&u,1,'i');add(path,0x81A4,s("keep"));req(J_FIFO,0,0);
  CHECK(!a.job_ret && a.fifo_sequence==2 && changed((char *)path,"keep") && a.fifo_owned==3);}
 if(which==54){fifo_fail_at=2;req(J_FIFO,0,0);CHECK(a.job_ret==28 && a.job_message==M_PIPE_OUT && !a.fifo_owned);
  CHECK(find(a.fifo_in)<0 && find(a.fifo_out)<0);}
 if(which==55){u8 path[64],in[64];fm_pipe_path(path,(u32)&u,1,'o');fm_pipe_path(in,(u32)&u,1,'i');
  add(path,0x81A4,s("keep"));req(J_FIFO,0,0);CHECK(!a.job_ret && a.fifo_sequence==2);
  CHECK(changed((char *)path,"keep") && find(in)<0 && a.fifo_owned==3);}
 if(which==56){req(J_FIFO,0,0);open_fail_at=2;fm_terminal_spawn(&u);CHECK(a.term_state==3);
  fm_terminal_poll(&u);CHECK(a.message==M_OPEN_OUT && a.error==13 && !a.term_state && !open_fds());}
 if(which==57){req(J_FIFO,0,0);fail_spawn=1;fm_terminal_spawn(&u);fm_terminal_poll(&u);
  CHECK(a.message==M_CONSOLE && a.error==12 && !a.term_state && !open_fds());}
 if(which==58){req(J_FIFO,0,0);fm_terminal_spawn(&u);CHECK(a.term_state==1 && a.term_pid==42 && open_fds()==2);
  dup_fail_at=2;u32 argv=(u32)a.terminal_name;bt_term_worker(1,&argv);CHECK(a.term_state==3 && a.term_error==9);
  fm_terminal_poll(&u);CHECK(a.message==M_STDIO && a.error==9);}
 if(which==59){req(J_FIFO,0,0);s32 index=find(a.fifo_in);fm_copy(nodes[index].data,40000,s("danger\n"));nodes[index].n=7;
  fm_terminal_spawn(&u);CHECK(a.term_state==1 && fds[a.term_in].at==7);}
 if(which==60){bt_pg_create(page_node,100);u.status=2;for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
  a.count=6;for(u32 i=0;i<6;i++){a.entries[i].type=i?8:4;fm_copy(a.entries[i].name,256,s("example.txt"));}
  for(u32 view=0;view<6;view++){a.view=view;a.dirty=1;bt_ui_show(&u,0);
   for(u32 i=0;i<FM_ROWS;i++){ui_record_t *r=record(a.objects[i]);if(!r || (r->flags&1))continue;
    if(r->parent==a.viewport){CHECK(r->x+r->w<=308);}else CHECK(r->x>=14 && r->y>=12 && r->x+r->w<=322 && r->y+r->h<=474);
    for(u32 j=i+1;j<FM_ROWS;j++){ui_record_t *q=record(a.objects[j]);if(!q || (q->flags&1) || q->parent!=r->parent)continue;
     CHECK(r->x+r->w<=q->x || q->x+q->w<=r->x || r->y+r->h<=q->y || q->y+q->h<=r->y);}
   }
   for(u32 i=0;i<6;i++){ui_record_t *r=record(a.details[i]);CHECK(((r->flags&1)==0)==(view==V_FILES));}
  }
 }
 if(which==61){a.term_state=2;a.view=V_PROMPT;a.prompt=P_COMMAND;fm_copy(a.input,512,s("pwd"));a.input_len=a.input_cursor=3;
  u32 ctx[2]={(u32)&u,53},e[4]={0,0,1,(u32)ctx};bt_app_event(e);CHECK(a.view==V_TERM && a.touch==53);
  ctx[1]=0;e[2]=8;bt_app_event(e);CHECK(!a.touch);
  fm_prompt(&a,P_COMMAND,s(""));ctx[1]=200;e[2]=1;bt_app_event(e);CHECK(a.input_len==1 && a.input[0]=='q');}
 if(which==62){req(J_FIFO,0,0);open_fail_at=1;fm_terminal_spawn(&u);fm_terminal_poll(&u);
  CHECK(a.message==M_OPEN_IN && a.error==13 && !open_fds());}
 if(which==63){req(J_FIFO,0,0);u32 argv=(u32)a.worker_name;
  fm_copy(a.terminal_name,12,a.worker_name);open_fail_at=2;bt_term_worker(1,&argv);CHECK(a.term_state==3);
  fm_terminal_poll(&u);CHECK(a.message==M_OPEN_OUT && a.error==13 && !open_fds());}
 if(which==64){bt_pg_create(page_node,100);u.status=2;for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
  a.view=V_FILE;a.count=1;a.entries[0].type=4;fm_layout(&u);
  CHECK(!a.contexts[4][1] && !a.contexts[5][1] && !a.contexts[6][1] && !a.contexts[7][1]);
  CHECK(a.contexts[8][1]==24 && a.contexts[13][1]==27);}
 if(which==65){a.term_state=2;a.view=V_TERM;fm_copy(a.command,256,s("previous"));fm_action(&u,40,0);
  CHECK(a.view==V_PROMPT && !a.input_len && !a.input[0]);fm_copy(a.input,512,s("pwd"));a.input_len=3;
  fm_accept(&u);CHECK(a.history_n==1 && fm_same(a.history[0],s("pwd")) && !a.input[0]);
  a.term_send_len=0;fm_action(&u,40,0);CHECK(!a.input_len);a.view=V_TERM;fm_action(&u,43,0);CHECK(fm_same(a.input,s("pwd")));}
 if(which==66){a.term_state=2;a.term_pid=10;a.history_n=4;a.term_len=3;a.pending_script=2;a.term_send_len=9;
  fm_copy(a.terminal,FM_TERM+1,s("old"));fm_copy(a.command,256,s("danger"));fm_action(&u,44,0);
  CHECK(a.job_kind==J_INTERRUPT && a.term_pending && a.reset_pending && !a.history_n && !a.term_send_len && !a.pending_script && !a.command[0]);
  a.job_state=0;a.term_state=3;timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(!a.reset_pending && !a.term_len && a.job_kind==J_FIFO && a.job_state==1);}
 if(which==67){a.view=V_FILES;a.total=18;a.count=12;u.build=100;a.viewport=1001;a.scroll_view=1;
  scroll_y_value=23;fm_scroll_poll(&u);CHECK(a.list_y==23 && !a.job_state && !scroll_set_calls);
  scroll_y_value=29;fm_scroll_poll(&u);CHECK(a.list_y==29 && !a.job_state);
  u32 ctx[2]={(u32)&u,901},e[4]={0,0,22,(u32)ctx};bt_app_event(e);CHECK(a.swipe_block);
  ctx[1]=100;e[2]=7;bt_app_event(e);CHECK(a.view==V_FILES);}
 if(which==68){a.view=V_FILES;a.total=18;u32 ctx[2]={(u32)&u,900},e[4]={0,0,21,(u32)ctx};indev[0x40]=0x10;bt_app_event(e);CHECK(!a.job_state && !a.swipe_block);
  a.view=V_PROMPT;indev[0x40]=0x40;bt_app_event(e);CHECK(!a.job_state && !a.swipe_block);
  a.view=V_VIEW;a.visible_bytes=40;bt_app_event(e);CHECK(!a.page_offset && !a.job_state);}
 if(which==69){s32 i=add(s("/data/p.PNG"),0x81A4,0);u8 *b=nodes[i].data;zero(b,24);nodes[i].n=24;
  b[0]=0x89;b[1]='P';b[2]='N';b[3]='G';b[4]=13;b[5]=10;b[6]=26;b[7]=10;
  b[12]='I';b[13]='H';b[14]='D';b[15]='R';b[19]=100;b[23]=90;
  read_chunk=3;req(J_INSPECT,"/data/p.PNG",0);CHECK(!a.job_ret && a.format==M_PNG && a.image_width==100 && a.image_height==90 && !open_fds());}
 if(which==70){add(s("/data/settings.JSON"),0x81A4,s("{\"v\": 2}"));req(J_INSPECT,"/data/settings.JSON",0);CHECK(a.format==M_JSON);
  s32 i=add(s("/data/blob"),0x81A4,s("abc"));nodes[i].data[1]=0;req(J_INSPECT,"/data/blob",0);CHECK(a.format==M_HEX && !open_fds());
  add(s("/data/x.md"),0x81A4,s("# heading"));req(J_INSPECT,"/data/x.md",0);CHECK(a.format==M_MARKDOWN);}
 if(which==71){a.view=V_IMAGE;a.format=M_PNG;a.image_width=a.image_height=200;a.file_size=100;fm_copy(a.path,512,s("/data/p.png"));decoder_bad=1;fm_image_prepare(&a);
  CHECK(a.view==V_INFO && a.message==M_IMAGE_FAIL && !a.image_ready && decode_calls==1);
  a.view=V_IMAGE;a.file_size=1048577;fm_image_prepare(&a);CHECK(decode_calls==1 && !a.image_ready);
  a.view=V_IMAGE;a.file_size=100;decoder_bad=0;decoder_header=5|(1024<<10)|(1024<<21);fm_image_prepare(&a);CHECK(a.message==M_IMAGE_BIG && a.view==V_INFO);}
 if(which==72){a.view=V_IMAGE;a.format=M_PNG;a.image_width=a.image_height=200;a.file_size=100;fm_copy(a.path,512,s("/data/p.png"));decoder_header=5|(512<<10)|(512<<21);
  fm_image_prepare(&a);CHECK(a.image_ready && fm_same(a.image_path,s("/data/p.png")));fm_image_show(&u);
  CHECK(a.image && image_zoom_value==128 && image_source==(u32)a.image_path);
  bt_pg_destroy(page_node);CHECK(!a.image && !u.root);}
 if(which==73 || which==74){s32 i=add(s("/data/p.bmp"),0x81A4,0);u8 *b=nodes[i].data;zero(b,70);nodes[i].n=70;
  b[0]='B';b[1]='M';b[10]=54;b[14]=40;b[18]=2;b[22]=2;b[26]=1;b[28]=24;
  b[56]=255;b[57]=255;b[62]=255;
  req(J_INSPECT,"/data/p.bmp",0);CHECK(!a.job_ret && a.format==M_BMP);
  if(which==74)b[30]=1;read_chunk=2;req(J_BITMAP,"/data/p.bmp",0);
  CHECK(!open_fds());if(which==73){CHECK(!a.job_ret && a.image_ready && a.image_descriptor[1]==16 && bitmap[0]==0xff0000ff && bitmap[2]==0xffff0000);}
  else CHECK(a.job_ret && a.job_message==M_IMAGE_FAIL && !a.image_ready);}
 if(which==75){a.format=M_JSON;a.file_size=200;fm_copy(a.path,512,s("/data/a.json"));a.view=V_INFO;fm_render_body(&a);CHECK(a.display[0]=='r');
  a.view=V_TERM;fm_copy(a.terminal,FM_TERM+1,s("ap> "));a.term_len=4;a.term_state=2;fm_action(&u,40,0);fm_render_body(&a);
  CHECK(a.display[0]=='a' && a.display[4]=='\n' && a.display[5]==0 && a.caret_x==0 && a.caret_y==22);}
 if(which==76){a.view=V_FILES;a.count=1;a.entries[0].type=4;fm_copy(a.entries[0].name,256,s("dir"));
  u32 ctx[2]={(u32)&u,100},e[4]={0,0,1,(u32)ctx};bt_app_event(e);e[2]=5;bt_app_event(e);
  e[2]=8;bt_app_event(e);CHECK(!a.touch && a.row_hold==100);e[2]=7;bt_app_event(e);
  CHECK(a.view==V_FILE && !a.job_state && !a.row_hold);}
 if(which==77){a.view=V_FILES;a.total=80;a.count=12;u.build=100;a.viewport=1001;a.scroll_view=1;
  scroll_y_value=10*FM_ROW_HEIGHT+17;fm_scroll_poll(&u);CHECK(a.list_y==617 && a.skip==8 && a.job_kind==J_LIST && a.job_type==1);
  CHECK(!scroll_set_calls && a.job_skip==8);}
 if(which==78){bt_pg_create(page_node,100);u.status=2;for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
  a.view=V_TERM;a.term_follow=0;for(u32 i=0;i<100;i++){a.terminal[i*2]='a';a.terminal[i*2+1]='\n';}a.term_len=200;
  a.term_y=143;fm_layout(&u);CHECK(scroll_y_value==143);u32 calls=scroll_set_calls;
  fm_terminal_text(&a,s("new\n"),4);fm_layout(&u);CHECK(a.term_y==143 && scroll_set_calls==calls);
  scroll_y_value=(s32)(a.content_lines*22+10-270-a.scroll_base*22);fm_scroll_poll(&u);CHECK(a.term_follow);
  fm_terminal_text(&a,s("new\n"),4);fm_layout(&u);CHECK(a.term_y==(s32)(a.content_lines*22+10-270));}
 if(which==79){bt_pg_create(page_node,100);u.status=2;for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
  a.total=2000;a.count=0;a.list_y=590*FM_ROW_HEIGHT+13;fm_layout(&u);CHECK(a.scroll_base==490 && scroll_y_value==6013);
  a.list_y=1065*FM_ROW_HEIGHT+7;a.scroll_sync=0;fm_layout(&u);CHECK(a.scroll_base==965 && scroll_y_value==6007);
  CHECK(a.list_y==1065*FM_ROW_HEIGHT+7 && record(a.spacer)->h<=36000);}
 if(which==80){s32 index=add(s("/data/long"),0x81A4,0);nodes[index].n=40000;
  for(u32 i=0;i<40000;i++)nodes[index].data[i]=i%29==28?'\n':'a';
  req(J_PAGE,"/data/long",0);CHECK(a.page_len==FM_EDIT && !open_fds());a.job_state=0;fm_copy(a.path,512,s("/data/long"));
  u.build=100;a.viewport=1001;a.view=V_VIEW;a.scroll_view=V_VIEW+1;a.content_lines=fm_text_scan(&a,a.edit,a.page_len,0,0);
  scroll_y_value=(s32)(a.content_lines-15)*22;fm_scroll_poll(&u);CHECK(a.job_kind==J_PAGE && a.page_offset>30000 && a.text_window);
  u32 anchor=a.view_anchor,argv=(u32)a.worker_name;bt_app_worker(1,&argv);timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(!a.text_window && a.text_y>=5*22 && a.view_anchor==anchor && !open_fds());}
 if(which==81){a.view=V_FILES;a.count=1;a.entries[0].type=4;fm_copy(a.entries[0].name,256,s("dir"));a.viewport=1001;
  u32 ctx[2]={(u32)&u,100},e[4]={0,0,1,(u32)ctx};bt_app_event(e);scroll_y_value=6;
  e[2]=7;bt_app_event(e);CHECK(a.view==V_FILES && !a.job_state);}
 if(which==82){a.page_len=512;a.file_size=513;for(u32 i=0;i<512;i++)a.page[i]='a';a.page[511]=0;
  CHECK(fm_format(&a)==M_HEX);a.page[511]=0xe4;CHECK(fm_format(&a)==M_TEXT);
  a.file_size=512;CHECK(fm_format(&a)==M_HEX);fm_copy(a.request,512,s("x.json"));CHECK(fm_format(&a)==M_HEX);}
 if(which==83){a.view=V_INFO;a.format=M_PNG;fm_copy(a.path,512,s("/data/p.png"));a.image_ready=0;
  fm_action(&u,34,0);CHECK(a.view==V_VIEW && a.hex && a.job_kind==J_PAGE && fm_same(a.request,a.path));}
 if(which==84){a.view=V_FILES;a.total=80;a.count=0;a.error=5;u.build=100;a.viewport=1001;a.scroll_view=1;
  scroll_y_value=100;fm_scroll_poll(&u);CHECK(!a.job_state && !spawned);
  a.job_state=2;a.job_kind=J_PAGE;a.job_ret=5;a.page_len=100;a.text_window=1;timer_words[3]=(u32)&u;
  bt_app_tick(timer_words);CHECK(!a.page_len && !a.text_window && a.error==5);}
 if(which==85){add(s("/data/a"),0x81A4,s("a"));req(J_LIST,"/data",0);
  CHECK(!a.job_ret && a.total==2 && a.count==2 && a.entries[0].type==FM_PARENT_TYPE);
  a.job_state=0;fm_action(&u,100,0);CHECK(fm_same(a.cwd,s("/")) && a.job_kind==J_LIST);
  a.job_state=0;a.entries[0].type=FM_PARENT_TYPE;fm_action(&u,100,0);
  CHECK(!a.job_state && a.view==V_FILES && a.message==M_ROOT);}
 if(which==86){a.view=V_EDIT;fm_copy(a.edit,FM_EDIT+1,s("WiWi\nsecond line\nthird line\nfourth line"));
  a.edit_len=fm_len(a.edit);a.cursor=1;fm_editor(&a);CHECK(a.caret_x==16 && a.caret_y==0);
  u8 old[4096];fm_copy(old,4096,a.display);a.cursor=2;fm_editor(&a);
  CHECK(a.caret_x==21 && fm_same(old,a.display) && !a.editor_top);
  a.cursor=a.edit_len;a.caret_follow=1;fm_editor(&a);CHECK(a.editor_y>0 && a.caret_y==66);
  a.cursor=0;fm_editor(&a);CHECK(!a.editor_top && !a.caret_x && !a.caret_y);}
 if(which==87){a.view=V_FILE;fm_copy(a.path,512,s("/data/new"));fm_copy(a.edit,FM_EDIT+1,s("old file"));a.edit_len=8;
  fm_action(&u,21,0);CHECK(a.view==V_EDIT && a.job_view==V_EDIT && !a.edit_len && !a.edit[0] && !a.editing);
  fm_action(&u,3,0);u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(a.view==V_TERM && !a.editing);}
 if(which==88){add(s("/data/new"),0x81A4,s("new file"));a.view=V_FILE;fm_copy(a.path,512,s("/data/new"));
  a.page_len=99;fm_action(&u,20,0);CHECK(!a.page_len && a.job_view==V_VIEW);
  fm_action(&u,3,0);u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(a.view==V_TERM && a.job_kind==J_INSPECT && !a.job_state);}
 if(which==89){a.view=V_FILES;a.count=1;a.entries[0].type=8;fm_copy(a.entries[0].name,256,s("first"));
  u32 ctx[2]={(u32)&u,100},e[4]={0,0,1,(u32)ctx};bt_app_event(e);
  a.listing_generation++;fm_copy(a.entries[0].name,256,s("second"));e[2]=7;bt_app_event(e);
  CHECK(a.view==V_FILES && !a.path[0]);}
 if(which==90){a.view=V_FILE;a.selected_type=8;a.count=1;a.entries[0].type=4;fm_copy(a.path,512,s("/data/a"));
  fm_action(&u,24,0);CHECK(a.clipboard==8 && fm_same(a.clip,s("/data/a")));
  add(s("/data/a"),0x81A4,s("a"));a.job_state=0;CHECK(fm_job(&u,J_MOVE,a.path,s("/data/b")));
  u32 argv=(u32)a.worker_name;bt_app_worker(1,&argv);timer_words[3]=(u32)&u;bt_app_tick(timer_words);
  CHECK(fm_same(a.path,s("/data/b")) && fm_same(a.clip,s("/data/b")) && a.view==V_FILES);}

 if(which==91){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  fm_copy(a.edit,FM_EDIT+1,s("Wi"));a.edit_len=2;a.cursor=1;fm_layout(&u);
  ui_record_t *caret=record(a.caret);CHECK(caret && !(caret->flags&1) && caret->w==3 && caret->h==20 && caret->x==26 && caret->y==10);
  for(u32 i=0;i<26;i++){ui_record_t *key=record(a.objects[5+i]);CHECK(key->w==40 && key->h==40 && !(key->flags&1));}
  a.view=V_FILES;fm_layout(&u);CHECK(caret->flags&1);}

 if(which==92){s32 i=add(s("/data/截图.PNG"),0x81A4,0);u8 *b=nodes[i].data;
  zero(b,33);nodes[i].n=33;b[0]=137;b[1]='P';b[2]='N';b[3]='G';b[4]=13;b[5]=10;b[6]=26;b[7]=10;
  b[11]=13;b[12]='I';b[13]='H';b[14]='D';b[15]='R';b[19]=200;b[23]=150;
  read_chunk=2;req(J_INSPECT,"/data/截图.PNG",0);CHECK(!a.job_ret && a.format==M_PNG && !open_fds());
  a.job_state=0;a.view=V_IMAGE;fm_copy(a.path,512,s("/data/截图.PNG"));decoder_real_file=1;fm_image_prepare(&a);
  CHECK(a.image_ready && a.image_width==200 && a.image_height==150 && fm_same(a.image_path,a.path));
  fm_image_show(&u);CHECK(image_source==(u32)a.image_path && record(a.image)->parent==u.root);
  a.image_width=4096;a.image_height=1;u32 calls=decode_calls;fm_image_prepare(&a);
  CHECK(!a.image_ready && a.message==M_IMAGE_BIG && decode_calls==calls);}
 if(which==93){a.view=V_TERM;for(u32 i=0;i<56;i++)a.terminal[i]='W';a.term_len=56;a.terminal[56]=0;
  CHECK(fm_text_scan(&a,a.terminal,56,0,0)==4 && fm_text_scan(&a,a.terminal,56,1,1)==17);
  fm_text_render(&a,a.display,4096,a.terminal,56,0,16);u32 width=0,lines=1;
  for(u32 i=0;a.display[i];i++){if(a.display[i]==10){CHECK(width<=284);width=0;lines++;}else width+=16;}
  CHECK(lines==4 && width<=284);
  fm_copy(a.terminal,FM_TERM+1,s("Wi\t中\nend"));a.term_len=fm_len(a.terminal);
  CHECK(fm_text_scan(&a,a.terminal,a.term_len,0,0)==2);
  fm_text_render(&a,a.display,4096,a.terminal,a.term_len,0,16);CHECK(fm_same(a.display,s("Wi    中\nend")));}
 if(which==94){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_TERM;clamp_scroll=1;
  for(u32 i=0;i<1200;i++){a.terminal[i*2]='W';a.terminal[i*2+1]=10;}a.term_len=2400;
  fm_layout(&u);CHECK(a.scroll_base>0 && a.term_y==(s32)(a.content_lines*22+10-270));
  CHECK(scroll_y_value+a.scroll_base*22==(u32)a.term_y);
  fm_terminal_text(&a,s("LAST LINE"),9);fm_layout(&u);CHECK(a.term_follow && fm_len(a.display)>=9);
  u32 n=fm_len(a.display);CHECK(fm_same(a.display+n-9,s("LAST LINE")));
  CHECK(scroll_y_value+a.scroll_base*22==(u32)a.term_y);
  a.term_follow=0;scroll_y_value-=37;fm_scroll_poll(&u);s32 old=a.term_y;
  fm_terminal_text(&a,s("\nmore"),5);fm_layout(&u);CHECK(a.term_y==old && !a.term_follow);}
 if(which==95){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  for(u32 i=0;i<30;i++){a.edit[i*2]='a';a.edit[i*2+1]=10;}a.edit_len=60;a.cursor=0;fm_layout(&u);
  scroll_y_value=79;fm_scroll_poll(&u);CHECK(a.editor_y==79 && !a.caret_follow);
  u32 calls=scroll_set_calls;fm_layout(&u);CHECK(a.editor_y==79 && scroll_y_value==79 && scroll_set_calls==calls);
  fm_action(&u,55,0);CHECK(a.caret_follow);fm_layout(&u);CHECK(!a.editor_y && a.cursor==1 && !a.caret_follow);}
 if(which==96){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  fm_copy(a.edit,FM_EDIT+1,s("Wi中\nsecond\nthird\nfourth\nfifth\nsixth\n"));a.edit_len=fm_len(a.edit);fm_layout(&u);
  u32 ctx[2]={(u32)&u,901},e[4]={0,0,1,(u32)ctx};((s16 *)indev)[4]=45;((s16 *)indev)[5]=135;
  bt_app_event(e);e[2]=8;bt_app_event(e);e[2]=7;bt_app_event(e);CHECK(a.cursor==2 && a.caret_follow);
  fm_layout(&u);scroll_y_value=44;fm_scroll_poll(&u);fm_layout(&u);
  ((s16 *)indev)[4]=45;((s16 *)indev)[5]=135;e[2]=1;bt_app_event(e);e[2]=8;bt_app_event(e);e[2]=7;bt_app_event(e);
  CHECK(a.cursor==15 && !(a.edit[a.cursor]&0x80));}
 if(which==97){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  fm_copy(a.edit,FM_EDIT+1,s("first\nsecond\nthird\nfourth\n"));a.edit_len=fm_len(a.edit);a.cursor=2;fm_layout(&u);
  u32 ctx[2]={(u32)&u,901},e[4]={0,0,1,(u32)ctx};((s16 *)indev)[4]=80;((s16 *)indev)[5]=135;
  bt_app_event(e);((s16 *)indev)[5]=152;e[2]=2;bt_app_event(e);((s16 *)indev)[5]=135;e[2]=7;bt_app_event(e);CHECK(a.cursor==2);
  e[2]=1;bt_app_event(e);e[2]=a.scroll_begin;bt_app_event(e);e[2]=7;bt_app_event(e);CHECK(a.cursor==2);
  e[2]=1;bt_app_event(e);e[2]=3;bt_app_event(e);e[2]=7;bt_app_event(e);CHECK(a.cursor==2);}
 if(which==98){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_TERM;fm_copy(a.terminal,FM_TERM+1,s("ap> "));a.term_len=4;
  fm_prompt(&a,P_COMMAND,s("Wi"));fm_layout(&u);fm_text_tap(&a,40,157);CHECK(a.input_cursor==1 && a.editor_prefix==1);
  fm_layout(&u);CHECK(a.caret_x==16 && a.caret_y==22 && record(a.caret)->parent==a.viewport);}

 if(which==99){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  fm_copy(a.edit,FM_EDIT+1,s("WiWiiiWiWWiiiWiiWi中WiWiWiiiWiWWiiiWiiWi中Wi"));a.edit_len=fm_len(a.edit);
  u32 glyph=0;for(u32 cur=0;cur<a.edit_len;cur=fm_next(a.edit,cur,a.edit_len),glyph++){
   a.cursor=cur;fm_layout(&u);u32 x=0,y=0;CHECK(draw_position(record(a.scroll_label),glyph,&x,&y));
   CHECK(a.caret_x==x && a.caret_y==y && record(a.caret)->x==record(a.scroll_label)->x+x);
  }
  a.cursor=a.edit_len;fm_action(&u,200,0);fm_layout(&u);u32 x=0,y=0;
  CHECK(draw_position(record(a.scroll_label),glyph+1,&x,&y) && a.caret_x==x && a.caret_y==y);}
 if(which==100){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_TERM;clamp_scroll=1;
  u32 p=0;for(u32 row=0;row<60;row++){for(u32 j=0;j<17;j++)a.terminal[p++]='W';a.terminal[p++]=10;}
  for(u32 j=0;j<17;j++)a.terminal[p++]='W';a.terminal[p]=0;a.term_len=p;fm_layout(&u);
  ui_record_t *l=record(a.scroll_label),*v=record(a.viewport);u32 physical=draw_height(l);
  CHECK(physical<=l->h && (s32)(l->y+physical)-scroll_y_value<=(s32)v->h);
  CHECK((s32)(l->y+physical)-scroll_y_value>=(s32)v->h-32);
  CHECK(fm_len(l->text)>17 && l->text[fm_len(l->text)-1]=='W');
  fm_terminal_text(&a,s("gjpqy"),5);fm_layout(&u);physical=draw_height(l);
  CHECK(physical<=l->h && (s32)(l->y+physical)-scroll_y_value<=(s32)v->h);
  CHECK(fm_same(l->text+fm_len(l->text)-6,s("g\njpqy")));}
 if(which==101){for(u32 i=0;i<48;i++)bt_ui_step(&u,0);a.view=V_EDIT;
  fm_copy(a.edit,FM_EDIT+1,s("Wi\nWi\nWi\nWi\nWi\nWi\nWi\nWi"));a.edit_len=fm_len(a.edit);a.cursor=a.edit_len;
  a.caret_follow=1;fm_layout(&u);ui_record_t *l=record(a.scroll_label),*caret=record(a.caret);
  u32 count=0;for(u32 i=0;l->text[i];i++)if(l->text[i]!=10)count++;
  u32 x=0,y=0;CHECK(draw_position(l,count,&x,&y));
  CHECK(caret->x==l->x+x && caret->y==l->y+y && draw_height(l)<=l->h);
  fm_text_tap(&a,14+l->x+16,116+l->y+y-scroll_y_value+4);
  CHECK(a.cursor==a.edit_len-1);}

 return 0;
}
u32 test_catalog(void){return (u32)catalog;}
u32 test_scroll_object(void){return a.viewport;}
u32 test_scroll_position(void){return (u32)scroll_y_value;}
u32 test_records(void){return (u32)records;}
u32 test_record_count(void){return record_n;}
u32 test_record_size(void){return sizeof(ui_record_t);}
u32 test_render(u32 view){reset();u32 at=0;for(u32 i=0;i<M_COUNT;i++){messages[i]=(u32)catalog+at;at+=fm_len(catalog+at)+1;}
 fm_copy(a.cwd,512,s("/data"));fm_copy(a.path,512,s("/data/example.sh"));a.count=7;a.total=19;
 fm_copy(a.entries[1].name,256,s("scripts"));a.entries[1].type=4;
 fm_copy(a.entries[2].name,256,s("logs"));a.entries[2].type=4;
 fm_copy(a.entries[3].name,256,s("example.sh"));a.entries[3].type=8;a.entries[3].size=238;
 fm_copy(a.entries[4].name,256,s("settings.lua"));a.entries[4].type=8;a.entries[4].size=1408;
 fm_copy(a.entries[5].name,256,s("notes.txt"));a.entries[5].type=8;a.entries[5].size=5600;
 fm_copy(a.entries[6].name,256,s("sensor.bin"));a.entries[6].type=8;a.entries[6].size=76800;
 a.entries[0].type=FM_PARENT_TYPE;fm_copy(a.entries[0].name,256,s(".."));a.selected=3;
 bt_pg_create(page_node,100);u.status=2;for(u32 i=0;i<48;i++)bt_ui_step(&u,0);
 a.view=view==0?V_FILES:view==1?V_FILE:view==2?V_TERM:view==3?V_PROMPT:V_VIEW;
 if(view==2){a.message=M_RUNNING;fm_copy(a.terminal,FM_TERM+1,s("NuttShell (NSH)\nnsh> pwd\n/data\nnsh> ls /data\n  scripts/\n  logs/\n  example.sh\n  settings.lua\nnsh> "));a.term_len=fm_len(a.terminal);}
 if(view==3){a.prompt=P_COMMAND;fm_copy(a.input,512,s("ls /data"));a.input_cursor=a.input_len=8;}
 if(view==4){fm_copy(a.edit,FM_EDIT+1,s("#!/bin/sh\n\necho \"N67 File Manager\"\npwd\nls /data\n"));a.page_len=fm_len(a.edit);}
 if(view==6){a.view=V_EDIT;fm_copy(a.edit,FM_EDIT+1,s("#!/bin/sh\necho \"hello\"\npwd\nls /data\n"));a.edit_len=fm_len(a.edit);a.cursor=19;a.modified=1;}
 if(view==7){a.view=V_EDIT;u32 at=0;
  for(u32 i=0;i<24;i++){at=fm_cat(a.edit,at,FM_EDIT+1,s("line "));at=fm_num(a.edit,at,FM_EDIT+1,i+1);a.edit[at++]=10;}
  a.edit[at]=0;a.edit_len=at;a.editor_y=107;a.cursor=0;a.caret_follow=0;a.scroll_sync=1;}
 if(view==8){a.view=V_TERM;u32 at=0;
  for(u32 i=0;i<60;i++){at=fm_cat(a.terminal,at,FM_TERM+1,s("output "));at=fm_num(a.terminal,at,FM_TERM+1,i+1);a.terminal[at++]=10;}
  at=fm_cat(a.terminal,at,FM_TERM+1,s("ap> "));a.term_len=at;a.term_follow=1;}
 if(view==5){a.view=V_TERM;a.message=M_PIPE_IN;a.error=17;}
 a.dirty=1;bt_ui_show(&u,0);return u.build;
}
