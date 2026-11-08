/* N67 file engine integrated into Chaos; firmware-owned root, heap-owned state.
 * Derived from our tested filemanager v6. Core retains its worker/NSH lifetimes. */
#include "platform_n67.c.in"
#include "core.c"
static bt_ui_t *chaos_files_ui;
static u32 chaos_files_mode;
static u32 chaos_files_gesture,chaos_files_press;
static const char *chaos_files_messages[]={
"就绪",
"处理中",
"操作失败",
"文件",
"终端",
"返回",
"刷新",
"更多",
"上一页",
"下一页",
"新文件",
"新目录",
"粘贴",
"路径",
"查看",
"编辑",
"运行 sh",
"运行 Lua",
"复制",
"移动",
"重命名",
"删除",
"保存",
"已保存",
"未保存",
"再点确认放弃/删除",
"文本过大",
"不是 UTF-8 文本",
"不支持此类型",
"目标存在或文件已改变",
"目录为空",
"十六进制",
"文本",
"输入",
"中断",
"清空",
"历史",
"发送",
"空格",
"退格",
"换行",
"确定",
"换键盘",
"左移",
"右移",
"名称",
"目标路径",
"目录",
"文件",
"已复制",
"已删除",
"已重命名",
"已创建",
"运行中",
"已停止",
"启动失败",
"开头",
"末尾",
"字符集",
"/dev/nfm.in",
"/dev/nfm.out",
"/proc",
"/status",
"上级目录：",
".nfm.part.",
"qwertyuiopasdfghjklzxcvbnm",
"QWERTYUIOPASDFGHJKLZXCVBNM",
"1234567890-=[]\\;',./!@#$%^",
"&*()_+{}|:\"<>?`~=:\\/$!%#@^",
"请先复制文件",
"脚本路径不支持或太长",
"文件末尾",
"取消",
"已选择",
"创建输入管道失败",
"创建输出管道失败",
"打开输入管道失败",
"打开输出管道失败",
"重定向失败",
"启动会话失败",
"输入命令",
"重置",
"上下滑动浏览",
"图片",
"信息",
"图片解码不支持或文件损坏",
"图片尺寸超限",
"JSON",
"CSV / TSV",
"配置文件",
"Markdown 源文",
"HTML 源文",
"XML 源文",
"PNG",
"JPEG",
"BMP",
"GIF 信息",
"LVGL 图片",
"UTF-8 源文",
"上一级目录",
"已在根目录"};
void chaos_files_flags(u32 gesture,u32 press){chaos_files_gesture=gesture;chaos_files_press=press;}
void chaos_files_open(u32 mode){chaos_files_mode=mode;}
static bt_ui_t *chaos_files_alloc(u32 page){
 if(chaos_files_ui){chaos_files_ui->page=page;((u32 *)page)[1]=(u32)chaos_files_ui;return chaos_files_ui;}
 bt_ui_t *u=(bt_ui_t *)((u32(*)(u32))0xc0f1171u)(sizeof(bt_ui_t)+FM_STATE_MAX);
 if(!u)return 0;for(u32 i=0;i<sizeof(bt_ui_t)+FM_STATE_MAX;i++)((u8 *)u)[i]=0;
 u->magic=BT_UI_MAGIC;u->page=page;u->obj_create=0xc23f09du;u->label_create=0xc25ebbdu;
 u->label_set_text=0xc263e09u;u->set_size=0xc23af59u;u->set_prop=0xc242e8bu;
 u->add_flag=0xc23ba45u;u->clear_flag=0xc23babbu;u->align=0xc23afe3u;
 u->runtime=(u32)(u+1);u->text=(u32)"Chaos 文件";
 fm_t *a=(fm_t *)u->runtime;
 u32 bindings[]={FM_MAGIC,0xc25a289u,(u32)bt_app_tick,0xc241159u,(u32)bt_app_event,
 0xc0c00a3u,(u32)bt_app_worker,(u32)bt_term_worker,0xc4490b9u,0xc1610b9u,
 16,chaos_files_gesture,chaos_files_press,(u32)chaos_files_messages,
 0xc2665f1u,(u32)"MiSans-Regular",0xc37e30du,0xc37dba5u,0xc37f459u,0xc37f0fdu,
 0xc37e1f5u,0xc37fc39u,0xc37f491u,0xc37fe01u,0xc37e249u,0xc37f775u,
 0xc0e4139u,0xc0e4199u,0xc0e4171u,0xc37fe21u,0xc4fdbbdu,0xc37c17du,
 0x200b11d0u,0xc1014edu,0xc0bd309u,0xc0e4121u,FM_STATE_MAX,1,
 0x200bf388u,12,4,8,0xc25eba1u,0xc2617d9u,0xc244021u,0xc25ef2du,0xc0f1171u,
 0xc23bd03u,0xc242ca1u,0xc23ea15u,0xc242841u,9,64,0xc239f2du};
 for(u32 i=0;i<54;i++)((u32 *)a)[i]=bindings[i];
 ((u32 *)page)[1]=(u32)u;chaos_files_ui=u;return u;
}
u32 chaos_files_create(u32 *p,u32 root,u32 start){
 (void)start;bt_ui_t *u=chaos_files_alloc((u32)p);if(!u)return 0xffffffffu;
 return bt_pg_create(p,p[11]?p[11]:root);
}
u32 chaos_files_resume(u32 *p){
 bt_ui_t *u=fm_ui(p);fm_t *a=fm_state(u);if(!a)return 0;
 if(chaos_files_mode && !a->job_state){
  if(!a->initialized){a->initialized=1;a->term_in=a->term_out=-1;}if(!a->cwd[0])fm_copy(a->cwd,FM_PATH,(const u8 *)"/data");
   a->view=V_TERM;a->term_pending=1;a->term_follow=1;a->scroll_sync=1;
   if(chaos_files_mode==2){
    const char *cmd="bttool start_scan 0 000000000000 000000000000 16 16 0 0";
    u32 n=0;while(cmd[n] && n<255){a->command[n]=(u8)cmd[n];n++;}a->command[n]=0;
    a->pending_script=3;
   }
 }
 if(!chaos_files_mode && a->view==V_TERM && !a->job_state)a->view=V_FILES;
 chaos_files_mode=0;return bt_pg_resume(p);
}
u32 chaos_files_pause(u32 *p){return bt_pg_pause(p);}
u32 chaos_files_destroy(u32 *p){return bt_pg_destroy(p);}
u32 chaos_files_signal(u32 *p,u32 code,u32 arg){return bt_pg_signal(p,code,arg);}
/* Existing Chaos UI heartbeat repairs a stalled file timer without creating
 * another timer. The clock gate prevents a second drive source when healthy. */
void chaos_files_poll(void){
 bt_ui_t *u=chaos_files_ui;fm_t *a=fm_state(u);
 if(!a || u->status!=2 || !a->timer)return;
 u32 now=((u32 (*)(void))a->tick_get)();
 if((u32)(now-a->now)>=200u)bt_app_tick((u32 *)a->timer);
}

/* Enter the audited native LVGL8 setter body without constructing a Lua state.
 * The prologue exactly matches 0xc46c720; 0xc46c756 restores this stack frame.
 * r4=lv_disp_t*, r3=lv_disp_rot_t. No Lua calls occur after 0xc46c776.
 */
__attribute__((naked)) void chaos_n67_rotate_display(u32 display,u32 rotation){
 __asm__ volatile(
  "push.w {r4,r5,r6,r7,r8,lr}\n"
  "sub sp,sp,#16\n"
  "add r7,sp,#8\n"
  "mov r4,r0\n"
  "mov r3,r1\n"
  "ldr r2,1f\n"
  "bx r2\n"
  ".p2align 2\n"
  "1: .word 0x0c46c777\n"
 );
}
