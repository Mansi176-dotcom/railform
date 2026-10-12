import numpy as np
from backend.models import Config
from backend.simulation import Simulator
from backend.preprocessing import CausalFilter
from backend.detection import Detector,calibrate
from backend.evaluation import match,metrics
from backend import persistence as db

def test_seed_and_speed():
    a=Simulator(Config(seed=42));b=Simulator(Config(seed=42))
    np.testing.assert_array_equal(a.chunk()['raw'],b.chunk()['raw'])
    c=Simulator(Config(speed=72)).chunk();assert abs(c['distance'][-1]-c['times'][-1]*20)<1e-12

def test_filter_state():
    x=np.random.default_rng(4).normal(size=(4,12800));a=CausalFilter(12800).apply(x);d=CausalFilter(12800);b=np.concatenate([d.apply(x[:,:4000]),d.apply(x[:,4000:])],axis=1);np.testing.assert_allclose(a,b)

def test_no_truth_input():
    s=Simulator(Config(preset=3,position=100));d=Detector(12800);e=[]
    for _ in range(45):
        chunk=s.chunk();assert set(chunk)=={'raw','times','position','distance','speed','sample_rate'};e+=d.ingest(chunk)
    assert any(x['kind']=='track' for x in e)
    assert len([x for x in e if x['kind']=='track'])<=2

def test_missing_data():
    s=Simulator(Config(dropout=.3));d=Detector(12800);events=[]
    for _ in range(8):events+=d.ingest(s.chunk())
    assert len(events)==1 and events[0]['kind']=='quality'
    assert np.isfinite(d.filtered).all()

def test_persistence():
    a=db.save('alert','test',{'status':'New'});a['status']='Acknowledged';db.save('alert','test',a,a['id']);assert db.get(a['id'])['status']=='Acknowledged'

def test_matching():
    pairs,fp,fn=match([{'position':100},{'position':102},{'position':200}],[{'position':101},{'position':300}],10);assert (len(pairs),fp,fn)==(1,2,1)
    m=metrics(1,2,1,2,[1],[.1],[3]);assert m['precision']==1/3 and m['recall']==.5 and m['false_alarms_per_km']==1

def test_reproducible_demo():
    ref=calibrate();sim=Simulator(Config(seed=42,preset=0),True);d=Detector(12800,ref);events=[]
    for _ in range(900):events+=d.ingest(sim.chunk())
    assert not [e for e in events if e['time']<14]
    assert any(e['label']=='Suspected squat-like impact' and 36<e['time']<40 for e in events)
    assert any(e['label']=='Likely periodic wheel-related disturbance' for e in events)
    assert any(e['kind']=='quality' for e in events)
