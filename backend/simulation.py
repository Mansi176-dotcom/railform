import numpy as np
from .models import Config
NAMES = ['Axle-box · Vertical','Axle-box · Longitudinal','Bogie · Vertical','Bogie · Lateral']
class Simulator:
    """Physics-inspired stochastic acceleration, never a validated dynamics solver."""
    def __init__(self, config: Config, demo=False):
        self.c=config; self.rng=np.random.default_rng(config.seed); self.index=0; self.demo=demo
    def truth(self):
        if self.demo:return [{'position':550.,'label':'Suspected squat-like impact','onset':16.5},{'position':1250.,'label':'Suspected squat-like impact','onset':37.5}]
        if self.c.preset in (1,2,3,4,7):return [{'position':self.c.position,'label':'Suspected long-wavelength irregularity' if self.c.preset==4 else 'Suspected squat-like impact','onset':self.c.position/(self.c.speed/3.6)}]
        return []
    def chunk(self, duration=.1):
        c=self.c; n=round(c.sample_rate*duration); t=(np.arange(n)+self.index)/c.sample_rate; self.index+=n
        speed=c.speed/3.6; distance=t*speed; position=distance%3000
        raw=np.array([.16*np.sin(2*np.pi*(34+i*7)*t)+.07*np.sin(2*np.pi*(110+speed)*t+i) for i in range(4)])
        raw+=self.rng.normal(0,c.noise,(4,n))
        events=self.truth()
        for j,event in enumerate(events):
            dt=(position-event['position'])/speed
            amp=([.65,4.5][j] if self.demo else {1:.65,2:c.severity,3:6,4:c.severity,7:4}.get(c.preset,0))
            if c.preset==4 and not self.demo:
                impact=amp*np.exp(-(dt/1.4)**2)*np.sin(2*np.pi*8*t)
            else:
                impact=amp*np.exp(-np.maximum(dt,0)*32)*np.sin(2*np.pi*1250*dt)*(dt>=0)*(dt<.3)
            for i,gain in enumerate([.8,1,.28,.12]):raw[i]+=impact*gain
        wheel=(c.preset in (5,7)) if not self.demo else ((t>=52)&(t<69))
        phase=np.mod(distance,2.8)/speed
        impact=3.2*np.exp(-phase*90)*np.sin(2*np.pi*850*phase)*wheel
        raw+=np.array([1,.85,.23,.1])[:,None]*impact
        raw+=c.bias+c.drift*t
        drop=c.dropout
        missing=self.rng.random((4,n))<drop
        if c.preset==6:missing|=self.rng.random((4,n))<.18
        if self.demo:missing|=np.broadcast_to((t>=72)&(t<80),(4,n))
        raw=np.clip(raw,-16,16);raw[missing]=np.nan
        return {'raw':raw,'times':t,'position':position,'distance':distance,'speed':speed,'sample_rate':c.sample_rate}
