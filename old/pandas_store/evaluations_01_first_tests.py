import pandas as pd
import numpy as np
from tinyolap.paceline.paceline import baseline


@baseline(iterations=1000, histogram=True)
def tests():
    df = pd.DataFrame(np.random.randn(100, 4))
    df.iloc[:9998] = np.nan
    sdf = df.astype(pd.SparseDtype("float", np.nan))
    return sdf
    #print(sdf.head())
    #print(sdf.dtypes)
    #print(sdf.sparse.density)

class Foo:
    @baseline(iterations=100000, histogram=True)
    def method(self):
        return True

f = Foo()
f.method()

tests()

def test():
    return 1,2

a = test()
print(a)