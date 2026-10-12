import numpy as np
from .preprocessing import CausalFilter
from .features import extract,decimate
from .models import VERSION

class Detector:
    """Receives measurements only, never preset, defect location, labels or truth."""
    def __init__(self,fs,reference=None):
        self.fs=fs;self.filter=CausalFilter(fs);self.raw=np.zeros((4,0));self.filtered=np.zeros((4,0));self.times=np.array([]);self.positions=np.array([]);self.distances=np.array([]);self.reference=reference or {'wavelet_energy':.055,'vertical_wavelet':.055,'low_energy':.035,'rms':.25};self.active=False;self.cooldown=-1e9;self.quality_active=False;self.history=[];self.spatial={};self.latest={};self.last_features={};self.window=int(.4*fs);self.hop=int(.1*fs);self.pending=0;self.candidate=None
    def ingest(self,chunk):
        raw=chunk['raw'];filtered=self.filter.apply(raw);self.pending+=raw.shape[1]
        for name,value in [('raw',raw),('filtered',filtered)]:setattr(self,name,np.concatenate([getattr(self,name),value],axis=1)[:,-self.window:])
        for name,key in [('times','times'),('positions','position'),('distances','distance')]:setattr(self,name,np.concatenate([getattr(self,name),chunk[key]])[-self.window:])
        if self.raw.shape[1]<self.window or self.pending<self.hop:return []
        self.pending%=self.hop
        missing=float(np.mean(~np.isfinite(self.raw)));saturation=float(np.mean(np.abs(np.nan_to_num(self.raw))>=15.99));f=extract(self.filtered,self.fs)
        ratios={k:f[k]/max(v,1e-9) for k,v in self.reference.items()};f.update({'missing':missing,'saturation':saturation});score=max(ratios['wavelet_energy'],ratios['low_energy']);f['score']=score;self.last_features=f
        self.history.append([float(self.times[-1]),score]);self.history=self.history[-600:]
        self.latest={'raw':self.raw.copy(),'filtered':self.filtered.copy(),'features':f,'history':list(self.history)}
        if missing>.05 or saturation>.01:
            if not self.quality_active:
                self.quality_active=True;self.candidate=None
                return [self.event('Sensor-quality issue','quality',f,ratios,len(self.times)-1)]
            return []
        self.quality_active=False
        if score<.65:self.active=False
        if self.candidate is None:
            if score<=1 or self.active or self.times[-1]-self.cooldown<.45:return []
            self.candidate=float(self.times[-1])
            return []
        if self.times[-1]-self.candidate<.199:return []
        self.candidate=None
        self.active=True;self.cooldown=self.times[-1]
        idx=int(np.argmax(np.abs(self.filtered[1])))
        label='Likely periodic wheel-related disturbance' if f['periodic'] else 'Suspected long-wavelength irregularity' if ratios['low_energy']>ratios['wavelet_energy'] else 'Suspected squat-like impact'
        return [self.event(label,'track',f,ratios,idx)]
    def event(self,label,kind,f,ratios,idx):
        pos=float(self.positions[idx]);pass_id=int(self.distances[idx]//3000);key=round(pos/30)
        distinct=self.spatial.setdefault(key,set());distinct.add(pass_id)
        support=f['vertical_wavelet']>self.reference['vertical_wavelet'];evidence='Limited' if kind=='quality' or not support else 'Supported';evidence='Repeated spatial support' if len(distinct)>1 and support else evidence
        score=f['score'];severity='High' if score>=8 else 'Moderate' if score>=2 else 'Low'
        explanation=(f"Missing samples {f['missing']:.1%}; saturation {f['saturation']:.1%}. Track inference was suppressed for this window." if kind=='quality' else f"Activity near {pos/1000:.3f} km exceeded the healthy reference. Longitudinal wavelet energy was {ratios['wavelet_energy']:.2f}× its reference and low-frequency energy was {ratios['low_energy']:.2f}×. Vertical support: {'present' if support else 'insufficient'}. Measured periodicity: {'present' if f['periodic'] else 'not established'}. This supports a cautious label, not a verified root cause.")
        return {'time':float(self.times[-1]),'position':pos,'pass':pass_id,'segment':f'S-{min(15,int(pos/200)+1):03d}','label':label,'kind':kind,'score':score,'severity':severity,'evidence':evidence,'passes':len(distinct),'features':dict(f),'ratios':ratios,'references':dict(self.reference),'explanation':explanation,'alternatives':'Wheel impacts, welds, joints and vehicle vibration can resemble track defects. Periodic track structures can resemble wheel impacts.','next':'Review the measured excerpt, data quality and independent passes; compare with independent inspection records before any operational decision.','limitations':'Synthetic data only. Window-edge and localization uncertainty remain. No field validation or calibrated failure probability.','detector':VERSION,'status':'New','history':[],'excerpt':decimate(self.filtered[1],self.fs)}

def calibrate(fs=12800):
    from .simulation import Simulator
    from .models import Config
    values=[]
    for seed in [11,12,13]:
        sim=Simulator(Config(seed=seed,preset=0,sample_rate=fs));d=Detector(fs)
        for _ in range(15):
            d.ingest(sim.chunk())
            if d.last_features:values.append(d.last_features)
    return {k:float(max(np.quantile([v[k] for v in values],.995)*4,1e-5)) for k in ['wavelet_energy','vertical_wavelet','low_energy','rms']}
