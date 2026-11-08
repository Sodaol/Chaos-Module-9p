ENTRY(chaos_n67_init)
SECTIONS {
 . = 0x1D100000;
 __n67_image_start = .;
 .text : { *(.text .text.*) }
 .rodata : ALIGN(4) { *(.rodata .rodata.*) }
 .data : ALIGN(4) { *(.data .data.*) }
 .bss (NOLOAD) : ALIGN(4) { *(.bss .bss.*) *(COMMON) }
 __n67_image_end = .;
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.eh_frame*) *(.comment) *(.note*) }
}
