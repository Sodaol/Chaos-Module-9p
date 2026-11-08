/* Read-only preflight: 1 current app, 2 v2.1, 4 current page,
 * 8 invalid chain, 16 duplicate package under another ID. */
static u32 pf_package(u32 p){

 for(u32 i=0;i<18u;i++){
  u32 a=p+i;
  if(!((a>=0x20000000u&&a<0x20100000u)||(a>=0x3c000020u&&a<0x3efffff8u)||(a>=0x2c080000u&&a<0x2c7ea290u)))return 0u;
  u32 word=i<4u?0x2e6d6f63u:i<8u?0x6f616863u:i<12u?0x616d2e73u:i<16u?0x6567616eu:0x72u;
  u8 expected=(u8)(word>>((i&3u)*8u));
  if(*(volatile u8 *)a!=expected)return 0u;
  if(!expected)return 1u;
 }return 0u;
}
u32 bt_entry_preflight(void){
 u32 mask=0u;
 u32 (*find)(u32)=(u32 (*)(u32))0x0c4467b5u;
 u32 node=find(0xe7d4u);
 if(bt_valid_ptr(node)&&bt_valid_ptr(node+0x10u)&&*(volatile u16 *)(node+0x10u)==0xe7d4u)mask|=1u;
 node=find(0xe7c3u);
 if(bt_valid_ptr(node)&&bt_valid_ptr(node+0x10u)&&*(volatile u16 *)(node+0x10u)==0xe7c3u)mask|=2u;
 return mask;
}
