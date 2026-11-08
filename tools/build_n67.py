"""Reproducible 9 Pro build. Does not write or flash firmware."""
from pathlib import Path
import json,struct,subprocess,sys,hashlib,os,shutil
R=Path(__file__).resolve().parents[1];W=R/'build-support'
from page_layout import PAGE_COUNT
def run(*cmd,cwd=R):subprocess.run(list(map(str,cmd)),cwd=cwd,check=True)
def main():
 (R/'n67/generated').mkdir(parents=True,exist_ok=True)
 from datetime import datetime,timezone
 stamp=datetime.fromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']),timezone.utc) if 'SOURCE_DATE_EPOCH' in os.environ else datetime.now(timezone.utc)
 (R/'n67/build-time.txt').write_bytes(stamp.strftime('%Y-%m-%d %H:%M UTC').encode()+b'\0')
 cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo.exe');rustc=shutil.which('rustc') or str(Path.home()/'.cargo/bin/rustc.exe')
 run(cargo,'rustc','--release','--target','thumbv7em-none-eabi','--features','n67,settings-egg' if os.environ.get('CHAOS_SETTINGS_EGG')=='1' else 'n67','--manifest-path','supervisor/Cargo.toml','--','-C','target-feature=+no-movt')
 sysroot=subprocess.check_output([str(rustc),'--print','sysroot'],text=True).strip()
 lld=next((Path(sysroot)/'lib/rustlib').glob('*/bin/rust-lld*'))
 from build_n67_files import compile_files
 files_obj=compile_files()
 run(lld,'-flavor','gnu','--gc-sections','--emit-relocs','-T','tools/n67.ld','-o','supervisor/chaos-n67.elf','supervisor/target/thumbv7em-none-eabi/release/libchaos_sup.a',files_obj)
 from pack_n67 import pack
 pack(R/'supervisor/chaos-n67.elf',R/'n67/generated/chaos.bin')
 fw=Path(os.environ.get('CHAOS_FW',str(R.parent/'fw/data/ota/app/vela_ap.bin'))).read_bytes()
 assert hashlib.sha256(fw).hexdigest()=='3e264bc267431ec71843cc7c2e4acd928b9280ea39ee1cd888636adcebabf82f'
 addresses=[205821900, 205809588, 205822656, 205817672, 204097440, 204097840, 203681948, 203724928, 203832840, 203665218, 203697802, 203665378, 203668036, 203668154, 203690328, 203696004, 203671680, 205825476, 205820088, 204989196, 204987300, 204993624, 204992764, 202260792, 202260888, 202260848, 204993680, 202260768, 202314096, 202311568, 203693192, 203843056, 203793032, 205825452, 205955082, 205833112, 205833248, 205863824, 204519612, 203783828, 203657410, 204995640, 203660136, 203660312, 203660372, 203823064, 203690468, 202113186, 202772664, 204988916, 204989000, 204994420, 204996128, 204980604, 202263424, 203702304, 203812652, 203668738, 203697312, 203680276, 203696192, 203661100, 203665240, 203657530, 203657580, 203811772, 203811796, 208155824, 208155844, 204996096, 206560188, 202380524, 202101512, 203811744, 204989256, 203661328, 203811768, 202092692, 202314452]
 addresses=list(dict.fromkeys(addresses+[0x0c37e1f4,0x0c45dc68,0x0c26fa22,0x0c290018,0x0c37e1b4,0x0c0ee72c,0x0c0c813c,0x0c2a47ec,0x0c2a308c,0x0c2a30ca,0x0c37f490,0x0c25ebbc,0x0c25ebd4,0x0c263e08,0x0c24427c,0x0c40662a,0x0c43479e,0x0c43ad90,0x0c43b6f4,0x0c23ba44,0x0c240b20,0x0c240b50,0x0c240f64,0x0c2a1d20,0x0c257ece,0x0c258498,0x0c2a46d4,0x0c2a3334,0x0c2a47a0,0x0c2a490a,0x0c7deb00,0x0c7de404,0x0c0c80bc,0x0c0c813c,0x0c4db9ac,0x0c4349d4,0x0c434a54,0x0c4349f0,0x0c43ba44,0x0c373b20,0x0c2702b4,0x0c275ad4,0x0c276ae4,0x0c275500,0x0c271d6c,0x0c274f60,0x0c25bc38,0x0c23ef90,0x0c23e908,0x0c43da64,0x0c2644d8,0x0c36f064,0x0c36ef10,0x0c373c18,0x0c23c8b8,0x0c2d6514,0x0c2cfd60,0x0c4fb974,0x0c2a0488,0x0c2a1f68,0x0c29ec00]))
 guards=[];proof=[]
 for i,a in enumerate(addresses):
  d=fw[a-0xc080000:a-0xc080000+8];x,y=struct.unpack('<II',d)
  guards.append(f'if(*(volatile u32 *){a:#x}u!={x:#x}u || *(volatile u32 *){a+4:#x}u!={y:#x}u)return {80+i}u;')
  proof.append({'address':hex(a),'bytes':d.hex(),'error':80+i})
 bridge=(W/'filemanager/platform_n67.c.in').read_text('utf-8').replace('r->icons, 1u',f'r->icons, {PAGE_COUNT}u')
 bridge=f'#define BT_RECOVERY_PAGES {PAGE_COUNT}u\n'+bridge
 if os.environ.get('CHAOS_SETTINGS_EGG')=='1':bridge='#define CHAOS_SETTINGS_EGG 1\n'+bridge
 bridge+='\nstatic void bt_ui_show(bt_ui_t *u,bt_cfg_t *c){(void)u;(void)c;}\nstatic u32 bt_ui_step(bt_ui_t *u,bt_cfg_t *c){(void)u;(void)c;return 0;}\n'
 bridge+='u32 bt_install_check(u32 find,u32 id){if(find!=0x0c4467b5u||id!=0xe7d4u)return 29u;return ((u32 (*)(u32))find)(id); }\n'
 bridge+='\n'+(R/'n67/entry-preflight.c').read_text('utf-8-sig')
 (R/'n67/bridge.c').write_text(bridge,'utf-8')
 (R/'n67/generated/firmware-fingerprints.json').write_text(json.dumps(proof,indent=2),'utf-8')
 run(sys.executable,R/'tools/build_n67_bridge.py')
 run(sys.executable,R/'tools/port_v21_bootstrap.py')
 run(sys.executable,R/'tools/make_n67_installer.py')
 run('node',W/'work/wasm/check_face.cjs',R/'n67/generated/main.lua')
 run(sys.executable,W/'installers/preview.py',R/'n67')
 run(sys.executable,W/'installers/pack.py',R/'n67')
 print('Built Chaos N67 installer')
if __name__=='__main__':main()
