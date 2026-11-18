"""Application-level permutation operators, not native AxolDB Evolution bindings."""
from .proposal import evaluate
VERSION='public-permutation-operators/1'
def swap(order,left,right):
 evaluate({'order':order})
 if type(left) is not int or type(right) is not int or not 0<=left<5 or not 0<=right<5:raise ValueError('Swap indices')
 child=list(order);child[left],child[right]=child[right],child[left]
 return dict(evaluate({'order':child}),provenance={'operator':'application-swap','version':VERSION,'parent':list(order),'indices':[left,right]})
def crossover(first,second,start,end):
 evaluate({'order':first});evaluate({'order':second})
 if type(start) is not int or type(end) is not int or not 0<=start<end<=5:raise ValueError('Crossover segment')
 child=[None]*5;child[start:end]=first[start:end];rest=iter(x for x in second if x not in child)
 for index in list(range(start))+list(range(end,5)):child[index]=next(rest)
 return dict(evaluate({'order':child}),provenance={'operator':'application-ordered-crossover','version':VERSION,'parents':[list(first),list(second)],'segment':[start,end]})
