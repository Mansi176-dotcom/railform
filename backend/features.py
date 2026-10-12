import numpy as np
import pywt
from scipy.signal import welch,find_peaks
from scipy.ndimage import uniform_filter1d
from scipy.stats import kurtosis

def extract(x,fs):
    rms=np.sqrt(np.mean(x*x,axis=1));peak=np.max(np.abs(x),axis=1)
    f,p=welch(x,fs=fs,nperseg=min(512,x.shape[1]),axis=1)
    band=np.trapezoid(p[:,(f>=600)&(f<=2200)],f[(f>=600)&(f<=2200)],axis=1)
    low=np.trapezoid(p[:,(f>=3)&(f<=20)],f[(f>=3)&(f<=20)],axis=1)
    # Decimation follows explicit low-pass resampling, preserving the 0.6–2.2 kHz project band.
    from scipy.signal import resample_poly
    small=resample_poly(x,1,2,axis=1)
    freqs=np.array([650,900,1250,1800,2200]);scales=pywt.central_frequency('morl')*(fs/2)/freqs
    coeff,_=pywt.cwt(small,scales,'morl',sampling_period=2/fs,axis=1)
    wave=np.mean(abs(coeff)**2,axis=(0,2))
    envelope=uniform_filter1d(np.max(np.abs(x[:2]),axis=0),size=max(1,int(fs*.003)))
    peaks,_=find_peaks(envelope,height=max(.45,float(envelope.max())*.4),distance=int(fs*.05),prominence=.3)
    spacing=np.diff(peaks)/fs
    periodic=float(len(spacing)>=2 and np.std(spacing)/max(np.mean(spacing),1e-9)<.2)
    return {'rms':float(rms[1]),'peak_to_peak':float(np.ptp(x[1])),'crest_factor':float(peak[1]/max(rms[1],1e-9)),'kurtosis':float(kurtosis(x[1],fisher=False)) if rms[1]>1e-8 else 0.,'band_energy':float(band[1]),'wavelet_energy':float(wave[1]),'vertical_wavelet':float(wave[0]),'low_energy':float(low[1]),'cross_sensor_agreement':float(min(wave[0],wave[1])/max(wave[0],wave[1],1e-9)),'periodic':periodic}

def decimate(y,fs,limit=320):
    # Per-bucket min/max in chronological order retain narrow extrema.
    out=[];step=max(1,len(y)//(limit//2))
    for start in range(0,len(y),step):
        z=y[start:start+step]
        if not np.any(np.isfinite(z)):out.extend([[start/fs,None],[(start+len(z)-1)/fs,None]]);continue
        for idx in sorted(set([int(np.nanargmin(z)),int(np.nanargmax(z))])):out.append([(start+idx)/fs,float(z[idx])])
    return out
