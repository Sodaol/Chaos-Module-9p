//! N67 BGRA backdrop renderer, rewritten for alpha.34.
//! Two separable binomial convolutions (coefficients of (1+x)^6),
//! bounded row work, then bilinear reconstruction. No borrowed pixel buffers.
const W:usize=336;
const H:usize=480;
const SW:usize=W/4;
const SH:usize=H/4;
const N:usize=SW*SH*3;
pub const BYTES:usize=W*H*4;
const WEIGHT:[u32;7]=[1,6,15,20,15,6,1];
#[derive(Debug,PartialEq)]
pub enum RenderError{Input,Output}
pub struct Renderer{phase:u8,row:usize,blur:bool,a:[u8;N],b:[u8;N]}
impl Renderer{
 pub const fn new()->Self{Self{phase:0,row:0,blur:false,a:[0;N],b:[0;N]}}
 pub fn reset(&mut self,blur:bool){self.phase=if blur{0}else{5};self.row=0;self.blur=blur;}
 pub fn finished(&self)->bool{self.phase==4}
 pub fn step(&mut self,input:&[u8],output:&mut [u8],budget:usize)->Result<usize,RenderError>{
  if input.len()<BYTES{return Err(RenderError::Input);}
  if output.len()<BYTES{return Err(RenderError::Output);}
  let mut rows=0;
  while rows<budget.min(16)&&!self.finished(){
   let y=self.row;
   match self.phase{
    5=>{
     // Transparent mode keeps every original pixel; no reduction or resampling.
     for x in 0..W{let p=(y*W+x)*4;let alpha=input[p+3] as u32;
      for c in 0..3{output[p+c]=((input[p+c] as u32*alpha+127)/255) as u8;}
      output[p+3]=255;
     }
    },
    0=>{
     for x in 0..SW{for c in 0..3{
      let mut sum=0u32;
      for dy in 0..4{for dx in 0..4{
       let p=((y*4+dy)*W+x*4+dx)*4;
       sum+=input[p+c] as u32*input[p+3] as u32;
      }}
      self.a[(y*SW+x)*3+c]=((sum+2040)/4080) as u8;
     }}
    },
    1|2=>{
     for x in 0..SW{for c in 0..3{
      let mut sum=0u32;
      for (k,&weight) in WEIGHT.iter().enumerate(){
       let (sx,sy)=if self.phase==1{((x as isize+k as isize-3).clamp(0,SW as isize-1) as usize,y)}
        else{(x,(y as isize+k as isize-3).clamp(0,SH as isize-1) as usize)};
       let i=(sy*SW+sx)*3+c;
       sum+=weight*if self.phase==1{self.a[i]}else{self.b[i]} as u32;
      }
      let i=(y*SW+x)*3+c;
      if self.phase==1{self.b[i]=((sum+32)/64) as u8;}else{self.a[i]=((sum+32)/64) as u8;}
     }}
    },
    3=>{
     let sy=y/4;let ny=(sy+1).min(SH-1);let fy=(y%4) as u32;
     for x in 0..W{
      let sx=x/4;let nx=(sx+1).min(SW-1);let fx=(x%4) as u32;
      let corners=[(sx,sy,(4-fx)*(4-fy)),(nx,sy,fx*(4-fy)),(sx,ny,(4-fx)*fy),(nx,ny,fx*fy)];
      for c in 0..3{
       let mut sum=0u32;for &(cx,cy,weight) in &corners{sum+=self.a[(cy*SW+cx)*3+c] as u32*weight;}
       let v=(sum+8)/16;output[(y*W+x)*4+c]=if self.blur{(v*160/255) as u8}else{v as u8};
      }
      output[(y*W+x)*4+3]=255;
     }
    },
    _=>{},
   }
   rows+=1;self.row+=1;
   if self.row==if self.phase==3||self.phase==5{H}else{SH}{
    self.row=0;
    self.phase=match self.phase{0=>if self.blur{1}else{3},1=>2,2=>3,_=>4};
   }
  }
  Ok(rows)
 }
}
