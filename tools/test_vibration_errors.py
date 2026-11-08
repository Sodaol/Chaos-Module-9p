"""Execute real 3.1.190 request gates rather than mocking them as success."""
from test_port_pages import PortBand
from unicorn.arm_const import *
class VibrationBand(PortBand):
 def __init__(self,base):
  self.driver_rc=0;self.driver_calls=0;super().__init__(base)
 def hook(self,u,a,n,ud):
  if 0xc45dc68<=a<0xc45dcf8:return
  if a in (0xc368f48,0xc0eb0e8,0xc4b49f0):
   if a==0xc368f48:self.driver_calls+=1;ret=self.driver_rc
   elif a==0xc4b49f0:
    x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
    u.mem_write(x,bytes(u.mem_read(y,z)));ret=x
   else:ret=0
   u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)

for base in (0x1d100000,0x1d340000,0x1c900000):
 for disable,busy,mode,rc,expected in [
  (1,0,0,0,'系统已停用震动'),(0,1,0,0,'其他震动正在执行'),
  (0,0,2,-5,'当前系统模式禁止震动'),(0,0,0,-2,'系统不支持此震动效果'),
  (0,0,0,-4,'震动参数为空'),(0,0,0,-19,'震动服务返回失败'),
  (0,0,0,0,'请求已提交，未检测实际震动')]:
  b=VibrationBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192);b.create(20)
  b.w8(0x200cbb6d,disable);b.w8(0x200cc6bc,mode)
  b.w8(0x200d6de4,busy);b.w8(0x200d6dec,busy);b.driver_rc=rc
  b.click(0);assert b.driver_calls==0
  b.drive();assert any(expected.encode() in t for t in [t for t,ms in b.toasts]),[t for t,ms in b.toasts]
  assert b.u.mem_read(0x200cbb6d,1)==bytes([disable]),'must preserve system disable'
  if disable or busy:assert b.driver_calls==0
  if rc<0 or disable or busy:assert any(b'rc=-' in t for t in [t for t,ms in b.toasts])
 print(f'PASS vibration errors ARM {base:08x}: actual disabled/busy gates, driver errors, exact reason and rc, deferred request, system setting preservation')
