/* SPDX-License-Identifier: GPL-3.0-only */
/* Plays each factory patch (a short phrase) through the engine at 48 kHz and writes tests/out.wav; checks levels. */
#include "../engine/sid1_engine.h"
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#define SR 48000
static void wav(const char *fn, const float *x, int n){FILE*f=fopen(fn,"wb");int i,b=n*2,r=SR,br=SR*2;short s;
 fwrite("RIFF",1,4,f);i=36+b;fwrite(&i,4,1,f);fwrite("WAVEfmt ",1,8,f);i=16;fwrite(&i,4,1,f);s=1;fwrite(&s,2,1,f);fwrite(&s,2,1,f);
 fwrite(&r,4,1,f);fwrite(&br,4,1,f);s=2;fwrite(&s,2,1,f);s=16;fwrite(&s,2,1,f);fwrite("data",1,4,f);fwrite(&b,4,1,f);
 for(i=0;i<n;i++){float v=x[i];if(v>1)v=1;if(v<-1)v=-1;s=(short)(v*32767);fwrite(&s,2,1,f);}fclose(f);}
int main(int argc,char**argv){
 static sid1_engine_t e; int per=SR*2, n, p, fail=0, os=argc>1;
 float *buf=calloc((size_t)per*(SID1_NFACTORY+1),sizeof(float));
 sid1_init(&e,SR); sid1_set_oversample(&e,os);
 sid1_render(&e,buf,per); /* settle */
 for(p=0;p<SID1_NFACTORY;p++){
  float *o=buf+(size_t)per*(p+1); double rms=0,pk=0; int i;
  sid1_set_patch(&e,&SID1_FACTORY[p]);
  sid1_note_on(&e,48,100); sid1_note_on(&e,55,100);
  sid1_render(&e,o,SR/2);
  sid1_note_off(&e,48); sid1_note_off(&e,55); sid1_note_on(&e,60,100);
  sid1_render(&e,o+SR/2,SR/2); sid1_note_off(&e,60);
  sid1_render(&e,o+SR,per-SR);
  for(i=0;i<per;i++){double v=o[i]; if(isnan(v)){fail=1;} rms+=v*v; if(fabs(v)>pk)pk=fabs(v);}
  rms=sqrt(rms/per);
  printf("%-11s rms %.3f peak %.3f%s\n",SID1_FACTORY[p].name,rms,pk,rms<0.003?"  <-- SILENT":"");
  if(rms<0.003||pk>=1.0) fail=1;
 }
 wav(os?"tests/out_2x.wav":"tests/out.wav",buf,per*(SID1_NFACTORY+1));
 return fail;
}
