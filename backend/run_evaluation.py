import json
from .evaluation import evaluate
if __name__=='__main__':
    result=evaluate()
    print(json.dumps(result,indent=2))
