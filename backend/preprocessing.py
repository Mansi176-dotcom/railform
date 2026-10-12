import numpy as np
from scipy.signal import butter,sosfilt
class CausalFilter:
    def __init__(self, fs):
        self.sos=butter(3,[3,4000],btype='bandpass',fs=fs,output='sos');self.state=np.zeros((4,len(self.sos),2));self.last=np.zeros(4)
    def apply(self,raw):
        clean=raw.copy()
        for i in range(4):
            valid=np.isfinite(clean[i])
            if not valid.all():
                indices=np.maximum.accumulate(np.where(valid,np.arange(len(valid)),-1))
                clean[i]=np.where(indices>=0,clean[i,np.maximum(indices,0)],self.last[i])
            self.last[i]=clean[i,-1]
            clean[i],self.state[i]=sosfilt(self.sos,clean[i],zi=self.state[i])
        return clean
