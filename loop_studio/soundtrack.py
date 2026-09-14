"""Original procedural music beds: restrained chords, bass and optional percussion."""
import array
import math
import random
import wave


def compose(path, duration, kind, cancel=None):
    rate=24000
    rng=random.Random(42)
    # D minor / B flat / F / C. No recorded or downloaded music is used.
    chords=((146.83,174.61,220.0),(116.54,146.83,174.61),(130.81,174.61,220.0),(130.81,164.81,196.0))
    bpm=112 if kind=='pulse' else 72
    beat=60/bpm
    frames=round(duration*rate)
    with wave.open(str(path),'wb') as output:
        output.setnchannels(2);output.setsampwidth(2);output.setframerate(rate)
        for block in range(0,frames,rate):
            if cancel and cancel.is_set():
                raise ValueError('Operation cancelled')
            samples=array.array('h')
            for n in range(block,min(frames,block+rate)):
                t=n/rate;bar=int(t/(beat*4));phase=t%(beat*4)
                frequencies=chords[bar%4]
                envelope=min(1,t/.45,max(0,(duration-t)/.8))
                chord_envelope=min(1,phase/.12,(beat*4-phase)/.18)
                pad=sum(math.sin(2*math.pi*f*t)+.16*math.sin(2*math.pi*f*2*t) for f in frequencies)*.045*chord_envelope
                bass=.055*math.sin(2*math.pi*(frequencies[0]/2)*t)
                percussion=0
                if kind=='pulse':
                    kick=t%beat
                    percussion=.22*math.exp(-kick*22)*math.sin(2*math.pi*(48*kick+5*(1-math.exp(-kick*28))))
                    hat=t%(beat/2)
                    percussion+=rng.uniform(-1,1)*.032*math.exp(-hat*100)
                    snare=(t-beat)%(beat*2)
                    percussion+=rng.uniform(-1,1)*.065*math.exp(-snare*35)
                value=max(-.9,min(.9,(pad+bass+percussion)*envelope))
                samples.extend((round(value*32767),round(value*32767)))
            output.writeframes(samples.tobytes())
