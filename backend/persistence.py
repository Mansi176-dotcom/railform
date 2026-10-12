import os,json,uuid
from datetime import datetime,timezone
from sqlalchemy import create_engine,Column,String,Text
from sqlalchemy.orm import DeclarativeBase,Session
DB=os.environ.get('RAILFORM_DB','sqlite:///runtime/railform.db')
os.makedirs('runtime',exist_ok=True)
engine=create_engine(DB,connect_args={'check_same_thread':False} if DB.startswith('sqlite') else {})
class Base(DeclarativeBase):pass
class Record(Base):
    __tablename__='records';id=Column(String,primary_key=True);kind=Column(String,index=True);run=Column(String,index=True);body=Column(Text)
Base.metadata.create_all(engine)
def save(kind,run,data,id=None):
    id=id or str(uuid.uuid4());data={**data,'id':id}
    with Session(engine) as s:
        r=s.get(Record,id)
        if r:r.body=json.dumps(data)
        else:s.add(Record(id=id,kind=kind,run=run,body=json.dumps(data)))
        s.commit()
    return data
def records(kind,run=None):
    with Session(engine) as s:
        q=s.query(Record).filter_by(kind=kind)
        if run:q=q.filter_by(run=run)
        return [json.loads(r.body) for r in q.all()]
def get(id):
    with Session(engine) as s:
        r=s.get(Record,id);return json.loads(r.body) if r else None
def timestamp():return datetime.now(timezone.utc).isoformat()
def prune(keep=20):
    runs=records('run')
    for r in runs[:-keep]:
        with Session(engine) as s:s.query(Record).filter_by(run=r['id']).delete();s.commit()
