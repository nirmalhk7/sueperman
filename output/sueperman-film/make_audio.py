"""Produce locally voiced dialogue and an original deterministic music/SFX mix."""
import array, json, math, subprocess, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'
# Absolute cue starts and maximum voice windows leave authored reaction holds intact.
CUES=[
('n1',0.65,3.8,'Daniel',154,'With great purchases come great responsibilities.'),
('n2',5.05,2.2,'Daniel',151,'Mostly keeping receipts.'),
('m1',10.5,1.2,'Fred',190,'Cycle complete!'),
('l1',11.9,.7,'Samantha (English (US))',180,'What?'),
('m2',13.0,1.1,'Fred',200,'Cycle complete!'),
('m3',14.2,1.8,'Fred',220,'For best results, download the LexCorp app.'),
('l2',16.15,1.0,'Samantha (English (US))',210,'Are you kidding me?'),
('m4',17.3,1.5,'Fred',210,'Thank you for choosing LexCorp!'),
('h1',21.2,3.2,'Eddy (English (US))',181,'Whoa, Lois. Step away from the spin cycle.'),
('h2',24.65,5.0,'Eddy (English (US))',184,"If you've got the receipt, Sueperman can check whether LexCorp owes you a remedy."),
('n3',30.65,10.1,'Daniel',161,"People miss recalls. They miss settlements. Sometimes they don't even know there's anything to claim."),
('n4',42.4,3.7,'Daniel',158,'Meet Sueperman. Your consumer-rights agent.'),
('n5',47.0,4.0,'Daniel',160,'It checks your purchases against official recall notices.'),
('n6',53.8,4.0,'Daniel',159,'Checks the details, and rejects false matches.'),
('n7',60.0,5.4,'Daniel',162,'And helps prepare the paperwork, with the evidence to back it up.'),
('l3',69.65,2.15,'Samantha (English (US))',162,'Wait. Are you Superman?'),
('h3',72.1,.48,'Eddy (English (US))',145,'No.'),
('l4',74.0,2.2,'Samantha (English (US))',160,'Can you fix my washing machine?'),
('h4',76.45,.48,'Eddy (English (US))',145,'No.'),
('h5',79.25,3.7,'Eddy (English (US))',155,'But I know how to get the paperwork started.'),
]
def run(args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
meta=[]
for ident,start,maximum,voice,rate,text in CUES:
    aiff=ASSETS/f'{ident}.aiff'; wav=ASSETS/f'{ident}.wav'
    if not aiff.exists(): run(['say','-v',voice,'-r',str(rate),'-o',str(aiff),text])
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(aiff)]))
    tempo=max(1,duration/maximum)
    run(['ffmpeg','-y','-i',str(aiff),'-af',f'atempo={tempo},loudnorm=I=-17:TP=-2:LRA=7','-ar','24000','-ac','1',str(wav)])
    actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(wav)]))
    meta.append(dict(id=ident,start=start,duration=actual,text=text,path=f'assets/{ident}.wav'))
    print(ident,round(actual,2),flush=True)
( ROOT/'audio-cues.json').write_text(json.dumps(meta,indent=2))
# Original, mathematically synthesized score: minor brass-like harmonics, strings and sub bass.
SR=24000; N=90*SR
mix=array.array('f',[0.0])*N
chords=[(146.83,174.61,220.0),(116.54,146.83,174.61),(130.81,164.81,196.0),(110,138.59,164.81)]
for k in range(45):
    t0=k*2; chord=chords[k%4]
    for i in range(2*SR):
        t=i/SR; absolute=t0+t
        if 69<=absolute<79.05 or 18.8<=absolute<20: continue
        if absolute<8: gain=.025
        elif absolute<19: gain=.012
        elif absolute<30: gain=.075
        elif absolute<42: gain=.04
        elif absolute<69: gain=.025
        else: gain=.09
        if any(c['start']-.12<=absolute<c['start']+c['duration']+.15 for c in meta): gain*=.42
        env=min(1,t/.09)*min(1,(2-t)/.3)
        value=0
        for f in chord:
            value+=(math.sin(2*math.pi*f*t)+.27*math.sin(4*math.pi*f*t)+.12*math.sin(6*math.pi*f*t))/4.17
        value+=.3*math.sin(2*math.pi*chord[0]/2*t)
        mix[int(t0*SR)+i]+=gain*env*value
# Cheerful machine chimes and intentional UI confirmation/hero impacts.
for start in [10.25,12.8,17.05,78.55,46.6,51.2,58.6,65.4,84.15]:
    for offset,f in [(0,1046.5),(.16,1318.5),(.32,1568)]:
        for i in range(int(.42*SR)):
            idx=int((start+offset)*SR)+i
            if idx<N: mix[idx]+=.085*math.exp(-i/SR*9)*math.sin(2*math.pi*f*i/SR)
for start in [19.65,29.8,41.85,58.0,79.05,84.0]:
    for i in range(int(.7*SR)):
        t=i/SR; idx=int(start*SR)+i
        if idx<N: mix[idx]+=.17*math.exp(-t*7)*math.sin(2*math.pi*(75*t-25*t*t))
for c in meta:
    with wave.open(str(ASSETS/f"{c['id']}.wav"),'rb') as w:
        raw=array.array('h');raw.frombytes(w.readframes(w.getnframes()))
    offset=int(c['start']*SR)
    for i,s in enumerate(raw):
        if offset+i<N: mix[offset+i]+=.88*s/32768
pcm=array.array('h',(int(max(-.95,min(.95,s))*32767) for s in mix))
with wave.open(str(ASSETS/'soundtrack.wav'),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())
def stamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(ROOT/'captions.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['start']+c['duration'])}\n{c['text']}" for i,c in enumerate(meta)))
print('90-second soundtrack and optional captions ready',flush=True)
