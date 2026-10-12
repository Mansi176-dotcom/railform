from time import perf_counter
import numpy as np
from .simulation import Simulator
from .detection import Detector,calibrate
from .models import Config,VERSION
from .persistence import timestamp

def match(pred,truth,tolerance=25):
    candidates=sorted((abs(p['position']-t['position']),i,j) for i,p in enumerate(pred) for j,t in enumerate(truth) if abs(p['position']-t['position'])<=tolerance)
    used_p=set();used_t=set();pairs=[]
    for error,i,j in candidates:
        if i not in used_p and j not in used_t:used_p.add(i);used_t.add(j);pairs.append((pred[i],truth[j],error))
    return pairs,len(pred)-len(pairs),len(truth)-len(pairs)
def metrics(tp,fp,fn,km,errors,delays,latency):
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return dict(tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0.,false_alarms_per_km=fp/km,localization_error=float(np.mean(errors)) if errors else None,delay=float(np.mean(delays)) if delays else None,latency=float(np.mean(latency)) if latency else None)
def evaluate(reference=None):
    reference=reference or calibrate();totals={k:{'tp':0,'fp':0,'fn':0,'errors':[],'delays':[],'latency':[]} for k in ['baseline','implemented']};correct=matched=0;km=0
    # All runs are partitioned before overlapping windows exist. Healthy calibration seeds are 11–13.
    seeds=list(range(101,109))
    for preset,seed in enumerate(seeds):
        c=Config(seed=seed,preset=preset,position=150,speed=120,severity=3,repeated=False);sim=Simulator(c);d=Detector(c.sample_rate,reference);pred=[];base=[];active=False;last=-100
        for _ in range(110):
            chunk=sim.chunk();start=perf_counter();events=d.ingest(chunk);totals['implemented']['latency'].append((perf_counter()-start)*1000)
            pred.extend(e for e in events if e['kind']=='track' and e['label']!='Likely periodic wheel-related disturbance')
            start=perf_counter();peak=float(np.nanmax(np.abs(chunk['raw'][:2]))) if np.any(np.isfinite(chunk['raw'][:2])) else 0;now=float(chunk['times'][-1])
            if peak>1 and not active and now-last>.45:
                idx=int(np.nanargmax(np.abs(chunk['raw'][1])));base.append({'position':float(chunk['position'][idx]),'time':now});active=True;last=now
            if peak<.65:active=False
            totals['baseline']['latency'].append((perf_counter()-start)*1000)
        truth=sim.truth();km+=110*.1*c.speed/3.6/1000
        for key,observations in [('implemented',pred),('baseline',base)]:
            pairs,fp,fn=match(observations,truth);v=totals[key];v['tp']+=len(pairs);v['fp']+=fp;v['fn']+=fn;v['errors'] += [p[2] for p in pairs];v['delays'] += [max(0,p['time']-t['onset']) for p,t,_ in pairs]
            if key=='implemented':matched+=len(pairs);correct+=sum(p['label']==t['label'] for p,t,_ in pairs)
    result={key:metrics(km=km,**v) for key,v in totals.items()}
    result.update(classification={'correct':correct,'matched':matched},protocol={'runs':8,'training_seeds':[11,12,13],'held_out_seeds':seeds,'split':'By run seed, before windowing. One run per preset; small illustrative test, not a generalization estimate.','matching_tolerance_m':25,'matching':'One-to-one, nearest eligible event; wheel and quality observations excluded from track-event predictions.','baseline':'Raw absolute acceleration > 1 m/s²; 0.65 hysteresis, 0.45 s cooldown.','observed_km':km,'detector':VERSION,'date':timestamp(),'window_s':.4,'hop_s':.1,'classification':'Conditional accuracy on matched track events only; misses reported separately.','negative_count':'Not defined for event matching; no true-negative claims.'})
    return result
