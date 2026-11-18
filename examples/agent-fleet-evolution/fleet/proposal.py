"""Versioned provider-neutral permutation boundary; no model-supplied cost is trusted."""
from typing import Protocol
import json
from .model import Scenario,validate_plan,routes_for,digest
from .config import load,HERE
class ProposalProvider(Protocol):
 def propose(self,request:dict)->dict:...
def evaluate(value):
 if not isinstance(value,dict) or set(value)!={'order'}:raise ValueError('Only an order proposal is accepted')
 order=value['order']
 if type(order) is not list or len(order)!=5 or any(type(x) is not str for x in order) or set(order)!={'d1','d2','d3','d4','d5'}:raise ValueError('Exact delivery permutation required; no repair')
 scenario=Scenario.load(load(HERE/'scenario.json'));orders={'v1':order[:3],'v2':order[3:]}
 paths=routes_for(scenario,(tuple(orders['v1']),tuple(orders['v2'])));cost=sum(x['cost'] for x in paths.values())
 return {'interface':'permutation/1','order':order,'orders':orders,'paths':paths,'cost':cost,'feasible':True,'proposalHash':digest(value),'modelCostTrusted':False}
def recorded(path):
 value=load(path)
 if set(value)!={'format','request','response','responseHash'} or value['format']!='authored-synthetic-recording/1':raise ValueError('Only the public authored fixture is accepted by this command')
 if digest(value['response'])!=value['responseHash']:raise ValueError('Recording hash')
 return dict(evaluate(value['response']),modelCalls=0,source='authored synthetic fixture; not a private model response')
