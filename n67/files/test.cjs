const fs=require('fs');
const names=['normalize paths','validate UTF-8','insert/delete UTF-8','load short reads/EINTR',
 'refuse oversized edit','refuse binary edit','save partial writes','save ENOSPC preserves original',
 'save fsync failure preserves original','save rename failure preserves original','detect external edit',
 'copy short reads/writes','copy refuses overwrite','move','exclusive new file','mkdir/remove empty directory',
 'directory window','serialize file workers','worker spawn failure','do not overwrite queued command',
 'script path is immutable','reject unsupported script path','FIFO partial send and output',
 'shell exit closes UI descriptors','bounded terminal buffer','PID reuse guard','interrupt owned descendants only',
 'build widgets and native scroll viewport','event allocation failure','pause/resume/destroy lifetime',
 'unsaved confirmation','long press does not activate new menu','tap key exactly once','text page coverage',
 'long press cursor to beginning/end','long press backspace repeats and releases',
 'transactional directory copy','directory copy write failure rollback','directory copy rename failure rollback',
 'reject copy into source directory','recursive directory deletion','delete symlink without traversing it',
 'directory copy does not follow symlinks','deletion preflight preserves files on unsupported entry',
 'continuous terminal line windows','hex rows fit without skipping bytes',
 'interrupt restarts console task running inline scripts','page exit cancels console restart',
 'long UTF-8 path cannot hide status row','recheck external edits before committing save',
 'clipboard remembers symlink type across directories',
 'pseudo-FS pipes avoid mounted tmp EEXIST','reuse owned pipe pair across 20 restarts',
 'input pipe collision preserves unrelated file','output pipe failure rolls back input device',
 'output pipe collision preserves existing node and retries','UI open error survives descriptor cleanup',
 'console spawn error survives descriptor cleanup','stdio redirect error is reported',
 'restart drains unconsumed commands','all six page layouts have usable nonoverlapping touch targets',
 'submitting Enter releases even after its context is hidden','UI input open error has no descriptor leak',
 'console output open error retains the failure stage','directory menu omits unsupported view/edit/run',
 'new command is blank; history remains explicit','reset clears commands/history and restarts session',
 'pixel scrolling and native scroll click suppression','horizontal and keyboard gestures preserve system behavior',
 'detect PNG header through short reads','structured formats and binary content detection',
 'unsupported and oversized images fall back to information','image fitting and firmware root lifetime',
 'worker BMP decoding orientation and partial reads','reject compressed BMP without corrupting viewer',
 'file information and fresh input retains console context','directory hold survives RELEASED before CLICKED',
 'directory virtualization preserves sub-row pixels',
 'terminal preserves reader position and follows only at bottom','large logical list rebases without losing pixels',
 'long file overlapping read preserves visible byte anchor','small finger drag cannot select a file','binary tail is never disguised as a partial UTF-8 sample',
 'image fallback reads the selected file before HEX display','scroll I/O failures stop retrying and clear invalid content',
 'parent row precedes files and remains safe at root','stable pixel caret and logical editor window',
 'clear old editor before loading; failed load preserves terminal','inspection completion preserves newly chosen view',
 'virtual row press cannot select a changed file','frozen selected type and moved clipboard path','visible caret and wider keys survive layout switches',
 'PNG uses actual N67 driver paths and checks full IHDR dimensions',
 'pixel wrapping matches content height for wide glyphs and tabs',
 'terminal last line remains reachable under scroll clamping and rebasing',
 'editor swipes preserve pixels and keys follow the caret',
 'text taps position UTF-8 cursor using scrolled coordinates',
 'drag, scroll and press loss cannot reposition a cursor',
 'command prompt and tap share the same text origin',
 'caret follows physical glyph positions without cumulative letter spacing drift',
 'terminal last glyphs fit both the label and viewport after physical wrapping',
 'multiline caret and tap match the label line spacing'];
(async()=>{const {instance}=await WebAssembly.instantiate(fs.readFileSync(__dirname+'/generated/test.wasm'));
 const size=instance.exports.test_state_size();if(size>0x18000)throw Error('resident state overflow');
 console.log(`PASS runtime state fits: ${size} bytes / ${0x18000}`);
 for(let i=0;i<names.length;i++){const rc=instance.exports.run_test(i);if(rc){
  const b=Buffer.from(instance.exports.memory.buffer),d=instance.exports.test_debug;
  const str=p=>b.subarray(p,b.indexOf(0,p)).toString();
  console.log({ret:d(0),message:d(1),errno:d(2),src:str(d(4)),dst:str(d(5))});
  const base=d(3);for(let n=0;n<16;n++){const p=base+n*40524;if(b.readUInt32LE(p+40520))console.log('node',n,str(p),b.readUInt32LE(p+40516));}
  throw Error(`${names[i]} failed at C line ${rc}`);
 }console.log('PASS '+names[i]);}
 console.log(`PASS ${names.length} native-core checks`);
})().catch(e=>{console.error(e);process.exit(1)});
