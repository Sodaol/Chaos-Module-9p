//! Bounded, read-only registry metadata. Never rewrites a user's apps.json.
#[derive(Clone,Copy)]
pub struct Metadata { pub name:[u8;128],pub version:[u8;48] }
impl Metadata { pub const EMPTY:Self=Self{name:[0;128],version:[0;48]}; }
type R<T> = Result<T,()>;
fn ws(b:&[u8],mut p:usize)->usize{while p<b.len()&&matches!(b[p],b' '|b'\n'|b'\r'|b'\t'){p+=1;}p}
fn hex(b:&[u8],p:usize)->R<u32>{let mut v=0;for &c in b.get(p..p+4).ok_or(())?{v=v*16+match c{b'0'..=b'9'=>(c-b'0') as u32,b'a'..=b'f'=>(c-b'a'+10) as u32,b'A'..=b'F'=>(c-b'A'+10) as u32,_=>return Err(())};}Ok(v)}
fn escaped(b:&[u8],p:&mut usize)->R<char>{
 let c=*b.get(*p).ok_or(())?;*p+=1;
 Ok(match c{b'"'=>'"',b'\\'=>'\\',b'/'=>'/',b'b'=>'\x08',b'f'=>'\x0c',b'n'=>'\n',b'r'=>'\r',b't'=>'\t',b'u'=>{
  let mut v=hex(b,*p)?;*p+=4;
  if (0xd800..=0xdbff).contains(&v){if b.get(*p..*p+2)!=Some(b"\\u"){return Err(());}*p+=2;let low=hex(b,*p)?;*p+=4;if !(0xdc00..=0xdfff).contains(&low){return Err(());}v=0x10000+((v-0xd800)<<10)+(low-0xdc00);}
  core::char::from_u32(v).ok_or(())?
 },_=>return Err(())})
}
fn string_end(b:&[u8],mut p:usize)->R<usize>{
 if b.get(p)!=Some(&b'"'){return Err(());}p+=1;
 loop{match *b.get(p).ok_or(())?{b'"'=>return Ok(p+1),b'\\'=>{p+=1;escaped(b,&mut p)?;},0..=31=>return Err(()),_=>p+=1}}
}
fn decode(b:&[u8],out:&mut[u8])->R<(usize,usize)>{
 if string_end(b,0)?!=b.len(){return Err(());}let mut p=1;let(mut n,mut total,mut full)=(0,0,false);
 while p+1<b.len(){let mut tmp=[0;4];let s=if b[p]==b'\\'{p+=1;let c=escaped(b,&mut p)?;c.encode_utf8(&mut tmp).as_bytes()}else{
  let c=core::str::from_utf8(&b[p..b.len()-1]).map_err(|_|())?.chars().next().ok_or(())?;p+=c.len_utf8();c.encode_utf8(&mut tmp).as_bytes()
 };total+=s.len();if !full&&n+s.len()<out.len(){out[n..n+s.len()].copy_from_slice(s);n+=s.len();}else{full=true;}}
 if !out.is_empty(){out[n]=0;}Ok((n,total))
}
fn end(b:&[u8],p:usize,depth:usize)->R<usize>{
 if depth>24{return Err(());}let p=ws(b,p);match *b.get(p).ok_or(())?{
 b'"'=>string_end(b,p),
 b'{'|b'['=>{let obj=b[p]==b'{';let close=if obj{b'}'}else{b']'};let mut q=ws(b,p+1);if b.get(q)==Some(&close){return Ok(q+1);}
  loop{if obj{q=ws(b,string_end(b,q)?);if b.get(q)!=Some(&b':'){return Err(());}q+=1;}q=ws(b,end(b,q,depth+1)?);
   match b.get(q){Some(c)if *c==close=>return Ok(q+1),Some(b',')=>q=ws(b,q+1),_=>return Err(())}}
 },
 b't' if b.get(p..p+4)==Some(b"true")=>Ok(p+4),b'f' if b.get(p..p+5)==Some(b"false")=>Ok(p+5),b'n' if b.get(p..p+4)==Some(b"null")=>Ok(p+4),
 b'-'|b'0'..=b'9'=>{let mut q=p;if b[q]==b'-'{q+=1;}match b.get(q){Some(b'0')=>q+=1,Some(b'1'..=b'9')=>{q+=1;while b.get(q).map(|c|c.is_ascii_digit()).unwrap_or(false){q+=1;}},_=>return Err(())}
  if b.get(q)==Some(&b'.'){q+=1;let start=q;while b.get(q).map(|c|c.is_ascii_digit()).unwrap_or(false){q+=1;}if q==start{return Err(());}}
  if matches!(b.get(q),Some(b'e'|b'E')){q+=1;if matches!(b.get(q),Some(b'+'|b'-')){q+=1;}let start=q;while b.get(q).map(|c|c.is_ascii_digit()).unwrap_or(false){q+=1;}if q==start{return Err(());}}Ok(q)
 },_=>Err(())}
}
fn eq_string(b:&[u8],text:&[u8])->bool{let mut tmp=[0;128];decode(b,&mut tmp).map(|(n,t)|n==t&&&tmp[..n]==text).unwrap_or(false)}
fn field<'a>(b:&'a[u8],key:&[u8])->R<Option<&'a[u8]>>{
 if b.first()!=Some(&b'{'){return Ok(None);}let mut q=ws(b,1);let mut found=None;
 while b.get(q)!=Some(&b'}'){let k=q;let ke=string_end(b,q)?;q=ws(b,ke);if b.get(q)!=Some(&b':'){return Err(());}q=ws(b,q+1);let ve=end(b,q,1)?;
  if eq_string(&b[k..ke],key){if found.is_some(){return Err(());}found=Some(&b[q..ve]);}q=ws(b,ve);if b.get(q)==Some(&b','){q=ws(b,q+1);}else if b.get(q)!=Some(&b'}'){return Err(());}}
 Ok(found)
}
fn text_field(b:&[u8],keys:&[&[u8]],out:&mut[u8])->R<bool>{
 for key in keys{if let Some(v)=field(b,key)?{if v.first()==Some(&b'"'){let(n,_)=decode(v,out)?;if n>0{return Ok(true);}}else if v.first().map(|c|c.is_ascii_digit()).unwrap_or(false){let n=v.len().min(out.len()-1);out[..n].copy_from_slice(&v[..n]);out[n]=0;return Ok(true);}}}Ok(false)
}
fn metadata(b:&[u8])->R<Metadata>{
 let mut m=Metadata::EMPTY;text_field(b,&[b"name",b"appName",b"label",b"title"],&mut m.name)?;
 if m.name[0]==0{if let Some(names)=field(b,b"names")?{if names.first()==Some(&b'['){let mut q=ws(names,1);while names.get(q)!=Some(&b']'){
  let e=end(names,q,1)?;let obj=&names[q..e];let default=field(obj,b"lang")?.map(|v|eq_string(v,b"defaults")).unwrap_or(false);
  if default||m.name[0]==0{text_field(obj,&[b"value",b"name"],&mut m.name)?;}if default{break;}q=ws(names,e);if names.get(q)==Some(&b','){q=ws(names,q+1);}else{break;}
 }}}}
 text_field(b,&[b"versionName",b"version",b"versionCode"],&mut m.version)?;Ok(m)
}
fn walk(b:&[u8],pkg:&[u8],depth:usize,found:&mut Option<Metadata>)->R<()>{
 if depth>24{return Err(());}if b.first()==Some(&b'{'){
  let mut matches=false;for key in [b"package".as_slice(),b"packageName",b"appPackage"]{if let Some(v)=field(b,key)?{matches|=eq_string(v,pkg);}}
  if matches{if found.is_some(){return Err(());}*found=Some(metadata(b)?);return Ok(());}
  let mut q=ws(b,1);while b.get(q)!=Some(&b'}'){q=ws(b,string_end(b,q)?);q=ws(b,q+1);let e=end(b,q,depth+1)?;walk(&b[q..e],pkg,depth+1,found)?;q=ws(b,e);if b.get(q)==Some(&b','){q=ws(b,q+1);}else{break;}}
 }else if b.first()==Some(&b'['){let mut q=ws(b,1);while b.get(q)!=Some(&b']'){let e=end(b,q,depth+1)?;walk(&b[q..e],pkg,depth+1,found)?;q=ws(b,e);if b.get(q)==Some(&b','){q=ws(b,q+1);}else{break;}}}Ok(())
}
pub fn registry(b:&[u8],pkg:&[u8])->R<Option<Metadata>>{
 if b.len()>65536||pkg.is_empty()||core::str::from_utf8(b).is_err(){return Err(());}let p=ws(b,0);let e=end(b,p,0)?;if ws(b,e)!=b.len(){return Err(());}let mut found=None;walk(&b[p..e],pkg,0,&mut found)?;Ok(found)
}
pub fn manifest(b:&[u8])->R<Metadata>{if core::str::from_utf8(b).is_err(){return Err(());}let p=ws(b,0);let e=end(b,p,0)?;if ws(b,e)!=b.len(){return Err(());}metadata(&b[p..e])}
#[cfg(test)]
mod tests{
 use super::*;
 fn s(b:&[u8])->&str{core::str::from_utf8(b.split(|c|*c==0).next().unwrap()).unwrap()}
 #[test]fn user_specific_schema(){let b=br#"{"unknown":true,"InstalledApps":[{"package":"x.a","name":"A","versionName":"1.2"},{"package":"x.b","name":"B","versionCode":27}],"order":["x.b","x.a"]}"#;let a=registry(b,b"x.a").unwrap().unwrap();assert_eq!(s(&a.name),"A");assert_eq!(s(&a.version),"1.2");assert_eq!(s(&registry(b,b"x.b").unwrap().unwrap().version),"27");assert!(registry(b,b"x.c").unwrap().is_none());}
 #[test]fn escaped_names(){let m=manifest(br#"{"names":[{"lang":"en","value":"fallback"},{"lang":"defaults","value":"\u624b\u74b0 \ud83d\ude3a"}],"version":"v\"1"}"#).unwrap();assert_eq!(s(&m.name),"手環 😺");assert_eq!(s(&m.version),"v\"1");}
 #[test]fn corrupt_and_duplicate_fail(){for b in [br#"{"package":"a","name":"bad\uD800"}"#.as_slice(),br#"[{"package":"a"},{"package":"a"}]"#,br#"{"package":"a","name":"A","name":"B"}"#,br#"{"package":"a",}"#,br#"{"version":01}"#,br#"[true false]"#,br#"{} junk"#]{assert!(registry(b,b"a").is_err());}}
 #[test]fn utf8_truncation(){let mut b=std::string::String::from("{\"name\":\"");for _ in 0..80{b.push('環');}b.push_str("\"}");let m=manifest(b.as_bytes()).unwrap();assert!(core::str::from_utf8(&m.name).is_ok());assert!(s(&m.name).len()<=127);}
}
