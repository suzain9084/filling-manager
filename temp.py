import math

class Solution(object):
    def countGoodArrays(self, n, m, k):
        def comp(n,k):
            if n < 0 or k < 0:
                return 0
            factorial = 1
            mapping = {} 
            for i in range(n+1):
                if i != 0:
                    factorial *= i
                if i == n-k or i == k:
                    mapping[i] = factorial

            return int(factorial/(mapping[n-k]*mapping[k]))
        mod = 10**9 + 7
        return comp(n-1,n-k-1)*m*(m-1)**(n-k-1)%mod
        
    
s = Solution()
n =40603
m =16984
k =29979
print(s.countGoodArrays(n,m,k))
