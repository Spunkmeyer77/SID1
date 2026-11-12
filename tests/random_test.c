/* SPDX-License-Identifier: GPL-3.0-only */
/* Rolls many patches of every type, on both chips, with random character settings, and plays each:
 * fails on any silent, clipping or NaN result. Writes tests/random.wav (a few rolls of each type). */
#include "../engine/sid1_engine.h"
#include "../engine/sid1_random.h"
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#define SR 48000
static float buf[SR];
static void wav(const char *fn, const float *x, int n){FILE*f=fopen(fn,"wb");int i,b=n*2,r=SR,br=SR*2;short s;
 fwrite("RIFF",1,4,f);i=36+b;fwrite(&i,4,1,f);fwrite("WAVEfmt ",1,8,f);i=16;fwrite(&i,4,1,f);s=1;fwrite(&s,2,1,f);fwrite(&s,2,1,f);
 fwrite(&r,4,1,f);fwrite(&br,4,1,f);s=2;fwrite(&s,2,1,f);s=16;fwrite(&s,2,1,f);fwrite("data",1,4,f);fwrite(&b,4,1,f);
 for(i=0;i<n;i++){float v=x[i];if(v>1)v=1;if(v<-1)v=-1;s=(short)(v*32767);fwrite(&s,2,1,f);}fclose(f);}
int main(void){
 static sid1_engine_t e; uint32_t seed=12345; int t,m,i,fails=0,total=0; float tmp[9600];
 float *demo=calloc(SR*7*8,sizeof(float)); int dn=0;
 sid1_patch_t cur=SID1_FACTORY[0], p;
 for(m=0;m<2;m++) for(t=0;t<SID1_R_NTYPES;t++){
  int quiet=0; double minr=9;
  for(i=0;i<150;i++){
   sid1_roll_t r={t,(i%3==0)?1.0f:(float)(seed%100)/100.0f,((float)(seed%201)-100)/100.0f,(float)((seed>>8)%100)/100.0f,((float)((seed>>4)%201)-100)/100.0f,(i%7==0)?(1<<(seed%5)):0,(int)(seed%4),m};
   int used=sid1_roll(&p,&cur,&r,&seed); (void)used;
   cur=p;
   sid1_init(&e,SR); sid1_set_model(&e,m); sid1_render(&e,tmp,9600);
   sid1_set_patch(&e,&p);
   sid1_note_on(&e,48,100); sid1_render(&e,buf,SR/2); sid1_note_off(&e,48); sid1_render(&e,buf+SR/2,SR/2);
   double rms=0,pk=0; int nan=0;
   for(int k=0;k<SR;k++){if(isnan(buf[k]))nan=1;rms+=buf[k]*buf[k];if(fabs(buf[k])>pk)pk=fabs(buf[k]);}
   rms=sqrt(rms/SR); if(rms<minr)minr=rms;
   total++;
   int drum=(t==SID1_R_DRUM)||(p.sr==0&&(p.ad&15)<6);
   if(nan||pk>=0.999||(drum?pk<0.03:rms<0.004)){fails++;quiet++; if(quiet<=2) printf("  FAIL %s %s rms %.4f pk %.3f wave %02x ad %02x sr %02x flt %d mode %02x cut %d res %d wt %d\n",m?"8580":"6581",SID1_RTYPE_NAMES[t],rms,pk,p.wave,p.ad,p.sr,p.flags&1,p.mode,p.cut,p.res,p.wt_len);}
   if(m==0&&i<6&&dn<SR*7*8-SR){for(int k=0;k<SR*7/10&&dn<SR*7*8;k++)demo[dn++]=buf[k];}
  }
  printf("%s %-5s  150 rolls, failed %d, quietest rms %.4f\n",m?"8580":"6581",SID1_RTYPE_NAMES[t],quiet,minr);
 }
 wav("tests/random.wav",demo,dn);
 printf("total %d, failed %d\n",total,fails);
 return fails!=0;
}
